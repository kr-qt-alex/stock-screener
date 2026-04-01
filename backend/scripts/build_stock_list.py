#!/usr/bin/env python3
"""
Build a complete tw_stocks.json from TWSE / TPEX official sources.

  上市 (listed)   → TWSE OpenAPI  exchangeReport/STOCK_DAY_ALL
                    Fields: Code, Name
                    Returns only stocks that traded today → active only

  上櫃 (otc)      → TPEX OpenAPI  tpex_mainboard_peratio_analysis
                    Fields: SecuritiesCompanyCode, CompanyName
                    Returns only currently listed mainboard OTC stocks

  興櫃 (emerging) → TWSE/TPEX ISIN  strMode=5
                    興櫃 market is newer; ISIN count (~350) closely matches
                    the actual active count, so no extra filtering needed.

yfinance symbol suffixes:
  上市  → {code}.TW
  上櫃  → {code}.TWO
  興櫃  → {code}.TWO  (TPEX-managed; yfinance data availability may vary)

Usage:
  cd backend
  python scripts/build_stock_list.py
"""

import json
import os
import re
import sys
import time

try:
    import requests
    import urllib3
except ImportError:
    os.system(f"{sys.executable} -m pip install requests")
    import requests
    import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT = os.path.join(BACKEND_DIR, 'tw_stocks.json')

HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; tw-screener/1.0)'}


def _get_json(url: str) -> list[dict]:
    resp = requests.get(url, headers=HEADERS, timeout=30, verify=False)
    resp.raise_for_status()
    return json.loads(resp.content.decode('utf-8'))


def _is_valid_code(code: str) -> bool:
    """Accept 4-6 digit numeric codes (stocks + ETFs)."""
    return bool(re.match(r'^\d{4,6}$', code))


# ---------------------------------------------------------------------------
# 上市 — TWSE exchangeReport/STOCK_DAY_ALL
# Returns all stocks that traded on the latest available trading day.
# ---------------------------------------------------------------------------

def fetch_listed() -> list[tuple[str, str]]:
    data = _get_json('https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL')
    results = []
    for item in data:
        code = str(item.get('Code', '')).strip()
        name = str(item.get('Name', '')).strip()
        if _is_valid_code(code) and name:
            results.append((code, name))
    return results


# ---------------------------------------------------------------------------
# 上櫃 — TPEX tpex_mainboard_peratio_analysis
# Returns currently listed mainboard OTC stocks.
# ---------------------------------------------------------------------------

def fetch_otc() -> list[tuple[str, str]]:
    data = _get_json(
        'https://www.tpex.org.tw/openapi/v1/tpex_mainboard_peratio_analysis'
    )
    results = []
    for item in data:
        code = str(item.get('SecuritiesCompanyCode', '')).strip()
        name = str(item.get('CompanyName', '')).strip()
        if _is_valid_code(code) and name:
            results.append((code, name))
    return results


# ---------------------------------------------------------------------------
# 興櫃 — ISIN strMode=5
# TPEX JSON APIs for ESM are unavailable; ISIN is used as fallback.
# The 興櫃 market is newer so the ISIN count closely matches active stocks.
# ---------------------------------------------------------------------------

def fetch_emerging() -> list[tuple[str, str]]:
    url = 'https://isin.twse.com.tw/isin/C_public.jsp?strMode=5'
    resp = requests.get(url, headers=HEADERS, timeout=30, verify=False)
    resp.encoding = 'big5'
    text = resp.text

    results = []
    for m in re.finditer(r'<td[^>]*>(\d{4,6})\u3000([^<\r\n]+)</td>', text):
        code = m.group(1).strip()
        name = m.group(2).strip()
        if _is_valid_code(code) and name:
            results.append((code, name))
    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

FETCHERS = [
    ('listed',   '.TW',  fetch_listed),
    ('otc',      '.TWO', fetch_otc),
    ('emerging', '.TWO', fetch_emerging),
]

LABELS = {'listed': '上市', 'otc': '上櫃', 'emerging': '興櫃'}


def main() -> None:
    all_stocks: list[dict] = []

    for market_type, suffix, fetcher in FETCHERS:
        label = LABELS[market_type]
        print(f'[{label}] 抓取中...', end=' ', flush=True)
        try:
            pairs = fetcher()
        except Exception as e:
            print(f'ERROR: {e}')
            continue
        print(f'{len(pairs)} 檔')

        for code, name in pairs:
            all_stocks.append({
                'symbol': f'{code}{suffix}',
                'name': name,
                'market_type': market_type,
            })
        time.sleep(1)

    # Deduplicate: first occurrence wins
    seen: dict[str, dict] = {}
    for s in all_stocks:
        if s['symbol'] not in seen:
            seen[s['symbol']] = s
    result = list(seen.values())

    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    listed   = sum(1 for s in result if s['market_type'] == 'listed')
    otc      = sum(1 for s in result if s['market_type'] == 'otc')
    emerging = sum(1 for s in result if s['market_type'] == 'emerging')
    print(f'\n完成：上市 {listed} + 上櫃 {otc} + 興櫃 {emerging} = 共 {len(result)} 檔')
    print(f'已寫入 {OUTPUT}')


if __name__ == '__main__':
    main()
