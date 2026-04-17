#!/usr/bin/env python3
"""
Fetch Taiwan stock daily OHLCV (盤後) data from Yahoo Finance and store in SQLite.

Usage:
    python scripts/fetch_ohlcv.py              # incremental – only missing days
    python scripts/fetch_ohlcv.py --full       # full gap-check across entire retention window

Config (read from backend/.env):
    DATA_RETENTION_YEARS  – years of history to keep (default: 1)
    FETCH_SCHEDULE_TIME   – (used by scheduler, not this script)

Database:
    Table: daily_prices (symbol, date, open, high, low, close, adj_close, volume)
"""

import os
import sys
import json
import sqlite3
import time
from datetime import datetime, timedelta, date

# Force UTF-8 output on Windows to prevent mojibake with Chinese characters
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding and sys.stderr.encoding.lower() != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

# Make sure we can import from the backend directory
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(BACKEND_DIR, '.env'))

try:
    import yfinance as yf
    import pandas as pd
except ImportError:
    print("yfinance/pandas not found – installing...")
    os.system(f"{sys.executable} -m pip install yfinance pandas")
    import yfinance as yf
    import pandas as pd

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DATA_RETENTION_YEARS = float(os.getenv('DATA_RETENTION_YEARS', '1'))
DB_PATH = os.path.abspath(os.path.join(BACKEND_DIR, '..', 'data', 'stocks.db'))
STOCKS_JSON = os.path.join(BACKEND_DIR, 'tw_stocks.json')

BATCH_SIZE = 50   # symbols per yf.download() call

# ---------------------------------------------------------------------------
# DB – table & index creation
# ---------------------------------------------------------------------------

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS daily_prices (
    symbol    TEXT NOT NULL,
    date      TEXT NOT NULL,
    open      REAL,
    high      REAL,
    low       REAL,
    close     REAL,
    adj_close REAL,
    volume    INTEGER,
    PRIMARY KEY (symbol, date)
)
"""

CREATE_INDEX_SQLS = [
    "CREATE INDEX IF NOT EXISTS idx_dp_symbol ON daily_prices(symbol)",
    "CREATE INDEX IF NOT EXISTS idx_dp_date   ON daily_prices(date)",
]


def init_table(conn: sqlite3.Connection) -> None:
    conn.execute(CREATE_TABLE_SQL)
    for sql in CREATE_INDEX_SQLS:
        conn.execute(sql)
    conn.commit()


# ---------------------------------------------------------------------------
# DB – query helpers
# ---------------------------------------------------------------------------

def get_last_date(conn: sqlite3.Connection, symbol: str, cutoff: str) -> str | None:
    """Return the most recent date stored for *symbol* on or after *cutoff*."""
    row = conn.execute(
        "SELECT MAX(date) FROM daily_prices WHERE symbol = ? AND date >= ?",
        (symbol, cutoff),
    ).fetchone()
    return row[0] if row and row[0] else None


def get_existing_dates(conn: sqlite3.Connection, symbol: str, cutoff: str) -> set[str]:
    """Return the set of all stored dates for *symbol* on or after *cutoff*."""
    rows = conn.execute(
        "SELECT date FROM daily_prices WHERE symbol = ? AND date >= ?",
        (symbol, cutoff),
    ).fetchall()
    return {r[0] for r in rows}


def prune_old_data(conn: sqlite3.Connection, cutoff: str) -> None:
    deleted = conn.execute(
        "DELETE FROM daily_prices WHERE date < ?", (cutoff,)
    ).rowcount
    conn.commit()
    if deleted:
        print(f"  [prune] Removed {deleted} rows older than {cutoff}")


# ---------------------------------------------------------------------------
# Insert helper
# ---------------------------------------------------------------------------

def _f(v):
    """Convert to float or None."""
    try:
        return None if pd.isna(v) else float(v)
    except (TypeError, ValueError):
        return None


def _i(v):
    """Convert to int or None."""
    try:
        return None if pd.isna(v) else int(v)
    except (TypeError, ValueError):
        return None


def insert_history(
    conn: sqlite3.Connection,
    symbol: str,
    hist: "pd.DataFrame",
    skip_dates: set[str],
) -> int:
    """Insert rows from a yfinance history DataFrame, skipping already-stored dates."""
    inserted = 0
    for ts, row in hist.iterrows():
        date_str = ts.strftime('%Y-%m-%d') if hasattr(ts, 'strftime') else str(ts)[:10]
        if date_str in skip_dates:
            continue
        conn.execute(
            """
            INSERT OR IGNORE INTO daily_prices
                (symbol, date, open, high, low, close, adj_close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                symbol,
                date_str,
                _f(row.get('Open')),
                _f(row.get('High')),
                _f(row.get('Low')),
                _f(row.get('Close')),
                _f(row.get('Adj Close') or row.get('Close')),
                _i(row.get('Volume')),
            ),
        )
        inserted += 1
    conn.commit()
    return inserted


