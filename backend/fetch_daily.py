#!/usr/bin/env python3
"""
Fetch Taiwan stock data from yfinance and store in SQLite.

Usage:
    python fetch_daily.py

This script reads tw_stocks.json, queries yfinance for each symbol,
and upserts the results into the SQLite database at ../data/stocks.db.
"""

import json
import math
import sqlite3
import os
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, FIRST_COMPLETED
from datetime import datetime

# Force UTF-8 output on Windows to prevent mojibake with Chinese characters
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding and sys.stderr.encoding.lower() != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

try:
    import yfinance as yf
except ImportError:
    print("yfinance not found – installing...")
    os.system(f"{sys.executable} -m pip install yfinance")
    import yfinance as yf

from sector_mapping import map_sector, map_industry

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, '..', 'data', 'stocks.db')
STOCKS_JSON = os.path.join(BASE_DIR, 'tw_stocks.json')

MAX_WORKERS = 5          # yfinance 0.2.x handles concurrent crumbs safely
REQUEST_DELAY = 0.3      # seconds between requests

_crumb_lock = threading.Lock()
_crumb_refreshing = False


def _refresh_crumb() -> None:
    """Force yfinance to re-acquire a fresh crumb."""
    global _crumb_refreshing
    with _crumb_lock:
        if _crumb_refreshing:
            return
        _crumb_refreshing = True
    try:
        yf.Ticker("^TWII").fast_info
    except Exception:
        pass
    finally:
        with _crumb_lock:
            _crumb_refreshing = False


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS stocks (
    symbol TEXT PRIMARY KEY,
    name TEXT,
    sector TEXT,
    sector_en TEXT,
    industry TEXT,
    industry_en TEXT,
    market_type TEXT,
    price REAL,
    pe_ratio REAL,
    forward_pe REAL,
    dividend_yield REAL,
    market_cap INTEGER,
    volume INTEGER,
    week_52_high REAL,
    week_52_low REAL,
    revenue_growth REAL,
    monthly_revenue REAL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

CREATE_INDEXES_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_sector ON stocks(sector)",
    "CREATE INDEX IF NOT EXISTS idx_pe ON stocks(pe_ratio)",
    "CREATE INDEX IF NOT EXISTS idx_yield ON stocks(dividend_yield)",
    "CREATE INDEX IF NOT EXISTS idx_cap ON stocks(market_cap)",
]


def _safe_float(v) -> float | None:
    """Return float or None; filters out Infinity and NaN."""
    if v is None:
        return None
    try:
        f = float(v)
        return None if math.isinf(f) or math.isnan(f) else f
    except (TypeError, ValueError):
        return None


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute(CREATE_TABLE_SQL)
    for idx_sql in CREATE_INDEXES_SQL:
        conn.execute(idx_sql)
    # Migrate existing DB: add new columns if missing
    existing = {row[1] for row in conn.execute("PRAGMA table_info(stocks)")}
    for col, definition in [
        ('industry',       'TEXT'),
        ('industry_en',    'TEXT'),
        ('monthly_revenue', 'REAL'),
    ]:
        if col not in existing:
            conn.execute(f"ALTER TABLE stocks ADD COLUMN {col} {definition}")
    conn.commit()


def determine_market_type(symbol: str) -> str:
    """Fallback: infer market type from symbol suffix."""
    if symbol.upper().endswith('.TWO'):
        return 'otc'
    return 'listed'


def _fetch_info(symbol: str) -> dict:
    """Run ticker.info in an isolated executor so we can apply a hard timeout."""
    return yf.Ticker(symbol).info


def fetch_stock(symbol: str, name: str) -> dict | None:
    """Fetch stock info from yfinance. Retries up to 3 times on rate-limit errors."""
    TIMEOUT = 20  # seconds per attempt — prevents curl_cffi from hanging forever
    for attempt in range(3):
        try:
            time.sleep(REQUEST_DELAY if attempt == 0 else 2)
            with ThreadPoolExecutor(max_workers=1) as _ex:
                _f = _ex.submit(_fetch_info, symbol)
                try:
                    info = _f.result(timeout=TIMEOUT)
                except TimeoutError:
                    print(f"  Timeout fetching {symbol}, skipping...")
                    return None
            if not info or not isinstance(info, dict):
                return None

            # Price: prefer currentPrice, fall back through alternatives
            price = (
                info.get('currentPrice')
                or info.get('regularMarketPrice')
                or info.get('previousClose')
            )

            pe_ratio = _safe_float(info.get('trailingPE'))
            forward_pe = _safe_float(info.get('forwardPE'))

            # yfinance already returns dividendYield as a percentage for TW stocks (e.g. 16.29 = 16.29%)
            dividend_yield = info.get('dividendYield')

            market_cap = info.get('marketCap')
            volume = info.get('regularMarketVolume') or info.get('averageVolume')
            week_52_high = info.get('fiftyTwoWeekHigh')
            week_52_low = info.get('fiftyTwoWeekLow')

            sector_en = info.get('sector', '') or ''
            sector = map_sector(sector_en)
            industry_en = info.get('industry', '') or ''
            industry = map_industry(industry_en)
            market_type = determine_market_type(symbol)  # overridden by caller if JSON has market_type

            # Prefer Chinese name from tw_stocks.json; fall back to yfinance name only if missing
            stock_name = name or info.get('shortName') or info.get('longName')

            return {
                'symbol': symbol,
                'name': stock_name,
                'sector': sector,
                'sector_en': sector_en,
                'industry': industry,
                'industry_en': industry_en,
                'market_type': market_type,
                'price': price,
                'pe_ratio': pe_ratio,
                'forward_pe': forward_pe,
                'dividend_yield': dividend_yield,
                'market_cap': market_cap,
                'volume': volume,
                'week_52_high': week_52_high,
                'week_52_low': week_52_low,
            }
        except Exception as e:
            err = str(e)
            is_rate_limit = '429' in err or 'Too Many Requests' in err
            is_crumb = 'Crumb' in err or ('401' in err and 'Unauthorized' in err)
            if is_rate_limit and attempt < 2:
                wait = 15 * (attempt + 1)
                print(f"  Rate limited on {symbol}, waiting {wait}s (attempt {attempt + 1}/3)...")
                time.sleep(wait)
                continue
            elif is_crumb and attempt < 2:
                print(f"  Crumb error on {symbol}, refreshing session (attempt {attempt + 1}/3)...")
                _refresh_crumb()
                time.sleep(3)
                continue
            print(f"  Error fetching {symbol}: {e}")
            return None
    return None


