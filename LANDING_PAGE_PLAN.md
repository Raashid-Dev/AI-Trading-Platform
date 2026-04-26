# AI Trading Platform — Landing Page Plan

> Reference: https://edgebuild.com/ (AI-Powered Trading Strategy Platform)
> Goal: Build a marketing landing page that equals or surpasses EdgeBuild in design, clarity, and conversion.

---

## What EdgeBuild Does (and What We'll Beat)

EdgeBuild focuses on: **build → backtest → deploy** algo strategies.

Our edge over EdgeBuild:
- **Live NSE signals** — real-time BUY_CALL / BUY_PUT signals, not just backtesting
- **AI confidence scoring** — every signal has a confidence %, not just binary signals
- **WebSocket-first** — sub-second latency updates, not page refreshes
- **Free to use** — no subscription wall to see signals
- **India-first** — built specifically for NSE options traders

---

## Landing Page Architecture

### Tech Stack
- **React + Vite** (existing frontend setup)
- **Tailwind CSS** (already installed)
- **Framer Motion** for animations
- **Recharts** for live chart previews in hero

### Routing
- Add `/` route → LandingPage component
- `/app` or `/dashboard` → existing trading dashboard
- LandingPage should be a separate route, not nested in App.jsx's current layout

---

## Page Sections (Top → Bottom)

### 1. NAVBAR
```
Logo | [Features] [How It Works] [Live Demo] [GitHub]     [Launch App →]
```
- Sticky on scroll, glass-morphism background (backdrop-blur)
- Mobile: hamburger menu
- CTA button: `Launch App →` → links to `/app`

---

### 2. HERO SECTION
**Headline:** `AI-Powered Options Signals for NSE Traders`
**Sub:** `Real-time BUY_CALL & BUY_PUT signals for NIFTY, BANKNIFTY & top stocks — powered by AI, updated every 5 minutes.`

**Left side:**
- Headline + sub + two CTAs:
  - Primary: `View Live Signals →` (takes to dashboard)
  - Secondary: `See How It Works` (scrolls down)
- Trust badges: `● LIVE NSE Data`, `● WebSocket Real-time`, `● Free & Open Source`

**Right side (animated):**
- Mini live signal card mockup — shows a pulsing signal like:
  ```
  🟢 BUY_CALL  NIFTY
  Confidence: 82%
  Entry: ₹23,847
  Target: ₹24,100 | SL: ₹23,650
  ```
- Or an equity curve chart (Recharts LineChart) showing upward trend