# ---------------------------------------------------------------------------
# Main routine
# ---------------------------------------------------------------------------

def run_fetch(full: bool = False) -> None:
    """
    Main entry point for data fetching.

    full=False (incremental, default):
        For each symbol, fetch from (last stored date + 1 day) to yesterday.
        If the symbol has no data, fetch the full retention window.

    full=True (gap-check):
        For each symbol, compare the entire retention window against the DB
        and insert any missing trading days.

    Uses yf.download() in batches of BATCH_SIZE for dramatically fewer API calls.
    """
    today = date.today()
    yesterday = today - timedelta(days=1)
    cutoff = today - timedelta(days=int(DATA_RETENTION_YEARS * 365.25))
    cutoff_str = cutoff.strftime('%Y-%m-%d')
    yesterday_str = yesterday.strftime('%Y-%m-%d')

    print(f"\n{'='*60}")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] OHLCV fetch started")
    print(f"  Mode      : {'full gap-check' if full else 'incremental'}")
    print(f"  Retention : {DATA_RETENTION_YEARS} year(s)")
    print(f"  Window    : {cutoff_str} → {yesterday_str}")
    print(f"{'='*60}")

    with open(STOCKS_JSON, 'r', encoding='utf-8') as fh:
        stocks_raw = json.load(fh)

    # Deduplicate by symbol
    seen: dict[str, dict] = {}
    for s in stocks_raw:
        seen[s['symbol']] = s
    stocks = list(seen.values())

    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    init_table(conn)
    prune_old_data(conn, cutoff_str)

    # ------------------------------------------------------------------
    # Phase 1: scan DB to determine which symbols need fetching
    # ------------------------------------------------------------------
    print("\n  Scanning existing data...", flush=True)
    to_fetch: list[tuple[str, str, date, set]] = []  # (symbol, name, fetch_start, skip_dates)
    skipped = 0

    for stock in stocks:
        symbol = stock['symbol']
        name = stock.get('name', symbol)

        if full:
            existing = get_existing_dates(conn, symbol, cutoff_str)
            fetch_start = cutoff
        else:
            last_date_str = get_last_date(conn, symbol, cutoff_str)
            if last_date_str is None:
                fetch_start = cutoff
                existing = set()
            else:
                last_date_obj = datetime.strptime(last_date_str, '%Y-%m-%d').date()
                if last_date_obj >= yesterday:
                    skipped += 1
                    continue
                fetch_start = last_date_obj + timedelta(days=1)
                existing = set()

        if fetch_start > yesterday:
            skipped += 1
            continue

        to_fetch.append((symbol, name, fetch_start, existing))

    n_to_fetch = len(to_fetch)
    print(f"  {skipped} already up-to-date  |  {n_to_fetch} to fetch", flush=True)

    total_inserted = 0

    if n_to_fetch == 0:
        conn.close()
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Finished.")
        print(f"  Inserted : 0 rows")
        print(f"  Skipped  : {skipped} symbols (already up-to-date)")
        print(f"  DB       : {DB_PATH}")
        return

    # ------------------------------------------------------------------
    # Phase 2: batch download and insert
    # ------------------------------------------------------------------
    n_batches = (n_to_fetch + BATCH_SIZE - 1) // BATCH_SIZE

    for batch_idx in range(n_batches):
        batch = to_fetch[batch_idx * BATCH_SIZE:(batch_idx + 1) * BATCH_SIZE]
        symbol_list = [s[0] for s in batch]
        min_start = min(s[2] for s in batch)

        print(
            f"\n>>> Batch {batch_idx + 1}/{n_batches}"
            f" ({len(batch)} symbols, from {min_start.strftime('%Y-%m-%d')})",
            flush=True,
        )

        # Fetch the whole batch in a single API call
        raw_map: dict[str, pd.DataFrame] = {}
        try:
            if len(symbol_list) == 1:
                df = yf.download(
                    symbol_list[0],
                    start=min_start.strftime('%Y-%m-%d'),
                    end=(yesterday + timedelta(days=1)).strftime('%Y-%m-%d'),
                    auto_adjust=False,
                    progress=False,
                )
                raw_map[symbol_list[0]] = df
            else:
                raw = yf.download(
                    symbol_list,
                    start=min_start.strftime('%Y-%m-%d'),
                    end=(yesterday + timedelta(days=1)).strftime('%Y-%m-%d'),
                    auto_adjust=False,
                    progress=False,
                    group_by='ticker',
                )
                for sym in symbol_list:
                    try:
                        sym_df = raw[sym].copy().dropna(how='all')
                        raw_map[sym] = sym_df
                    except Exception:
                        raw_map[sym] = pd.DataFrame()
        except Exception as exc:
            print(f"  Batch download error: {exc}", flush=True)
            for sym_idx, (symbol, name, _, _) in enumerate(batch):
                pos = batch_idx * BATCH_SIZE + sym_idx + 1
                print(f"[{pos}/{n_to_fetch}] {symbol} ({name}) - skipped (batch error)", flush=True)
            time.sleep(3)
            continue

        # Process each symbol in the batch
        for sym_idx, (symbol, name, fetch_start, skip_dates) in enumerate(batch):
            pos = batch_idx * BATCH_SIZE + sym_idx + 1
            hist = raw_map.get(symbol, pd.DataFrame())

            if hist is None or hist.empty:
                print(f"[{pos}/{n_to_fetch}] {symbol} ({name}) - no data", flush=True)
                continue

            # Trim to this symbol's individual start date
            # (batch may have fetched earlier rows for symbols with older min_start)
            start_str = fetch_start.strftime('%Y-%m-%d')
            date_strs = hist.index.strftime('%Y-%m-%d')
            hist = hist[date_strs >= start_str]

            if hist.empty:
                print(f"[{pos}/{n_to_fetch}] {symbol} ({name}) - no new data", flush=True)
                continue

            n = insert_history(conn, symbol, hist, skip_dates)
            total_inserted += n
            print(f"[{pos}/{n_to_fetch}] {symbol} ({name}) +{n} rows", flush=True)

        time.sleep(1)  # polite pause between batches

    conn.close()
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Finished.")
    print(f"  Inserted : {total_inserted} rows")
    print(f"  Skipped  : {skipped} symbols (already up-to-date)")
    print(f"  DB       : {DB_PATH}")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='Fetch Taiwan stock daily OHLCV data from Yahoo Finance'
    )
    parser.add_argument(
        '--full',
        action='store_true',
        help=(
            'Full gap-check mode: scan the entire retention window for '
            'missing trading days instead of only fetching recent data'
        ),
    )
    args = parser.parse_args()
    run_fetch(full=args.full)
