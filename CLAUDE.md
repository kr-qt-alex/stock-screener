# tw-screener — 開發指南 (CLAUDE.md)

台股 AI 篩選器，使用 FastAPI + SQLite 後端、React + Vite 前端，整合 Yahoo Finance 資料與 Anthropic Claude AI。

---

## 專案結構

```
tw-screener/
├── backend/
│   ├── .env                    # 後端設定（需手動建立，勿 commit）
│   ├── main.py                 # FastAPI 應用、路由、排程器
│   ├── models.py               # Pydantic 資料模型
│   ├── database.py             # SQLite schema 初始化與工具函數
│   ├── screener.py             # SQL 查詢建構器
│   ├── ai_parser.py            # Claude 自然語言解析
│   ├── fetch_daily.py          # 股票快照資料抓取（pe、殖利率等）
│   ├── sector_mapping.py       # 產業英文→中文對照
│   ├── tw_stocks.json          # 台股股票清單（symbol + name）
│   ├── requirements.txt        # Python 依賴
│   └── scripts/
│       └── fetch_ohlcv.py      # 每日 OHLCV 盤後資料抓取腳本
├── frontend/
│   ├── src/
│   │   ├── App.jsx             # 主應用、useReducer 狀態管理
│   │   ├── api.js              # Axios API 客戶端
│   │   ├── hooks/useScreener.js
│   │   ├── components/         # 10 個 React 元件
│   │   └── constants/conditionLibrary.js
│   ├── package.json
│   └── vite.config.js
└── data/
    └── stocks.db               # SQLite 資料庫（runtime 自動建立）
```

---

## 後端設定 (`backend/.env`)

```env
DATA_RETENTION_YEARS=1          # 歷史 OHLCV 資料保留年數
AI_ENABLED=true                 # 開啟/關閉 AI 自然語言篩選（true/false）
FETCH_SCHEDULE_TIME=17:30       # 每日自動撈資料時間（HH:MM 24小時制）
```

> ⚠️ `.env` 不應 commit 至版控。
> AI 功能使用**本機 Claude Code CLI**，不需要另外設定 API Key。

---

## 資料庫 Schema

### `stocks` 表（快照，用於篩選器）
| 欄位 | 類型 | 說明 |
|------|------|------|
| symbol | TEXT PK | 股票代號（e.g. 2330.TW） |
| name | TEXT | 股票名稱 |
| sector / sector_en | TEXT | 產業（中/英） |
| market_type | TEXT | listed / otc |
| price, pe_ratio, forward_pe, dividend_yield | REAL | 基本面指標 |
| market_cap, volume | INTEGER | 市值、成交量 |
| week_52_high, week_52_low | REAL | 52週高低 |
| revenue_growth | REAL | 營收成長率 |
| updated_at | TIMESTAMP | 最後更新時間 |

### `daily_prices` 表（歷史 OHLCV）
| 欄位 | 類型 | 說明 |
|------|------|------|
| symbol | TEXT | 股票代號 |
| date | TEXT | 日期（YYYY-MM-DD），與 symbol 組成 PK |
| open, high, low, close, adj_close | REAL | 開高低收（調整後） |
| volume | INTEGER | 成交量 |

---

## 啟動方式

### 後端
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```
後端啟動時會自動：
1. 初始化 SQLite 資料庫（建立 `stocks` 與 `daily_prices` 表）
2. 在背景執行一次資料抓取（`fetch_daily.py` + `scripts/fetch_ohlcv.py`）
3. 啟動排程器，在 `.env` 設定的時間每天自動抓取

### 前端
```bash
cd frontend
npm install
npm run dev
```
前端開發伺服器跑在 `http://localhost:5173`。

---

## 資料抓取腳本

### 快照資料（用於篩選器即時查詢）
```bash
cd backend
python fetch_daily.py
```
- 抓取每支股票的 pe_ratio、殖利率、市值等快照指標
- 每次執行會 UPSERT `stocks` 表（覆蓋最新值）

