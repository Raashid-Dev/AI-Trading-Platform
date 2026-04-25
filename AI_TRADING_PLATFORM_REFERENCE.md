# AI Trading Platform — Complete Reference Document

> **Purpose:** Full technical reference for the AI Trading Platform project. Use this to onboard a new AI assistant, make edits, or resume development.

---

## 1. Project Overview

An NSE/India options signal engine with a live React dashboard. The backend runs a trading loop that scores market conditions, generates BUY_CALL / BUY_PUT signals, tracks trades and performance, then writes state to a JSON file. A FastAPI server reads that file and streams it to connected clients via WebSocket (with HTTP polling as fallback). The React frontend consumes this stream and renders live metrics.

**Live URLs:**
- Backend (Render): `https://ai-trading-platform-33ow.onrender.com`
- Health check: `https://ai-trading-platform-33ow.onrender.com/health`
- Frontend: runs locally at `http://localhost:3000` (not yet deployed to Vercel)
- GitHub repo: `https://github.com/Raashid-Dev/AI-Trading-Platform`

---

## 2. Repository Structure

```
AI Trading Platform/
├── main.py                          # Trading loop entry point
├── server.py                        # FastAPI server (HTTP + WebSocket)
├── config.py                        # Shared constants and config
├── start.sh                         # Render startup script (runs both processes)
├── render.yaml                      # Render deployment config
├── requirements.txt                 # Pinned Python dependencies
├── runtime.txt                      # Python version pin for Render (3.11.0)
├── live_state.json                  # Runtime state file (gitignored, written by main.py)
├── engine/
│   ├── data_fetcher.py              # Fetches OHLCV candle data via yfinance
│   ├── market_scorer.py             # Scores market conditions (trend, momentum, volatility)
│   ├── options_signal.py            # Generates BUY_CALL / BUY_PUT signals
│   └── performance_tracker.py      # Tracks open/closed trades, P&L, win rate
└── frontend/
    ├── .env                         # Vite env vars (API + WS URLs)
    ├── vite.config.js               # Vite build config + dev proxy
    ├── vercel.json                  # Vercel SPA rewrite config
    ├── package.json
    ├── tailwind.config.js
    └── src/
        ├── main.jsx                 # React entry point
        ├── App.jsx                  # Root component, uses useTradeStream hook
        ├── api.js                   # Axios HTTP helpers (BASE_URL from env)
        ├── useTradeStream.js        # WS + polling hook with retry/backoff
        └── components/
            ├── Header.jsx           # Transport badge (WS·LIVE / POLLING / CONNECTING)
            ├── CapitalCard.jsx      # Current capital display
            ├── SignalTable.jsx      # Live signals table
            ├── OpenTrades.jsx       # Open positions table
            ├── ClosedTrades.jsx     # Closed trades history
            ├── PerformancePanel.jsx # Win rate, P&L, expectancy
            └── EquityChart.jsx      # Equity curve chart (Recharts)
```

---

## 3. Data Flow

```
market data (yfinance)
        ↓
   data_fetcher.py  →  raw OHLCV candles
        ↓
   market_scorer.py  →  scores: trend / momentum / volatility
        ↓
  options_signal.py  →  signal: BUY_CALL | BUY_PUT | HOLD + confidence
        ↓
performance_tracker.py  →  trade lifecycle, P&L, metrics
        ↓
   main.py writes  →  live_state.json  (atomic: .tmp → os.replace)
        ↓
  server.py _file_watcher polls every 1s
        ↓
  WebSocket broadcast to all connected clients
        ↓
  React useTradeStream hook  →  UI re-render
```

---

## 4. Key Files — Full Details

### 4.1 `main.py` (Trading Loop)

- Entry point. Runs in a loop, one iteration per candle.
- Reads `LIVE_STATE_FILE` env var (default: `live_state.json`).
- **Atomic write pattern:**
  ```python
  _tmp = LIVE_STATE_FILE + ".tmp"
  with open(_tmp, "w") as f:
      json.dump(state, f, default=str)
  os.replace(_tmp, LIVE_STATE_FILE)
  ```
- Per-candle try/except to prevent loop crash on single bad tick.
- Structured logging with `log_main = logging.getLogger("trading-loop")`.
- Modes: `--mock` (simulated data) or `--live` (real yfinance data).

