# Project Memory — AI Trading Platform

> This file stores persistent notes, references, and decisions across sessions.

---

## Inspiration & References

### EdgeBuild
- **URL:** https://edgebuild.com/
- **Type:** AI-Powered Trading Strategy Platform
- **What it does:** Build, backtest, and deploy algorithmic trading strategies using AI tools
- **Why we're referencing it:** Raashid wants to build a marketing/landing page for the AI Trading Platform that is similar to or better than EdgeBuild's website
- **Note added:** 2026-04-26

---

## Live URLs

- **Backend (Render):** https://ai-trading-platform-33ow.onrender.com
- **Health check:** https://ai-trading-platform-33ow.onrender.com/health
- **GitHub repo:** https://github.com/Raashid-Dev/AI-Trading-Platform
- **Frontend (GitHub Pages):** https://raashid-dev.github.io/AI-Trading-Platform/

---

## Key Decisions & Notes

- Backend on Render (free tier — spins down after inactivity)
- Frontend deployed via GitHub Pages (Vite build → `frontend/dist`)
- CORS: `allow_credentials=False` with `allow_origins=["*"]` — important constraint
- Data: NSE stocks via yfinance (.NS suffix), NSE indices via unofficial NSE India API
- Symbols: NIFTY, BANKNIFTY, RELIANCE, HDFCBANK, ICICIBANK, INFY, TCS
- Signal types: BUY_CALL, BUY_PUT, HOLD
- Transport: WebSocket primary, HTTP polling fallback

---

## Planned: Marketing Landing Page

Goal: Build a world-class marketing/landing page inspired by EdgeBuild but tailored for the AI Trading Platform.

See: `LANDING_PAGE_PLAN.md` for full spec.
