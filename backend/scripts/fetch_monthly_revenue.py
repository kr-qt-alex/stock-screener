#!/usr/bin/env python3
"""
Fetch Taiwan listed-stock monthly revenue from TWSE OpenAPI and store in stocks table.

Source: https://openapi.twse.com.tw/v1/opendata/t187ap05_L
  - Returns all listed (上市) companies for the latest reported month
  - OTC (上櫃) companies are left as NULL (TPEx API requires browser session)

Revenue is stored as INTEGER in 千元 (thousands TWD).
"""

import os
import sys
import sqlite3
import json
from datetime import datetime

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding and sys.stderr.encoding.lower() != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

try:
    from dotenv import load_dotenv
    _env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env')
    load_dotenv(_env_path)
except ImportError:
    pass

try:
    import requests
    import urllib3
except ImportError:
    os.system(f"{sys.executable} -m pip install requests")
    import requests
    import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH  = os.path.join(BASE_DIR, '..', 'data', 'stocks.db')

TWSE_URL = 'https://openapi.twse.com.tw/v1/opendata/t187ap05_L'


def fetch_twse_revenue() -> dict[str, int]:
    """Fetch latest-month revenue for all listed companies from TWSE OpenAPI.

    Returns dict mapping full symbol (e.g. '2330.TW') to revenue in 千元.
    """
    resp = requests.get(TWSE_URL, timeout=30, verify=False)
    resp.raise_for_status()
    data = json.loads(resp.content.decode('utf-8'))

    result: dict[str, int] = {}
    for row in data:
        code = row.get('公司代號', '').strip()
        rev_raw = row.get('營業收入-當月營收', '').replace(',', '').strip()
        if not code or not rev_raw:
            continue
        try:
            result[f'{code}.TW'] = int(rev_raw)
        except ValueError:
            continue
    return result


def update_stocks(conn: sqlite3.Connection, revenue_map: dict[str, int]) -> int:
    updated = 0
    for symbol, revenue in revenue_map.items():
        cur = conn.execute(
            "UPDATE stocks SET monthly_revenue = ? WHERE symbol = ?",
            (revenue, symbol),
        )
        updated += cur.rowcount
    conn.commit()
    return updated


def ensure_column(conn: sqlite3.Connection) -> None:
    existing = {row[1] for row in conn.execute("PRAGMA table_info(stocks)")}
    if 'monthly_revenue' not in existing:
        conn.execute("ALTER TABLE stocks ADD COLUMN monthly_revenue INTEGER")
        conn.commit()


def main() -> None:
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] fetch_monthly_revenue 開始")

    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    ensure_column(conn)

    print("  抓取 TWSE OpenAPI 最近月營收...", end='', flush=True)
    try:
        revenue_map = fetch_twse_revenue()
    except Exception as exc:
        print(f"\n  ERROR: {exc}")
        conn.close()
        return

    if not revenue_map:
        print(" (無資料)")
        conn.close()
        return

    # Show which year-month this covers (for logging)
    print(f" 取得 {len(revenue_map)} 筆")

    updated = update_stocks(conn, revenue_map)
    conn.close()
    print(f"  更新 {updated} 支上市股票月營收")
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] fetch_monthly_revenue 完成")


if __name__ == '__main__':
    main()