### OHLCV 歷史資料（每日盤後）
```bash
cd backend

# 增量模式（預設）：只補缺少的天數
python scripts/fetch_ohlcv.py

# 完整 gap-check 模式：掃描整個保留窗口補缺
python scripts/fetch_ohlcv.py --full
```

**增量模式邏輯：**
1. 讀取 `.env` 中 `DATA_RETENTION_YEARS` 計算保留窗口起始日
2. 對每支股票查詢 DB 中最後一筆日期
3. 若沒有資料 → 從保留窗口起始日開始抓取
4. 若有資料但不是最新 → 從最後日期+1天開始抓取
5. 自動刪除超過保留期限的舊資料

**全量模式邏輯（`--full`）：**
- 對每支股票取得 DB 中整個保留窗口已存在的日期集合
- 透過 yfinance 下載完整窗口資料
- 只插入 DB 中缺少的日期（`INSERT OR IGNORE`）

---

## API 端點

| Method | Path | 說明 |
|--------|------|------|
| GET | `/api/health` | 健康檢查，回傳 DB 統計與 AI 狀態 |
| GET | `/api/sectors` | 取得所有產業類別 |
| GET | `/api/fields` | 取得所有可篩選欄位定義 |
| POST | `/api/screen` | 篩選股票（manual 或 natural_language 模式） |
| POST | `/api/fetch` | 手動觸發背景資料抓取 |

### `/api/screen` 請求格式
```json
// 手動模式
{
  "mode": "manual",
  "filters": {
    "conditions": [
      { "block_type": "AND", "rules": [{ "field": "pe_ratio", "operator": "lte", "value": 20 }] }
    ],
    "block_logic": "AND"
  },
  "sort_by": "dividend_yield",
  "sort_order": "desc",
  "page": 1,
  "page_size": 20
}

// 自然語言模式（需 AI_ENABLED=true）
{
  "mode": "natural_language",
  "query": "本益比低於20且殖利率高於3%的股票"
}
```

---

## 重要模組說明

### `ai_parser.py`
- `parse_natural_language(query)` — 透過本機 **Claude Code CLI**（`claude -p ...`）將自然語言轉為 `Filters` 物件
- 不需要 `ANTHROPIC_API_KEY`，使用已登入的 Claude Code 身份驗證
- AI 關閉時（`AI_ENABLED=false`），`/api/screen` 的 NL 模式會回傳錯誤訊息

### `screener.py`
- `build_query(filters, sort_by, sort_order, page, page_size)` — 將 `Filters` 物件轉為 SQLite 參數化查詢
- 支援 AND/OR block 邏輯
- 允許的 operator：`eq`, `gt`, `gte`, `lt`, `lte`

### `sector_mapping.py`
- `map_sector(sector_en)` — 將 yfinance 回傳的英文產業名稱對應為中文

---

## 技術棧

| 層 | 技術 |
|----|------|
| 後端框架 | FastAPI + Uvicorn |
| 資料庫 | SQLite 3 + aiosqlite（async） |
| 排程器 | APScheduler 3.x（AsyncIOScheduler） |
| 資料來源 | yfinance（Yahoo Finance） |
| AI | Claude Code CLI（本機，無需 API Key） |
| 前端框架 | React 18 + Vite |
| UI | Tailwind CSS 4 |
| 表格 | TanStack React Table |
| HTTP | Axios |

---

## 開發注意事項

1. **`.env` 不得 commit** — 包含 API Key，請加入 `.gitignore`
2. **第一次啟動較慢** — `fetch_ohlcv.py` 初次執行會抓取所有股票的完整歷史資料
3. **yfinance rate limit** — 腳本已內建速率限制（每10支停頓2秒，其他0.5秒）
4. **daily_prices 不影響篩選器** — 篩選器讀取 `stocks` 表（快照），`daily_prices` 為歷史 OHLCV 資料，供未來圖表功能使用
5. **台股代號格式** — 上市股票用 `.TW`，上櫃用 `.TWO`
6. **CORS** — 後端允許 `localhost:5173`（Vite）與 `localhost:3000`
