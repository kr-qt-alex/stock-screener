# tw-screener 台股 AI 篩選器

使用 FastAPI + SQLite 後端、React + Vite 前端，整合 Yahoo Finance 資料與 Anthropic Claude AI 的台股篩選工具。

---

## 第一次安裝

> 只需要執行一次。之後每次開發請直接看「日常開發啟動」章節。

### 步驟 1 — 建立後端 Python 環境

> 需要 **Python 3.10 以上**。可執行 `python --version` 確認版本。

```bash
cd backend

# 建立虛擬環境（只需一次）
python -m venv venv

# 啟動虛擬環境
source venv/Scripts/activate        # Git Bash / bash
# venv\Scripts\Activate.ps1         # PowerShell
# venv\Scripts\activate.bat         # cmd

# 安裝依賴套件（用 python -m pip 確保裝進 venv）
python -m pip install -r requirements.txt
```

啟動成功後，terminal 的提示字元前面會出現 `(venv)` 字樣。

### 步驟 2 — 建立後端設定檔

```bash
# 在 backend/ 目錄下執行（複製 sample 為正式設定檔）
cp .env.sample .env
```

預設值即可正常使用。若需修改，以文字編輯器開啟 `backend/.env`，各設定說明已寫在檔案的註解中。

### 步驟 3 — 安裝前端套件

```bash
cd ../frontend
npm install
```

安裝完成後，第一次安裝結束。

---

## 日常開發啟動

每次開發需要同時啟動後端與前端，建議**開兩個 terminal**。

### Terminal 1 — 後端

```bash
cd backend

# 每次開新 terminal 都需要先啟動虛擬環境
source venv/Scripts/activate        # Git Bash / bash
venv\Scripts\Activate.ps1           # PowerShell
venv\Scripts\activate.bat           # cmd

# 啟動後端
python -m uvicorn main:app --reload
```

看到 `Application startup complete.` 表示啟動成功。

後端啟動時會自動：
- 初始化 SQLite 資料庫（`data/stocks.db`）
- 在背景執行一次資料抓取
- 啟動每日排程（依 `.env` 中 `FETCH_SCHEDULE_TIME` 設定）

| 位址 | 說明 |
|------|------|
| `http://localhost:8000` | API 根路徑 |
| `http://localhost:8000/docs` | Swagger 互動文件 |

### Terminal 2 — 前端

```bash
cd frontend
npm run dev
```

看到 `Local: http://localhost:5173/` 表示啟動成功，開啟瀏覽器前往該網址即可使用。

---

## 使用說明

### 篩選器

1. 開啟 `http://localhost:5173`
2. 在篩選條件區新增條件（PE、殖利率、市值等）
3. 點擊「篩選」取得結果

### AI 自然語言篩選

需先完成以下設定：

1. 安裝並登入 Claude Code CLI：

   ```bash
   npm install -g @anthropic-ai/claude-code
   claude login
   ```

2. 將 `backend/.env` 中的 `AI_ENABLED` 改為 `true`：

   ```env
   AI_ENABLED=true
   ```

3. 重新啟動後端後，即可在搜尋框輸入中文篩選條件，例如：

   > 本益比低於 20 且殖利率高於 3% 的電子股

AI 功能使用本機 Claude Code CLI，**無需另外設定 API Key**。

---

## 手動操作資料

後端啟動後會自動抓取資料，通常不需要手動執行。若需要手動觸發：

### 透過 API（後端需已啟動）

```bash
curl -X POST http://localhost:8000/api/fetch
```

### 直接執行腳本（後端不需啟動）

```bash
cd backend
source venv/Scripts/activate

# 抓取快照資料（PE、殖利率、市值等，寫入 stocks 表）
python fetch_daily.py

# 抓取 OHLCV 歷史資料（增量模式，只補缺少的天數）
python scripts/fetch_ohlcv.py

# 抓取 OHLCV 歷史資料（全量模式，掃描整個保留窗口補缺）
python scripts/fetch_ohlcv.py --full
```

### 重新產生股票清單

```bash
cd backend
source venv/Scripts/activate
python scripts/build_stock_list.py
```

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