### 4.2 `server.py` (FastAPI)

- **CORS:** `allow_credentials=False` with `allow_origins=["*"]`. **Critical:** `allow_credentials=True` with wildcard origin is rejected by browsers.
- **WebSocket endpoint:** `/ws` — on connect sends current state snapshot immediately; updates pushed by file watcher.
- **Background tasks (started on app startup):**
  - `_file_watcher()`: polls `live_state.json` every 1s; broadcasts on mtime/size change.
  - `_heartbeat_task()`: pings all WS clients every 15s to detect dead connections.
- **Rate limiting:** In-memory sliding window, 10 req/sec per IP. Applied to `/state`, `/signals`, `/summary` via `Depends(rate_limit)`.
- **Safe state read:** `_load_state_safe()` never raises — returns last known-good state from `_last_valid_state` cache if file is missing or corrupt.
- **HTTP endpoints:**
  - `GET /health` — status, connections count, last_update UTC, mode (websocket/polling), allowed_origins
  - `GET /state` — full live state (rate-limited)
  - `GET /signals` — signals array (rate-limited)
  - `GET /summary` — capital + signal summary + performance (rate-limited)
  - `GET /trades` — open and closed trades
  - `GET /metrics` — performance metrics
  - `GET /capital` — capital object

### 4.3 `engine/performance_tracker.py`

- Tracks open trades (entry, stop-loss, target) and closed trades (outcome, P&L).
- Memory safety: caps closed trades at 500 in `export_state()`:
  ```python
  MAX_CLOSED_TRADES = 500
  if len(closed) > self.MAX_CLOSED_TRADES:
      closed = closed[-self.MAX_CLOSED_TRADES:]
  ```

### 4.4 `frontend/src/useTradeStream.js`

- Tries WebSocket first, falls back to HTTP polling if WS fails after all retries.
- **Backoff:** `[1000, 2000, 5000, 10000]` ms — fixed array, not exponential.
- **WS retry from polling:** Every 30s, resets retry count and attempts WS reconnect.
- `connectRef` forward-ref pattern prevents stale closure in `setInterval`.
- Returns: `{ state, connected, transport, lastUpdate, error }` where `transport` is `"websocket" | "polling" | "connecting"`.

### 4.5 `frontend/src/components/Header.jsx`

Transport-aware badge:
```js
const TRANSPORT_LABELS = {
  websocket:  { label: 'WS · LIVE',   dot: 'bg-green-400 animate-pulse' },
  polling:    { label: 'POLLING',      dot: 'bg-yellow-400 animate-pulse' },
  connecting: { label: 'CONNECTING…', dot: 'bg-blue-400 animate-pulse' },
};
```

---

## 5. Environment Variables

### Backend (Render)
| Variable | Value | Notes |
|---|---|---|
| `TRADING_MODE` | `mock` | or `live` for real market data |
| `ALLOWED_ORIGINS` | `*` | Comma-separated URLs for production |
| `LIVE_STATE_FILE` | `live_state.json` | Path to state file |
| `PYTHON_VERSION` | `3.11.0` | Forces Python 3.11 on Render |

### Frontend (`frontend/.env`)
```
VITE_API_URL=https://ai-trading-platform-33ow.onrender.com
VITE_WS_URL=wss://ai-trading-platform-33ow.onrender.com/ws
VITE_POLL_MS=10000
```

---

## 6. Deployment

### Backend — Render (free tier)

**Why single service:** Render free tier doesn't share disk between separate web+worker services. Both `main.py` and `server.py` run in the same container via `start.sh` so they share the filesystem for `live_state.json`.

**`start.sh`:**
```bash
#!/usr/bin/env bash
set -e
python main.py --${TRADING_MODE:-mock} &
exec uvicorn server:app --host 0.0.0.0 --port "$PORT"
```

**`render.yaml`:**
```yaml
services:
  - type: web
    name: ai-trading-backend
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: bash start.sh
    envVars:
      - key: TRADING_MODE
        value: mock
      - key: ALLOWED_ORIGINS
        value: "*"
```

**`runtime.txt`:** `3.11.0` (no `python-` prefix — Render format)

**Note:** Free tier sleeps after 15 min of inactivity. On wake-up, `live_state.json` is absent until the trading loop writes the first candle (~30s).

### Frontend — Local Dev

