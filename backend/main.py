import os
import subprocess
import sys
import threading
from contextlib import asynccontextmanager
from datetime import datetime

# Load .env before anything else so env vars are available to all modules
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))

import aiosqlite
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from database import init_db, get_last_updated, get_stock_count, get_price_date_range, DB_PATH
from models import ScreenRequest, ScreenResponse, StockResult, Filters
from screener import build_query
from ai_parser import parse_natural_language

# ---------------------------------------------------------------------------
# Config from .env
# ---------------------------------------------------------------------------

AI_ENABLED = os.getenv('AI_ENABLED', 'true').lower() == 'true'

_fetch_time = os.getenv('FETCH_SCHEDULE_TIME', '17:30')
try:
    _schedule_hour, _schedule_minute = map(int, _fetch_time.split(':'))
except ValueError:
    _schedule_hour, _schedule_minute = 17, 30

# ---------------------------------------------------------------------------
# Script paths
# ---------------------------------------------------------------------------

_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
_FETCH_DAILY_SCRIPT          = os.path.join(_BACKEND_DIR, 'fetch_daily.py')
_FETCH_MONTHLY_REVENUE_SCRIPT = os.path.join(_BACKEND_DIR, 'scripts', 'fetch_monthly_revenue.py')
_FETCH_OHLCV_SCRIPT          = os.path.join(_BACKEND_DIR, 'scripts', 'fetch_ohlcv.py')
_LOG_PATH = os.path.abspath(os.path.join(_BACKEND_DIR, '..', 'data', 'fetch.log'))

_running_procs: list[subprocess.Popen] = []
_fetch_thread: threading.Thread | None = None
_fetch_current_step: int = 0          # 1-3 while running, 0 when idle
_fetch_steps_done: list[bool] = [False, False, False]


def _is_fetching() -> bool:
    """Return True if the fetch thread or any subprocess is still running."""
    global _running_procs, _fetch_thread
    _running_procs = [p for p in _running_procs if p.poll() is None]
    thread_alive = _fetch_thread is not None and _fetch_thread.is_alive()
    return bool(_running_procs) or thread_alive


