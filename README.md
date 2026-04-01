# tw-screener 台股 AI 篩選器

使用 FastAPI + SQLite 後端、React + Vite 前端，整合 Yahoo Finance 資料與 Anthropic Claude AI 的台股篩選工具。

---

## 安裝與啟動

### 後端

```bash
cd backend
pip install -r requirements.txt
```

複製並建立環境設定檔（`.env` 不得 commit）：

```env
DATA_RETENTION_YEARS=1
AI_ENABLED=true
FETCH_SCHEDULE_TIME=17:30
```

啟動開發伺服器：

```bash
uvicorn main:app --reload
```

後端啟動時會自動初始化資料庫、執行一次資料抓取，並啟動每日排程。

---

### 前端

```bash
cd frontend
npm install
npm run dev
```

前端開發伺服器跑在 `http://localhost:5173`。

---

## 資料腳本

### 快照資料（篩選器即時查詢用）

```bash
cd backend
python fetch_daily.py
```

抓取每支股票的 PE、殖利率、市值等快照指標，UPSERT 至 `stocks` 表。

---

### OHLCV 歷史資料（每日盤後）

```bash
cd backend

# 增量模式（預設）：只補缺少的天數
python scripts/fetch_ohlcv.py

# 全量 gap-check 模式：掃描整個保留窗口補缺
python scripts/fetch_ohlcv.py --full
```

- **增量模式**：查詢各股票在 DB 中的最後一筆日期，從該日期+1天開始抓取；無資料則從保留窗口起始日開始。
- **全量模式**：下載完整保留窗口資料，只插入 DB 中缺少的日期（`INSERT OR IGNORE`）。
- 超過 `DATA_RETENTION_YEARS` 保留期限的舊資料會自動刪除。

---

### 建立股票清單

```bash
cd backend
python scripts/build_stock_list.py
```

重新產生 `tw_stocks.json`（台股代號與名稱對照表）。

---

## 技術棧

| 層 | 技術 |
|----|------|
| 後端框架 | FastAPI + Uvicorn |
| 資料庫 | SQLite 3 + aiosqlite |
| 排程器 | APScheduler 3.x |
| 資料來源 | yfinance（Yahoo Finance） |
| AI | Claude Code CLI（本機，無需 API Key） |
| 前端框架 | React 18 + Vite |
| UI | Tailwind CSS 4 |
| 表格 | TanStack React Table |
| HTTP | Axios |