def upsert_stock(conn: sqlite3.Connection, data: dict) -> None:
    # Use INSERT OR IGNORE + UPDATE pattern so that monthly_revenue
    # (written by fetch_monthly_revenue.py) is not overwritten by this script.
    conn.execute(
        """
        INSERT INTO stocks
            (symbol, name, sector, sector_en, industry, industry_en, market_type,
             price, pe_ratio, forward_pe, dividend_yield, market_cap, volume,
             week_52_high, week_52_low, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(symbol) DO UPDATE SET
            name          = excluded.name,
            sector        = excluded.sector,
            sector_en     = excluded.sector_en,
            industry      = excluded.industry,
            industry_en   = excluded.industry_en,
            market_type   = excluded.market_type,
            price         = excluded.price,
            pe_ratio      = excluded.pe_ratio,
            forward_pe    = excluded.forward_pe,
            dividend_yield = excluded.dividend_yield,
            market_cap    = excluded.market_cap,
            volume        = excluded.volume,
            week_52_high  = excluded.week_52_high,
            week_52_low   = excluded.week_52_low,
            updated_at    = excluded.updated_at
        """,
        (
            data['symbol'],
            data['name'],
            data['sector'],
            data['sector_en'],
            data['industry'],
            data['industry_en'],
            data['market_type'],
            data['price'],
            data['pe_ratio'],
            data['forward_pe'],
            data['dividend_yield'],
            data['market_cap'],
            data['volume'],
            data['week_52_high'],
            data['week_52_low'],
            datetime.now().isoformat(),
        ),
    )


def _is_fresh_today(conn: sqlite3.Connection) -> tuple[bool, int, int]:
    """Return (is_fresh, fresh_count, total_count). Fresh = >=90% updated today."""
    today = datetime.now().strftime('%Y-%m-%d')
    total = conn.execute("SELECT COUNT(*) FROM stocks").fetchone()[0]
    fresh = conn.execute(
        "SELECT COUNT(*) FROM stocks WHERE date(updated_at) = ?", (today,)
    ).fetchone()[0]
    return (total > 0 and fresh >= total * 0.9), fresh, total


def main() -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    with open(STOCKS_JSON, 'r', encoding='utf-8') as f:
        stocks = json.load(f)

    conn_check = sqlite3.connect(DB_PATH)
    init_db(conn_check)
    if '--skip-if-fresh' in sys.argv:
        is_fresh, fresh_count, total_count = _is_fresh_today(conn_check)
        if is_fresh:
            print(f"快照資料今日已更新（{fresh_count}/{total_count} 支），跳過抓取")
            conn_check.close()
            return
    conn_check.close()

    # De-duplicate by symbol (keep last occurrence)
    seen: dict[str, dict] = {}
    for s in stocks:
        seen[s['symbol']] = s
    stocks = list(seen.values())

    total = len(stocks)
    print(f"Fetching {total} stocks into {DB_PATH}  (workers={MAX_WORKERS})")

    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    db_lock = threading.Lock()
    init_db(conn)

    success = 0
    failed = 0
    completed = 0
    print_lock = threading.Lock()

    def process(stock: dict) -> bool:
        nonlocal success, failed, completed
        symbol = stock['symbol']
        name = stock['name']
        market_type_from_json = stock.get('market_type')

        data = fetch_stock(symbol, name)

        with print_lock:
            completed_now = completed + 1
            completed += 1
            if data:
                if market_type_from_json:
                    data['market_type'] = market_type_from_json
                with db_lock:
                    upsert_stock(conn, data)
                    conn.commit()
                success += 1
                print(
                    f"[{completed_now}/{total}] {symbol} ({name})  "
                    f"OK  price={data['price']}  pe={data['pe_ratio']}  "
                    f"yield={data['dividend_yield']}%  sector={data['sector']}"
                )
                return True
            else:
                failed += 1
                print(f"[{completed_now}/{total}] {symbol} ({name})  FAILED")
                return False

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(process, s) for s in stocks]
        for f in as_completed(futures):
            f.result()  # surface any unexpected exceptions

    conn.close()
    print(f"\nFinished. Success: {success}  Failed: {failed}")
    print(f"Database: {os.path.abspath(DB_PATH)}")


if __name__ == '__main__':
    main()