def _spawn(script: str, *args: str) -> None:
    """Start a Python script as a fire-and-forget subprocess.
    stdout/stderr are appended to the shared fetch log file so the frontend
    can display progress. On Windows, CREATE_NEW_PROCESS_GROUP isolates the
    child from Ctrl+C signals.
    """
    log_fh = open(_LOG_PATH, 'ab')
    try:
        kwargs = dict(stdout=log_fh, stderr=log_fh)
        if sys.platform == 'win32':
            kwargs['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP
        proc = subprocess.Popen([sys.executable, script, *args], **kwargs)
        _running_procs.append(proc)
    finally:
        log_fh.close()  # subprocess inherits its own fd copy


_STEP_LABELS = [
    "━━ Step 1/3 ── 快照資料 (PE、殖利率、市值…) ━━",
    "━━ Step 2/3 ── TWSE 月營收 ━━",
    "━━ Step 3/3 ── OHLCV 歷史價格 (增量) ━━",
]


def _run_fetches_sequential(force: bool = False) -> None:
    """Run all fetch scripts sequentially in a background thread."""
    global _fetch_current_step, _fetch_steps_done
    _fetch_steps_done = [False, False, False]
    scripts = [_FETCH_DAILY_SCRIPT, _FETCH_MONTHLY_REVENUE_SCRIPT, _FETCH_OHLCV_SCRIPT]
    extra_args = [] if force else ['--skip-if-fresh']
    for i, script in enumerate(scripts):
        _fetch_current_step = i + 1
        with open(_LOG_PATH, 'ab') as log_fh:
            log_fh.write(f"\n{_STEP_LABELS[i]}\n".encode())
        with open(_LOG_PATH, 'ab') as log_fh:
            kwargs = dict(stdout=log_fh, stderr=log_fh)
            if sys.platform == 'win32':
                kwargs['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP
            proc = subprocess.Popen([sys.executable, script, *extra_args], **kwargs)
            _running_procs.append(proc)
            proc.wait()
            _running_procs[:] = [p for p in _running_procs if p.poll() is None]
        _fetch_steps_done[i] = True
        with open(_LOG_PATH, 'ab') as log_fh:
            log_fh.write(f"━━ Step {i+1}/3 完成 ━━\n".encode())
    _fetch_current_step = 0


def run_all_fetches(force: bool = False) -> None:
    """Trigger all fetch scripts sequentially. force=True skips freshness check."""
    if _is_fetching():
        return  # already running, ignore duplicate trigger
    os.makedirs(os.path.dirname(_LOG_PATH), exist_ok=True)
    mode_label = "強制重新抓取" if force else "自動更新（已是最新則跳過）"
    with open(_LOG_PATH, 'w', encoding='utf-8') as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 開始抓取資料 ({mode_label})...\n\n")
    global _fetch_thread
    _fetch_thread = threading.Thread(target=_run_fetches_sequential, args=(force,), daemon=True)
    _fetch_thread.start()


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

scheduler = AsyncIOScheduler()

# ---------------------------------------------------------------------------
# Application lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Initialise database tables
    init_db()

    # 2. Run data fetch immediately on startup (non-blocking subprocesses)
    run_all_fetches()

    # 3. Schedule a daily fetch at the configured time
    scheduler.add_job(
        run_all_fetches,
        'cron',
        hour=_schedule_hour,
        minute=_schedule_minute,
        id='daily_fetch',
        replace_existing=True,
    )
    scheduler.start()
    print(
        f"Scheduler started – daily fetch at "
        f"{_schedule_hour:02d}:{_schedule_minute:02d}  |  AI_ENABLED={AI_ENABLED}"
    )

    yield

    scheduler.shutdown()


# ---------------------------------------------------------------------------
# App instance
# ---------------------------------------------------------------------------

app = FastAPI(title="台股 AI 篩選器", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/api/health")
async def health():
    """Health check – returns DB stats."""
    return {
        "status": "ok",
        "ai_enabled": AI_ENABLED,
        "fetch_schedule": f"{_schedule_hour:02d}:{_schedule_minute:02d}",
        "last_updated": get_last_updated(),
        "stock_count": get_stock_count(),
    }


@app.get("/api/sectors")
async def get_sectors():
    """Return all distinct sector names that exist in the database."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT DISTINCT sector FROM stocks WHERE sector IS NOT NULL ORDER BY sector"
        ) as cursor:
            rows = await cursor.fetchall()
    return {"sectors": [r[0] for r in rows]}


@app.get("/api/industries")
async def get_industries():
    """Return all distinct industry names that exist in the database."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT DISTINCT industry FROM stocks WHERE industry IS NOT NULL AND industry != '' ORDER BY industry"
        ) as cursor:
            rows = await cursor.fetchall()
    return {"industries": [r[0] for r in rows]}


@app.get("/api/industry_options")
async def get_industry_options():
    """Return merged industry/sector options using the same fallback logic as the display:
    industry if present, otherwise sector. Sorted alphabetically."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """
            SELECT DISTINCT COALESCE(NULLIF(industry, ''), sector) AS label
            FROM stocks
            WHERE label IS NOT NULL
            ORDER BY label
            """
        ) as cursor:
            rows = await cursor.fetchall()
    return {"options": [r[0] for r in rows]}


@app.get("/api/fields")
async def get_fields():
    """Return metadata for every filterable/sortable field."""
    return {
        "fields": [
            {"key": "pe_ratio",       "label": "本益比",           "type": "number"},
            {"key": "forward_pe",     "label": "預估本益比",       "type": "number"},
            {"key": "dividend_yield", "label": "殖利率 近12月 (%)", "type": "number"},
            {"key": "market_cap",     "label": "市值",             "type": "number"},
            {"key": "price",          "label": "股價",             "type": "number"},
            {"key": "volume",         "label": "成交量",           "type": "number"},
            {"key": "week_52_high",    "label": "52週最高",              "type": "number"},
            {"key": "week_52_low",    "label": "52週最低",              "type": "number"},
            {"key": "monthly_revenue", "label": "最近月營收 (千元)",     "type": "number"},
            {"key": "sector",         "label": "大產業",                "type": "select"},
            {"key": "industry",       "label": "細產業",           "type": "select"},
            {"key": "market_type",    "label": "市場別",           "type": "select",
             "options": ["listed", "otc", "emerging"]},
        ]
    }


@app.post("/api/screen", response_model=ScreenResponse)
async def screen(req: ScreenRequest):
    """
    Main screening endpoint.

    Supports two modes:
    - ``manual``: caller supplies a structured ``filters`` object.
    - ``natural_language``: caller supplies a free-text ``query`` which is
      parsed by Claude into a ``Filters`` object automatically.
    """
    try:
        if req.mode == 'natural_language':
            if not req.query:
                raise HTTPException(
                    status_code=400,
                    detail="'query' is required when mode is 'natural_language'",
                )
            if not AI_ENABLED:
                raise HTTPException(
                    status_code=503,
                    detail="AI 功能已關閉（AI_ENABLED=false），請使用手動篩選模式",
                )
            filters, ai_reason = await parse_natural_language(req.query)
        else:
            ai_reason = None
            if not req.filters:
                filters = Filters(conditions=[], block_logic='AND')
            else:
                filters = req.filters

        select_sql, count_sql, select_params, count_params = build_query(
            filters,
            sort_by=req.sort_by,
            sort_order=req.sort_order,
            page=req.page,
            page_size=req.page_size,
        )

        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row

            async with db.execute(count_sql, count_params) as cursor:
                count_row = await cursor.fetchone()
                total = count_row[0] if count_row else 0

            async with db.execute(select_sql, select_params) as cursor:
                rows = await cursor.fetchall()

        results = [StockResult(**dict(row)) for row in rows]

        return ScreenResponse(
            mode=req.mode,
            parsed_conditions=filters if filters.conditions else None,
            ai_reason=ai_reason or None,
            results=results,
            total=total,
            page=req.page,
            page_size=req.page_size,
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")


@app.post("/api/fetch")
async def trigger_fetch():
    """
    Manually kick off a background data-fetch (snapshot + OHLCV history).
    Always forces a full re-fetch regardless of freshness.
    """
    run_all_fetches(force=True)
    return {"status": "started", "message": "快照資料與 OHLCV 歷史資料抓取已在背景執行"}


@app.get("/api/data/range")
async def data_range():
    """Return the MIN/MAX date stored in daily_prices."""
    return get_price_date_range()


@app.post("/api/fetch/full")
async def trigger_full_fetch():
    """
    Kick off a full gap-check OHLCV backfill (fetch_ohlcv.py --full).
    Use this after changing DATA_RETENTION_YEARS in .env without restarting.
    """
    os.makedirs(os.path.dirname(_LOG_PATH), exist_ok=True)
    with open(_LOG_PATH, 'w', encoding='utf-8') as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 開始完整回補資料 (--full)...\n")
        f.write("  掃描整個保留窗口，補齊所有缺漏的交易日\n\n")
    _spawn(_FETCH_OHLCV_SCRIPT, '--full')
    return {"status": "started", "message": "OHLCV 完整回補已在背景執行"}


@app.get("/api/fetch/log")
async def fetch_log():
    """Return recent lines from the fetch log and whether a fetch is still running."""
    running = _is_fetching()
    if not os.path.exists(_LOG_PATH):
        return {"running": running, "current_step": _fetch_current_step,
                "steps_done": _fetch_steps_done, "lines": []}
    try:
        with open(_LOG_PATH, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
    except OSError:
        return {"running": running, "current_step": _fetch_current_step,
                "steps_done": _fetch_steps_done, "lines": []}
    return {
        "running": running,
        "current_step": _fetch_current_step,
        "steps_done": _fetch_steps_done,
        "lines": [l.rstrip('\n') for l in lines[-300:]],
    }


@app.get("/api/stock/{symbol}/prices")
async def stock_prices(symbol: str, days: int = 90):
    """Return OHLCV history for a single stock from daily_prices table."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT date, open, high, low, close, adj_close, volume
               FROM daily_prices WHERE symbol = ?
               ORDER BY date DESC LIMIT ?""",
            (symbol, days),
        ) as cursor:
            rows = await cursor.fetchall()
    return {"symbol": symbol, "prices": [dict(r) for r in reversed(rows)]}


