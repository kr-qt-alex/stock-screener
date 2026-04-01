import aiosqlite
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'stocks.db')

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

CREATE_DAILY_PRICES_SQL = """
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

CREATE_DAILY_INDEXES_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_dp_symbol ON daily_prices(symbol)",
    "CREATE INDEX IF NOT EXISTS idx_dp_date   ON daily_prices(date)",
]


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(CREATE_TABLE_SQL)
    for idx_sql in CREATE_INDEXES_SQL:
        conn.execute(idx_sql)
    conn.execute(CREATE_DAILY_PRICES_SQL)
    for idx_sql in CREATE_DAILY_INDEXES_SQL:
        conn.execute(idx_sql)
    conn.commit()
    conn.close()


async def get_db():
    return await aiosqlite.connect(DB_PATH)


def get_last_updated():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.execute("SELECT MAX(updated_at) FROM stocks")
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    except Exception:
        return None


def get_stock_count():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.execute("SELECT COUNT(*) FROM stocks")
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else 0
    except Exception:
        return 0


def get_price_date_range() -> dict:
    """Return the MIN and MAX dates stored in daily_prices, or None if empty."""
    try:
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute(
            "SELECT MIN(date), MAX(date) FROM daily_prices"
        ).fetchone()
        conn.close()
        return {"from": row[0], "to": row[1]} if row and row[0] else {"from": None, "to": None}
    except Exception:
        return {"from": None, "to": None}