```bash
cd "AI Trading Platform/frontend"
npm install
npm run dev
# → http://localhost:3000
```

Dev proxy in `vite.config.js` forwards `/api` and `/ws` to `localhost:8000` during local development.

### Frontend — Vercel (not yet deployed)

`frontend/vercel.json` is configured with SPA rewrite. To deploy:
```bash
cd frontend
npm run build
npx vercel --prod
```
Set `VITE_API_URL` and `VITE_WS_URL` as Vercel environment variables pointing to the Render backend.

---

## 7. Python Dependencies (`requirements.txt`)

```
numpy==1.26.4
pandas==2.1.4
yfinance==0.2.40
pytz==2024.1
fastapi==0.110.0
uvicorn[standard]==0.29.0
websockets==12.0
```

All pinned to exact versions with pre-built wheels for Python 3.11. **Do not upgrade** without testing — newer Python (3.12+) or numpy (2.x) may break pandas compatibility on Render's build environment.

---

## 8. Live State Schema (`live_state.json`)

```json
{
  "timestamp": "2026-04-25T20:00:00Z",
  "capital": {
    "current": 100000.0,
    "initial": 100000.0,
    "pnl": 500.0
  },
  "signals": [
    {
      "symbol": "NIFTY",
      "signal": "BUY_CALL",
      "confidence": 0.78,
      "timestamp": "..."
    }
  ],
  "open_trades": [
    {
      "id": "...",
      "symbol": "NIFTY",
      "direction": "CALL",
      "entry_price": 150.0,
      "stop_loss": 120.0,
      "target": 200.0,
      "status": "OPEN"
    }
  ],
  "closed_trades": [ ... ],
  "performance": {
    "win_rate": 0.62,
    "expectancy": 1.4,
    "total_pnl": 5000.0,
    "closed_trades": 25
  }
}
```

---

## 9. Known Issues & Gotchas

| Issue | Cause | Fix |
|---|---|---|
| CORS "Network Error" | `allow_credentials=True` + `allow_origins=["*"]` | Use `allow_credentials=False` |
| Render uses Python 3.14 | Default runtime | Set `runtime.txt` = `3.11.0` + `PYTHON_VERSION=3.11.0` env var |
| `live_state.json` missing on startup | Render free tier cold start | Normal — wait ~30s for first candle |
| `git index.lock` error | Stale lock from crashed process | `rm -f .git/index.lock` |
| GitHub push rejected (password) | GitHub removed password auth | Use PAT: `https://username:TOKEN@github.com/repo` |
| WS code 1006 (abnormal closure) | Network drop or Render sleep | `useTradeStream` auto-retries with backoff |
| `zsh: number expected` in terminal | Em-dash `—` pasted as flag | Type commands manually, don't paste |

---

## 10. Git Workflow

```bash
cd "/Users/raashidshaikh/Desktop/AI Trading Platform"

# Check status
git status
git log --oneline -5

# Stage and commit
git add <files>
git commit -m "description"
git push

# If push fails (auth)
git remote set-url origin https://Raashid-Dev:YOUR_PAT@github.com/Raashid-Dev/AI-Trading-Platform.git
git push
```

After pushing, trigger redeploy: **Render dashboard → service → Manual Deploy → Deploy latest commit**.

---

## 11. Running Locally (Backend)

```bash
cd "/Users/raashidshaikh/Desktop/AI Trading Platform"
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Terminal 1 — trading loop
python main.py --mock

# Terminal 2 — API server
uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

---

## 12. Pending Tasks / Next Steps

1. **Verify CORS fix is deployed** — commit `allow_credentials=False` in `server.py` was not pushed in the last session. Run:
   ```bash
   cd "/Users/raashidshaikh/Desktop/AI Trading Platform"
   rm -f .git/index.lock
   git add server.py
   git commit -m "fix: allow_credentials=False to resolve CORS with wildcard origin"
   git push
   ```
   Then Manual Deploy on Render.

2. **Deploy frontend to Vercel** — run `npm run build` then `npx vercel --prod` from `frontend/` directory. Add env vars in Vercel dashboard.

3. **Switch to live trading data** — change `TRADING_MODE` env var in Render from `mock` to `live`.

4. **Tighten CORS for production** — once frontend is on a fixed domain, set `ALLOWED_ORIGINS` to that specific URL instead of `*`.