**Design:**
- Dark background: `#0a0f1e` (deep navy)
- Gradient mesh or grid lines in background (like EdgeBuild's dark techy feel)
- Hero text: Large, bold, white — maybe gradient text on key word
- Accent color: Electric blue `#3b82f6` + Cyan `#06b6d4`

---

### 3. LIVE METRICS TICKER (Social Proof Strip)
Horizontal scrolling ticker strip:
```
📈 NIFTY: +0.8%  |  📊 Win Rate: 68%  |  ⚡ Signals Today: 12  |  💰 Avg P&L: +₹2,340  |  🔴 BANKNIFTY: -0.3%  |  ...
```
- Auto-scrolling marquee
- Pulls from `/summary` endpoint if user visits live, or static for landing
- Creates urgency and shows the platform is "alive"

---

### 4. FEATURES SECTION — "Why Traders Choose Us"
3-column grid (or 2x3), each card:

| Feature | Icon | Description |
|---------|------|-------------|
| Live NSE Signals | ⚡ | BUY_CALL / BUY_PUT signals updated every 5 min from real market data |
| AI Confidence Score | 🤖 | Each signal carries a % confidence based on trend + momentum + volatility |
| Multi-Symbol Coverage | 📊 | NIFTY, BANKNIFTY, RELIANCE, TCS, INFY, HDFCBANK, ICICIBANK |
| WebSocket Streaming | 🔌 | Sub-second latency updates via WebSocket, HTTP polling fallback |
| Performance Tracking | 📈 | Full P&L tracking, win rate, expectancy, equity curve |
| Free & Open Source | 🔓 | No subscription. MIT licensed. Fork and deploy your own. |

Card design: dark glass cards with subtle border, icon in colored circle, hover lift animation

---

### 5. HOW IT WORKS — "Signal in 3 Steps"
Horizontal step flow with connecting arrows:

```
[📡 Fetch Live Data]  →  [🧠 AI Scores Market]  →  [📣 Signal Generated]
  yfinance NSE API        Trend + Momentum +           BUY_CALL 82% conf.
  Every 5 minutes         Volatility scoring            Entry/Target/SL
```

- Animated connector lines between steps (CSS or Framer Motion)
- Below each step: short technical detail for credibility

---

### 6. LIVE DEMO PREVIEW — "See It In Action"
Embedded preview of the actual dashboard (iframe or screenshot animation):
- Either: animated screenshot carousel of the dashboard tabs (Overview, Signals, Trades, Stocks)
- Or: auto-refreshing live mini-widget showing latest signal from `/summary`
- CTA below: `Open Full Dashboard →`

This is the equivalent of EdgeBuild's "try it" section — shows the real product.

---

### 7. SIGNAL SHOWCASE — "Latest Signals"
Live feed of the 3 most recent signals pulled from `/signals`:
```
┌─────────────────────────────────┐
│ 🟢 BUY_CALL  NIFTY             │
│ Confidence: 82%                 │
│ Entry ₹23,847 → Target ₹24,100 │
│ Stop Loss: ₹23,650              │
│ 2 min ago                       │
└─────────────────────────────────┘
```
- 3 cards in a row, auto-refreshing every 30s
- "Refreshed 2 min ago" timestamp
- Encourages users to go to the full dashboard

---

### 8. TECH STACK SECTION — "Built with Modern Tech"
Logo grid (like EdgeBuild's tech logos):
- Python | FastAPI | yfinance | React | Vite | Tailwind | WebSocket | Recharts | Render | GitHub Pages
- Dark pill badges or logo icons
- Subtle: "No API keys required. No subscription. Just signals."

---

### 9. PERFORMANCE METRICS — "Real Results"
Stats bar (big bold numbers):
```
68%        12+         ₹2,340      <1s
Win Rate   Signals/Day  Avg P&L    Latency
```
- Animated count-up on scroll into view
- Sourced from actual backend `/metrics` if possible, otherwise static estimates

---

### 10. TESTIMONIAL / ABOUT SECTION
Since this is a personal/portfolio project:
- "Built by a solo developer obsessed with NSE options trading"
- GitHub stars count, commit count
- Or replace with a "Community" section if open-sourced

---

### 11. CTA SECTION (Bottom Banner)
Full-width dark blue gradient banner:
```
Ready to trade smarter?
Get live NSE options signals — free, real-time, AI-powered.

[Launch the Dashboard →]    [View on GitHub]
```

---

### 12. FOOTER
```
AI Trading Platform          © 2026 Raashid
[Features] [Dashboard] [GitHub] [How It Works]
Built with ❤️ for NSE traders
Disclaimer: For educational purposes only. Not financial advice.
```

---

## Design System

### Colors
```css
--bg-primary:    #0a0f1e;   /* Deep navy — main background */
--bg-secondary:  #0d1526;   /* Slightly lighter — cards */
--bg-card:       #111827;   /* Card backgrounds */
--border:        #1f2937;   /* Subtle borders */
--accent-blue:   #3b82f6;   /* Primary accent */
--accent-cyan:   #06b6d4;   /* Secondary accent */
--accent-green:  #10b981;   /* Positive / buy call */
--accent-red:    #ef4444;   /* Negative / buy put */
--text-primary:  #f9fafb;   /* Main text */
--text-muted:    #6b7280;   /* Muted text */
```

### Typography
- Headings: `Inter` or `Plus Jakarta Sans` — bold, large
- Mono/data: `JetBrains Mono` or `Fira Code` — for prices, signals
- Body: `Inter` — 16px, 1.6 line-height

### Animations
- Framer Motion: `fadeInUp` on section enter (triggered by IntersectionObserver)
- Hero signal card: subtle float animation
- Metrics counter: count-up on scroll
- Ticker: CSS marquee (`overflow: hidden` + `@keyframes scroll`)
- Feature cards: hover lift (`translateY(-4px) + box-shadow`)

---

## Implementation Plan

### Phase 1 — Static Landing Page (1–2 days)
1. Create `frontend/src/pages/LandingPage.jsx`
2. Add `/` route in `App.jsx` (or `main.jsx`)
3. Move existing dashboard to `/app`
4. Build all sections with static/mock data
5. Add Framer Motion animations
6. Mobile responsive (Tailwind breakpoints)

### Phase 2 — Live Data Integration (1 day)
7. Hero: pull latest signal from `/summary` endpoint
8. Metrics ticker: pull from `/summary`
9. Signal showcase: pull from `/signals`
10. Performance stats: pull from `/metrics`

### Phase 3 — Polish & Deploy (1 day)
11. SEO: meta tags, OG image, title
12. Performance: lazy-load dashboard iframe/screenshot
13. Analytics: add basic page-view tracking (Plausible or GA4)
14. Update GitHub Pages deploy workflow to serve `/` as landing

---

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `frontend/src/pages/LandingPage.jsx` | CREATE | Main landing page component |
| `frontend/src/pages/LandingPage.css` | CREATE (optional) | Custom animations not in Tailwind |
| `frontend/src/App.jsx` | MODIFY | Add `/` → LandingPage, `/app` → Dashboard |
| `frontend/src/components/landing/Hero.jsx` | CREATE | Hero section |
| `frontend/src/components/landing/Features.jsx` | CREATE | Features grid |
| `frontend/src/components/landing/HowItWorks.jsx` | CREATE | 3-step flow |
| `frontend/src/components/landing/SignalPreview.jsx` | CREATE | Live signal cards |
| `frontend/src/components/landing/MetricsTicker.jsx` | CREATE | Scrolling ticker |
| `frontend/src/components/landing/Navbar.jsx` | CREATE | Landing navbar (different from app header) |
| `frontend/src/components/landing/Footer.jsx` | CREATE | Footer |
| `frontend/package.json` | MODIFY | Add `framer-motion` dependency |

---

## Competitive Advantages Over EdgeBuild

| EdgeBuild | Our Platform |
|-----------|-------------|
| Algo strategy builder | Live ready-made signals — no setup needed |
| Backtest focus | Real-time live trading signals |
| Subscription model | 100% free |
| US markets | NSE India — NIFTY/BANKNIFTY options |
| Generic | AI confidence scoring per signal |
| Desktop-heavy | WebSocket mobile-friendly dashboard |

---

## Disclaimer Copy
> **Educational purposes only.** This platform is a demonstration of real-time data engineering and AI signal generation. Signals generated are not financial advice. Always consult a SEBI-registered advisor before trading options.
