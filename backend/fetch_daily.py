#!/usr/bin/env python3
"""
Fetch Taiwan stock data from yfinance and store in SQLite.

Usage:
    python fetch_daily.py

This script reads tw_stocks.json, queries yfinance for each symbol,
and upserts the results into the SQLite database at ../data/stocks.db.
"""

import json
import sqlite3
import os
import sys
import time
from datetime import datetime

try:
    import yfinance as yf
except ImportError:
    print("yfinance not found – installing...")
    os.system(f"{sys.executable} -m pip install yfinance")
    import yfinance as yf

from sector_mapping import map_sector

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, '..', 'data', 'stocks.db')
STOCKS_JSON = os.path.join(BASE_DIR, 'tw_stocks.json')

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS stocks (
    symbol TEXT PRIMARY KEY,
    name TEXT,
    sector TEXT,
    sector_en TEXT,
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
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

CREATE_INDEXES_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_sector ON stocks(sector)",
    "CREATE INDEX IF NOT EXISTS idx_pe ON stocks(pe_ratio)",
    "CREATE INDEX IF NOT EXISTS idx_yield ON stocks(dividend_yield)",
    "CREATE INDEX IF NOT EXISTS idx_cap ON stocks(market_cap)",
]


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute(CREATE_TABLE_SQL)
    for idx_sql in CREATE_INDEXES_SQL:
        conn.execute(idx_sql)
    conn.commit()


def determine_market_type(symbol: str) -> str:
    """Fallback: infer market type from symbol suffix."""
    if symbol.upper().endswith('.TWO'):
        return 'otc'
    return 'listed'


def fetch_stock(symbol: str, name: str) -> dict | None:
    """Fetch stock info from yfinance.  Returns a dict or None on failure."""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info

        # Price: prefer currentPrice, fall back through alternatives
        price = (
            info.get('currentPrice')
            or info.get('regularMarketPrice')
            or info.get('previousClose')
        )

        pe_ratio = info.get('trailingPE')
        forward_pe = info.get('forwardPE')

        # yfinance already returns dividendYield as a percentage for TW stocks (e.g. 16.29 = 16.29%)
        dividend_yield = info.get('dividendYield')

        market_cap = info.get('marketCap')
        volume = info.get('regularMarketVolume') or info.get('averageVolume')
        week_52_high = info.get('fiftyTwoWeekHigh')
        week_52_low = info.get('fiftyTwoWeekLow')
        revenue_growth = info.get('revenueGrowth')

        sector_en = info.get('sector', '') or ''
        sector = map_sector(sector_en)
        market_type = determine_market_type(symbol)  # overridden by caller if JSON has market_type

        # Prefer Chinese name from tw_stocks.json; fall back to yfinance name only if missing
        stock_name = name or info.get('shortName') or info.get('longName')

        return {
            'symbol': symbol,
            'name': stock_name,
            'sector': sector,
            'sector_en': sector_en,
            'market_type': market_type,
            'price': price,
            'pe_ratio': pe_ratio,
            'forward_pe': forward_pe,
            'dividend_yield': dividend_yield,
            'market_cap': market_cap,
            'volume': volume,
            'week_52_high': week_52_high,
            'week_52_low': week_52_low,
            'revenue_growth': revenue_growth,
        }
    except Exception as e:
        print(f"  Error fetching {symbol}: {e}")
        return None


def upsert_stock(conn: sqlite3.Connection, data: dict) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO stocks
            (symbol, name, sector, sector_en, market_type, price, pe_ratio, forward_pe,
             dividend_yield, market_cap, volume, week_52_high, week_52_low, revenue_growth,
             updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data['symbol'],
            data['name'],
            data['sector'],
            data['sector_en'],
            data['market_type'],
            data['price'],
            data['pe_ratio'],
            data['forward_pe'],
            data['dividend_yield'],
            data['market_cap'],
            data['volume'],
            data['week_52_high'],
            data['week_52_low'],
            data['revenue_growth'],
            datetime.now().isoformat(),
        ),
    )


def main() -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    with open(STOCKS_JSON, 'r', encoding='utf-8') as f:
        stocks = json.load(f)

    # De-duplicate by symbol (keep last occurrence)
    seen: dict[str, dict] = {}
    for s in stocks:
        seen[s['symbol']] = s
    stocks = list(seen.values())

    print(f"Fetching {len(stocks)} stocks into {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    success = 0
    failed = 0

    for i, stock in enumerate(stocks):
        symbol = stock['symbol']
        name = stock['name']
        market_type_from_json = stock.get('market_type')
        print(f"[{i + 1}/{len(stocks)}] {symbol} ({name}) ...", end=' ', flush=True)

        data = fetch_stock(symbol, name)
        if data:
            # Use market_type from tw_stocks.json (distinguishes emerging from otc)
            if market_type_from_json:
                data['market_type'] = market_type_from_json
            upsert_stock(conn, data)
            conn.commit()
            success += 1
            print(
                f"OK  price={data['price']}  pe={data['pe_ratio']}  "
                f"yield={data['dividend_yield']}%  sector={data['sector']}"
            )
        else:
            failed += 1
            print("FAILED")

        # Polite rate-limiting: pause every 10 requests
        if (i + 1) % 10 == 0:
            time.sleep(2)
        else:
            time.sleep(0.5)

    conn.close()
    print(f"\nFinished. Success: {success}  Failed: {failed}")
    print(f"Database: {os.path.abspath(DB_PATH)}")


if __name__ == '__main__':
    main()
