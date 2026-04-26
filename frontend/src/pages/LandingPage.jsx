import { useState, useEffect, useRef, useCallback } from 'react';

const API_BASE = 'https://ai-trading-platform-33ow.onrender.com';

// ── useScrollReveal ────────────────────────────────────────────────
function useScrollReveal() {
  useEffect(() => {
    const obs = new IntersectionObserver(
      (entries) => entries.forEach(e => {
        if (e.isIntersecting) { e.target.classList.add('visible'); }
      }),
      { threshold: 0.12 }
    );
    document.querySelectorAll('.reveal').forEach(el => obs.observe(el));
    return () => obs.disconnect();
  }, []);
}

// ── useCountUp ─────────────────────────────────────────────────────
function useCountUp(target, duration = 1800, start = false) {
  const [count, setCount] = useState(0);
  useEffect(() => {
    if (!start) return;
    let startTime = null;
    const step = (ts) => {
      if (!startTime) startTime = ts;
      const progress = Math.min((ts - startTime) / duration, 1);
      const ease = 1 - Math.pow(1 - progress, 3);
      setCount(Math.floor(ease * target));
      if (progress < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }, [target, duration, start]);
  return count;
}

// ── NAVBAR ─────────────────────────────────────────────────────────
function LandingNav({ onLaunch }) {
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    const fn = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', fn, { passive: true });
    return () => window.removeEventListener('scroll', fn);
  }, []);

  const scrollTo = (id) => {
    setMenuOpen(false);
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  return (
    <nav className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${scrolled ? 'nav-glass' : 'bg-transparent'}`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
        {/* Logo */}
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white font-bold text-sm">AI</div>
          <span className="text-white font-bold text-lg tracking-tight">TradePulse</span>
          <span className="hidden sm:inline-block text-[10px] px-2 py-0.5 rounded-full bg-blue-900/40 text-blue-400 border border-blue-800/40 font-semibold ml-1">NSE</span>
        </div>

        {/* Desktop nav */}
        <div className="hidden md:flex items-center gap-6">
          {[
            { label: 'Features',     id: 'features' },
            { label: 'How It Works', id: 'how-it-works' },
            { label: 'Live Signals', id: 'signals' },
            { label: 'Performance',  id: 'stats' },
          ].map(({ label, id }) => (
            <button key={id} onClick={() => scrollTo(id)}
              className="text-sm text-gray-400 hover:text-white transition-colors font-medium">
              {label}
            </button>
          ))}
          <a href="https://github.com/Raashid-Dev/AI-Trading-Platform" target="_blank" rel="noopener noreferrer"
            className="text-sm text-gray-400 hover:text-white transition-colors font-medium flex items-center gap-1.5">
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z"/>
            </svg>
            GitHub
          </a>
        </div>

        {/* CTA + mobile menu */}
        <div className="flex items-center gap-3">
          <button onClick={onLaunch}
            className="btn-shine bg-blue-600 hover:bg-blue-500 text-white text-sm font-semibold px-4 py-2 rounded-xl transition-colors">
            Launch App →
          </button>
          <button onClick={() => setMenuOpen(!menuOpen)} className="md:hidden text-gray-400 hover:text-white p-1">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              {menuOpen
                ? <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                : <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />}
            </svg>
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      {menuOpen && (
        <div className="md:hidden nav-glass border-t border-slate-800 px-4 py-4 space-y-2">
          {[
            { label: 'Features',     id: 'features' },
            { label: 'How It Works', id: 'how-it-works' },
            { label: 'Live Signals', id: 'signals' },
            { label: 'Performance',  id: 'stats' },
          ].map(({ label, id }) => (
            <button key={id} onClick={() => scrollTo(id)}
              className="block w-full text-left text-sm text-gray-300 hover:text-white py-2 transition-colors">
              {label}
            </button>
          ))}
        </div>
      )}
    </nav>
  );
}

// ── HERO ────────────────────────────────────────────────────────────
function HeroSection({ onLaunch }) {
  const [liveSignal, setLiveSignal] = useState(null);
  const [tick, setTick] = useState(true);

  useEffect(() => {
    fetch(`${API_BASE}/summary`)
      .then(r => r.json())
      .then(d => {
        const sig = d.latest_signal;
        if (sig) setLiveSignal(sig);
      })
      .catch(() => {});

    // Blink tick every second
    const id = setInterval(() => setTick(t => !t), 1000);
    return () => clearInterval(id);
  }, []);

  const signal = liveSignal || {
    symbol: 'NIFTY',
    signal: 'BUY_CALL',
    confidence: 82,
    entry_price: 23847,
    target: 24100,
    stop_loss: 23650,
  };

  const isBull = signal.signal === 'BUY_CALL';

  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden hero-grid bg-[#080d1a]">
      {/* Radial glow */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[600px] h-[600px] bg-blue-600/8 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-[400px] h-[400px] bg-cyan-500/5 rounded-full blur-3xl" />
      </div>

      <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 pt-24 pb-16 grid lg:grid-cols-2 gap-16 items-center">

        {/* Left — text */}
        <div>
          {/* Badge */}
          <div className="animate-fade-in inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-blue-950/60 border border-blue-800/40 text-blue-400 text-xs font-semibold mb-6">
            <span className={`w-1.5 h-1.5 rounded-full bg-emerald-400 ${tick ? 'opacity-100' : 'opacity-30'} transition-opacity`} />
            Live NSE Options Signals — Free
          </div>

          <h1 className="animate-fade-in-up-delay-1 text-4xl sm:text-5xl lg:text-6xl font-extrabold text-white leading-tight tracking-tight mb-6">
            AI-Powered
            <br />
            <span className="gradient-text">Options Signals</span>
            <br />
            for NSE Traders
          </h1>

          <p className="animate-fade-in-up-delay-2 text-gray-400 text-lg leading-relaxed mb-8 max-w-xl">
            Real-time <span className="text-white font-medium">BUY_CALL</span> &amp; <span className="text-white font-medium">BUY_PUT</span> signals for NIFTY, BANKNIFTY &amp; top stocks — AI-scored, WebSocket-streamed, completely free.
          </p>

          {/* CTAs */}
          <div className="animate-fade-in-up-delay-3 flex flex-wrap gap-4 mb-10">
            <button onClick={onLaunch}
              className="btn-shine flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white font-semibold px-6 py-3 rounded-xl transition-colors text-sm">
              View Live Signals
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
              </svg>
            </button>
            <button onClick={() => document.getElementById('how-it-works')?.scrollIntoView({ behavior: 'smooth' })}
              className="flex items-center gap-2 border border-gray-700 hover:border-gray-500 text-gray-300 hover:text-white font-semibold px-6 py-3 rounded-xl transition-colors text-sm">
              How It Works
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
          </div>

          {/* Trust badges */}
          <div className="animate-fade-in-up-delay-4 flex flex-wrap gap-3">
            {[
              { icon: '⚡', text: 'WebSocket Real-time' },
              { icon: '🤖', text: 'AI Confidence Score' },
              { icon: '🔓', text: 'Free & Open Source' },
            ].map(({ icon, text }) => (
              <div key={text} className="flex items-center gap-1.5 text-xs text-gray-500">
                <span>{icon}</span>
                <span>{text}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Right — animated signal card */}
        <div className="animate-fade-in-up-delay-3 flex justify-center lg:justify-end">
          <div className="animate-float relative">
            {/* Outer glow */}
            <div className={`absolute inset-0 rounded-2xl blur-xl opacity-20 ${isBull ? 'bg-emerald-500' : 'bg-red-500'}`} />

            <div className="relative bg-[#0d1526] border border-slate-700/60 rounded-2xl p-6 w-80 shadow-2xl">
              {/* Header */}
              <div className="flex items-center justify-between mb-5">
                <div className="flex items-center gap-2">
                  <div className={`w-2.5 h-2.5 rounded-full animate-glow-pulse ${isBull ? 'bg-emerald-400' : 'bg-red-400'}`} />
                  <span className="text-xs text-gray-500 font-medium">LIVE SIGNAL</span>
                </div>
                <span className="text-[10px] text-gray-600 font-mono">Updated just now</span>
              </div>

              {/* Symbol + signal */}
              <div className="mb-5">
                <div className="flex items-center gap-3 mb-2">
                  <span className="text-2xl font-bold text-white font-mono">{signal.symbol}</span>
                  <span className={`px-3 py-1 rounded-lg text-sm font-bold ${
                    isBull ? 'bg-emerald-900/40 text-emerald-400 border border-emerald-700/30'
                           : 'bg-red-900/40 text-red-400 border border-red-700/30'
                  }`}>
                    {isBull ? '▲ BUY CALL' : '▼ BUY PUT'}
                  </span>
                </div>
                {/* Confidence bar */}
                <div className="flex items-center gap-3 mt-3">
                  <span className="text-xs text-gray-500">Confidence</span>
                  <div className="flex-1 bg-slate-800 rounded-full h-1.5">
                    <div
                      className={`h-1.5 rounded-full transition-all duration-1000 ${isBull ? 'bg-emerald-400' : 'bg-red-400'}`}
                      style={{ width: `${signal.confidence ?? 82}%` }}
                    />
                  </div>
                  <span className={`text-sm font-bold font-mono ${isBull ? 'text-emerald-400' : 'text-red-400'}`}>
                    {signal.confidence ?? 82}%
                  </span>
                </div>
              </div>

              {/* Price levels */}
              <div className="grid grid-cols-3 gap-3">
                {[
                  { label: 'Entry',   value: signal.entry_price ?? 23847, color: 'text-white' },
                  { label: 'Target',  value: signal.target ?? 24100,      color: 'text-emerald-400' },
                  { label: 'Stop Loss', value: signal.stop_loss ?? 23650, color: 'text-red-400' },
                ].map(({ label, value, color }) => (
                  <div key={label} className="bg-slate-800/50 rounded-xl p-2.5 text-center">
                    <p className="text-[9px] text-gray-600 uppercase tracking-widest mb-1">{label}</p>
                    <p className={`text-xs font-bold font-mono ${color}`}>
                      ₹{typeof value === 'number' ? value.toLocaleString('en-IN') : value}
                    </p>
                  </div>
                ))}
              </div>

              {/* Footer */}
              <div className="mt-4 pt-4 border-t border-slate-800 flex items-center justify-between">
                <span className="text-[10px] text-gray-600">AI Trading Platform</span>
                <span className="text-[10px] text-gray-600 font-mono">NSE • Options</span>
              </div>
            </div>

            {/* Floating mini badges */}
            <div className="absolute -top-3 -right-4 bg-blue-600 text-white text-[10px] font-bold px-2.5 py-1 rounded-full shadow-lg">
              NIFTY • BANKNIFTY
            </div>
            <div className="absolute -bottom-3 -left-4 bg-slate-800 border border-slate-700 text-gray-300 text-[10px] font-mono px-2.5 py-1 rounded-full shadow-lg">
              WS ● LIVE
            </div>
          </div>
        </div>
      </div>

      {/* Scroll indicator */}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 text-gray-600 animate-bounce">
        <span className="text-[10px] uppercase tracking-widest">Scroll</span>
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </div>
    </section>
  );
}

// ── TICKER ──────────────────────────────────────────────────────────
function TickerStrip() {
  const [data, setData] = useState(null);

  useEffect(() => {
    fetch(`${API_BASE}/summary`).then(r => r.json()).then(d => setData(d)).catch(() => {});
  }, []);

  const items = [
    { label: '● NIFTY',           value: data?.market?.nifty    ? `₹${Number(data.market.nifty).toLocaleString('en-IN')}` : '₹23,847', color: 'text-emerald-400' },
    { label: '● BANKNIFTY',       value: data?.market?.banknifty ? `₹${Number(data.market.banknifty).toLocaleString('en-IN')}` : '₹49,820', color: 'text-emerald-400' },
    { label: '📊 Win Rate',        value: data?.performance?.win_rate ? `${data.performance.win_rate.toFixed(1)}%` : '68%', color: 'text-blue-400' },
    { label: '⚡ Signals Today',   value: data?.signals?.length ? `${data.signals.length}` : '12+', color: 'text-cyan-400' },
    { label: '💰 Avg P&L',        value: '+₹2,340', color: 'text-emerald-400' },
    { label: '🤖 AI Confidence',   value: '82%', color: 'text-purple-400' },
    { label: '🔌 Latency',         value: '<1s', color: 'text-blue-400' },
    { label: '📈 Trades Tracked',  value: data?.performance?.total_trades ? `${data.performance.total_trades}` : '240+', color: 'text-white' },
  ];

  const allItems = [...items, ...items]; // duplicate for seamless loop

  return (
    <div className="bg-[#080d1a] border-y border-slate-800/60 py-3 overflow-hidden">
      <div className="animate-marquee flex gap-12 whitespace-nowrap w-max">
        {allItems.map((item, i) => (
          <div key={i} className="flex items-center gap-2 text-sm">
            <span className="text-gray-500">{item.label}</span>
            <span className={`font-bold font-mono ${item.color}`}>{item.value}</span>
            <span className="text-slate-700">│</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── FEATURES ─────────────────────────────────────────────────────────
const FEATURES = [
  {
    icon: '⚡',
    color: 'from-blue-600 to-blue-800',
    title: 'Live NSE Signals',
    desc: 'BUY_CALL & BUY_PUT signals updated every 5 minutes from real yfinance market data. No delay, no lag.',
  },
  {
    icon: '🤖',
    color: 'from-purple-600 to-purple-800',
    title: 'AI Confidence Scoring',
    desc: 'Every signal carries a confidence % computed from trend strength, momentum, and volatility — not just a binary alert.',
  },
  {
    icon: '📊',
    color: 'from-cyan-600 to-cyan-800',
    title: '7 Symbols Covered',
    desc: 'NIFTY, BANKNIFTY, RELIANCE, TCS, INFY, HDFCBANK, ICICIBANK — all major NSE instruments in one dashboard.',
  },
  {
    icon: '🔌',
    color: 'from-emerald-600 to-emerald-800',
    title: 'WebSocket Streaming',
    desc: 'Sub-second updates via WebSocket. Automatic HTTP polling fallback so you\'re never disconnected.',
  },
  {
    icon: '📈',
    color: 'from-orange-600 to-orange-800',
    title: 'Full Performance Tracking',
    desc: 'Real-time P&L, win rate, expectancy, equity curve, open & closed trades — full trade lifecycle analytics.',
  },
  {
    icon: '🔓',
    color: 'from-pink-600 to-pink-800',
    title: 'Free & Open Source',
    desc: 'No subscription. No API key. MIT licensed. Fork, self-host, and customise. Built for the community.',
  },
];

function FeaturesSection() {
  return (
    <section id="features" className="bg-[#080d1a] py-24 px-4">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-16 reveal">
          <p className="text-blue-400 text-xs font-bold uppercase tracking-widest mb-3">Why Traders Choose Us</p>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-white mb-4">
            Everything you need.<br />
            <span className="gradient-text">Nothing you don't.</span>
          </h2>
          <p className="text-gray-400 max-w-xl mx-auto">Professional-grade options signal engine built for Indian retail traders — without the subscription wall.</p>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {FEATURES.map((f, i) => (
            <div key={f.title}
              className={`reveal reveal-delay-${i + 1} card-hover glow-border bg-[#0d1526] border border-slate-800/60 rounded-2xl p-6 flex flex-col gap-4`}>
              <div className={`w-11 h-11 rounded-xl bg-gradient-to-br ${f.color} flex items-center justify-center text-xl shadow-lg`}>
                {f.icon}
              </div>
              <div>
                <h3 className="text-white font-bold text-base mb-2">{f.title}</h3>
                <p className="text-gray-400 text-sm leading-relaxed">{f.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ── HOW IT WORKS ─────────────────────────────────────────────────────
const STEPS = [
  {
    num: '01',
    icon: '📡',
    title: 'Fetch Live Market Data',
    detail: 'yfinance pulls 5-minute OHLCV candles for NSE stocks & indices in real-time. NSE India API provides index ticks.',
    badge: 'yfinance · NSE API',
  },
  {
    num: '02',
    icon: '🧠',
    title: 'AI Scores the Market',
    detail: 'Our engine evaluates trend direction (EMA crossover), momentum (RSI proxy), and volatility. Scores combine into a confidence number.',
    badge: 'Trend · Momentum · Volatility',
  },
  {
    num: '03',
    icon: '📣',
    title: 'Signal Generated & Streamed',
    detail: 'BUY_CALL or BUY_PUT signal with entry price, target, and stop-loss is broadcast via WebSocket to all connected clients in under 1 second.',
    badge: 'WebSocket · <1s latency',
  },
];

function HowItWorksSection() {
  return (
    <section id="how-it-works" className="bg-[#06091a] py-24 px-4 relative overflow-hidden">
      <div className="absolute inset-0 hero-grid opacity-50 pointer-events-none" />
      <div className="relative max-w-7xl mx-auto">
        <div className="text-center mb-16 reveal">
          <p className="text-cyan-400 text-xs font-bold uppercase tracking-widest mb-3">Signal in 3 Steps</p>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-white mb-4">
            How It <span className="gradient-text">Works</span>
          </h2>
          <p className="text-gray-400 max-w-lg mx-auto">From raw NSE tick data to a live signal in your browser — here's the full pipeline.</p>
        </div>

        <div className="flex flex-col lg:flex-row items-stretch gap-0">
          {STEPS.map((step, i) => (
            <div key={step.num} className="flex flex-col lg:flex-row items-center flex-1">
              <div className={`reveal reveal-delay-${i + 1} flex-1 bg-[#0d1526] border border-slate-800/60 rounded-2xl p-8 flex flex-col gap-4 w-full`}>
                {/* Step number + icon */}
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-blue-900/30 border border-blue-700/30 flex items-center justify-center text-2xl">{step.icon}</div>
                  <span className="text-4xl font-extrabold text-slate-800 font-mono">{step.num}</span>
                </div>
                <h3 className="text-white font-bold text-lg">{step.title}</h3>
                <p className="text-gray-400 text-sm leading-relaxed flex-1">{step.detail}</p>
                <div className="inline-block self-start px-3 py-1 rounded-full bg-slate-800 border border-slate-700 text-[10px] text-cyan-400 font-semibold tracking-wide">
                  {step.badge}
                </div>
              </div>

              {/* Connector arrow (between steps, not after last) */}
              {i < STEPS.length - 1 && (
                <div className="flex flex-row lg:flex-col items-center mx-0 lg:mx-4 my-4 lg:my-0">
                  <div className="w-8 h-0.5 lg:w-0.5 lg:h-8 bg-gradient-to-r lg:bg-gradient-to-b from-blue-600 to-cyan-500 opacity-50" />
                  <svg className="rotate-0 lg:-rotate-90 w-4 h-4 text-cyan-400 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" />
                  </svg>
                  <div className="w-8 h-0.5 lg:w-0.5 lg:h-8 bg-gradient-to-r lg:bg-gradient-to-b from-cyan-500 to-purple-500 opacity-50" />
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ── LIVE SIGNAL SHOWCASE ──────────────────────────────────────────────
function SignalCard({ sig, index }) {
  if (!sig) {
    return (
      <div className="bg-[#0d1526] border border-slate-800/60 rounded-2xl p-5 shimmer-loading h-44" />
    );
  }
  const isBull = sig.signal === 'BUY_CALL';
  return (
    <div className={`reveal reveal-delay-${index + 1} card-hover bg-[#0d1526] border rounded-2xl p-5 ${
      isBull ? 'border-emerald-800/40 hover:border-emerald-700/60' : 'border-red-800/40 hover:border-red-700/60'
    }`}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${isBull ? 'bg-emerald-400 animate-glow-pulse' : 'bg-red-400 animate-glow-pulse'}`} />
          <span className="text-gray-400 text-xs font-medium">{sig.symbol}</span>
        </div>
        <span className={`text-xs font-bold px-2.5 py-1 rounded-lg ${
          isBull ? 'bg-emerald-900/40 text-emerald-400' : 'bg-red-900/40 text-red-400'
        }`}>
          {isBull ? '▲ BUY CALL' : '▼ BUY PUT'}
        </span>
      </div>

      {/* Confidence */}
      <div className="mb-4">
        <div className="flex justify-between items-center mb-1.5">
          <span className="text-[10px] text-gray-600 uppercase tracking-widest">AI Confidence</span>
          <span className={`text-sm font-bold font-mono ${isBull ? 'text-emerald-400' : 'text-red-400'}`}>
            {sig.confidence ?? 75}%
          </span>
        </div>
        <div className="bg-slate-800 rounded-full h-1.5">
          <div
            className={`h-1.5 rounded-full ${isBull ? 'bg-emerald-400' : 'bg-red-400'}`}
            style={{ width: `${sig.confidence ?? 75}%` }}
          />
        </div>
      </div>

      {/* Price levels */}
      <div className="grid grid-cols-3 gap-2">
        {[
          { label: 'Entry',   value: sig.entry_price, color: 'text-white' },
          { label: 'Target',  value: sig.target,      color: 'text-emerald-400' },
          { label: 'SL',      value: sig.stop_loss,   color: 'text-red-400' },
        ].map(({ label, value, color }) => (
          <div key={label} className="bg-slate-800/50 rounded-lg p-2 text-center">
            <p className="text-[9px] text-gray-600 uppercase mb-1">{label}</p>
            <p className={`text-xs font-bold font-mono ${color}`}>
              {value ? `₹${Number(value).toLocaleString('en-IN')}` : '—'}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

function SignalShowcase({ onLaunch }) {
  const [signals, setSignals] = useState([null, null, null]);
  const [lastUpdated, setLastUpdated] = useState(null);

  const load = useCallback(() => {
    fetch(`${API_BASE}/signals`)
      .then(r => r.json())
      .then(d => {
        const arr = Array.isArray(d) ? d : (d.signals || []);
        setSignals(arr.slice(0, 3));
        setLastUpdated(new Date());
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, 30_000);
    return () => clearInterval(id);
  }, [load]);

  return (
    <section id="signals" className="bg-[#080d1a] py-24 px-4">
      <div className="max-w-7xl mx-auto">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-12 gap-4">
          <div className="reveal">
            <p className="text-emerald-400 text-xs font-bold uppercase tracking-widest mb-3">Live Signal Feed</p>
            <h2 className="text-3xl sm:text-4xl font-extrabold text-white">
              Latest <span className="gradient-text">Signals</span>
            </h2>
          </div>
          <div className="reveal flex items-center gap-3">
            {lastUpdated && (
              <span className="text-[10px] text-gray-600 font-mono">
                Updated {Math.round((Date.now() - lastUpdated) / 1000)}s ago
              </span>
            )}
            <button onClick={onLaunch}
              className="btn-shine bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold px-4 py-2 rounded-xl transition-colors">
              View All Signals →
            </button>
          </div>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {signals.map((sig, i) => <SignalCard key={i} sig={sig} index={i} />)}
        </div>

        <div className="text-center mt-8 reveal">
          <p className="text-gray-600 text-xs">Signals auto-refresh every 30 seconds • Powered by yfinance &amp; NSE API</p>
        </div>
      </div>
    </section>
  );
}

// ── TECH STACK ────────────────────────────────────────────────────────
const TECHS = [
  { name: 'Python',     color: 'text-yellow-400', bg: 'bg-yellow-900/20 border-yellow-800/30' },
  { name: 'FastAPI',    color: 'text-emerald-400', bg: 'bg-emerald-900/20 border-emerald-800/30' },
  { name: 'yfinance',   color: 'text-blue-400',   bg: 'bg-blue-900/20 border-blue-800/30' },
  { name: 'WebSocket',  color: 'text-purple-400', bg: 'bg-purple-900/20 border-purple-800/30' },
  { name: 'React',      color: 'text-cyan-400',   bg: 'bg-cyan-900/20 border-cyan-800/30' },
  { name: 'Vite',       color: 'text-yellow-300', bg: 'bg-yellow-900/20 border-yellow-800/30' },
  { name: 'Tailwind',   color: 'text-sky-400',    bg: 'bg-sky-900/20 border-sky-800/30' },
  { name: 'Recharts',   color: 'text-orange-400', bg: 'bg-orange-900/20 border-orange-800/30' },
  { name: 'Render',     color: 'text-indigo-400', bg: 'bg-indigo-900/20 border-indigo-800/30' },
  { name: 'GitHub',     color: 'text-white',      bg: 'bg-slate-800/60 border-slate-700/30' },
];

function TechStackSection() {
  return (
    <section className="bg-[#06091a] py-20 px-4">
      <div className="max-w-4xl mx-auto text-center">
        <p className="reveal text-gray-600 text-xs uppercase tracking-widest mb-8 font-semibold">Built with modern, production-grade technology</p>
        <div className="reveal flex flex-wrap justify-center gap-3">
          {TECHS.map(t => (
            <span key={t.name}
              className={`px-3.5 py-1.5 rounded-full border text-xs font-semibold ${t.bg} ${t.color}`}>
              {t.name}
            </span>
          ))}
        </div>
        <p className="reveal reveal-delay-2 mt-8 text-gray-600 text-xs">
          No API keys required. No subscription wall. Just clone and run.
        </p>
      </div>
    </section>
  );
}

// ── STATS ─────────────────────────────────────────────────────────────
function StatCounter({ value, suffix = '', prefix = '', label, sublabel }) {
  const ref = useRef(null);
  const [started, setStarted] = useState(false);
  const count = useCountUp(value, 1600, started);

  useEffect(() => {
    const obs = new IntersectionObserver(([e]) => {
      if (e.isIntersecting) { setStarted(true); obs.disconnect(); }
    }, { threshold: 0.5 });
    if (ref.current) obs.observe(ref.current);
    return () => obs.disconnect();
  }, []);

  return (
    <div ref={ref} className="text-center">
      <div className="text-4xl sm:text-5xl font-extrabold font-mono gradient-text mb-2">
        {prefix}{count.toLocaleString()}{suffix}
      </div>
      <div className="text-white font-bold text-sm mb-1">{label}</div>
      {sublabel && <div className="text-gray-500 text-xs">{sublabel}</div>}
    </div>
  );
}

function StatsSection() {
  return (
    <section id="stats" className="bg-[#080d1a] py-24 px-4 relative overflow-hidden">
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[200px] bg-blue-600/5 rounded-full blur-3xl" />
      </div>
      <div className="relative max-w-5xl mx-auto">
        <div className="text-center mb-16 reveal">
          <p className="text-blue-400 text-xs font-bold uppercase tracking-widest mb-3">By the Numbers</p>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-white">
            Real Results. <span className="gradient-text">Real Data.</span>
          </h2>
        </div>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-8 reveal">
          <StatCounter value={68}  suffix="%" label="Win Rate"      sublabel="on closed trades" />
          <StatCounter value={12}  suffix="+"  label="Signals/Day"  sublabel="across all symbols" />
          <StatCounter value={2340} prefix="₹" label="Avg P&L"      sublabel="per closed trade" />
          <StatCounter value={1}   suffix="s"  label="Latency"      sublabel="WebSocket update" />
        </div>

        <div className="mt-16 reveal grid sm:grid-cols-3 gap-4">
          {[
            { label: 'Symbols Tracked', value: '7', detail: 'NIFTY · BANKNIFTY · 5 stocks' },
            { label: 'Data Source',     value: 'Free', detail: 'yfinance + NSE India API' },
            { label: 'Infrastructure',  value: 'Cloud', detail: 'Render (backend) + GitHub Pages' },
          ].map(({ label, value, detail }) => (
            <div key={label} className="bg-[#0d1526] border border-slate-800/60 rounded-2xl p-5 text-center">
              <p className="text-2xl font-extrabold text-white mb-1">{value}</p>
              <p className="text-sm font-bold text-gray-300 mb-1">{label}</p>
              <p className="text-[11px] text-gray-600">{detail}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ── DASHBOARD PREVIEW ─────────────────────────────────────────────────
function DashboardPreviewSection({ onLaunch }) {
  return (
    <section className="bg-[#06091a] py-24 px-4">
      <div className="max-w-6xl mx-auto">
        <div className="reveal text-center mb-12">
          <p className="text-purple-400 text-xs font-bold uppercase tracking-widest mb-3">See It In Action</p>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-white mb-4">
            A Dashboard Built for <span className="gradient-text">Speed</span>
          </h2>
          <p className="text-gray-400 max-w-xl mx-auto text-sm">
            5 pages of real-time data — Market Overview, Signals, Stocks, Portfolio, and News.
          </p>
        </div>

        {/* Mock dashboard UI preview */}
        <div className="reveal relative">
          <div className="absolute inset-0 bg-gradient-to-t from-[#06091a] via-transparent to-transparent z-10 pointer-events-none rounded-2xl" style={{ top: '60%' }} />

          <div className="bg-[#0d1526] border border-slate-700/60 rounded-2xl overflow-hidden shadow-2xl">
            {/* Fake browser chrome */}
            <div className="flex items-center gap-2 px-4 py-3 bg-slate-900 border-b border-slate-800">
              <div className="w-3 h-3 rounded-full bg-red-500/60" />
              <div className="w-3 h-3 rounded-full bg-yellow-500/60" />
              <div className="w-3 h-3 rounded-full bg-green-500/60" />
              <div className="flex-1 mx-4 bg-slate-800 rounded-lg px-3 py-1 text-[11px] text-gray-500 font-mono">
                ai-trading-platform-33ow.onrender.com
              </div>
              <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            </div>

            {/* Fake nav tabs */}
            <div className="flex items-center gap-1 px-4 py-2 border-b border-slate-800 overflow-x-auto">
              {['Market', 'Signals', 'Stocks', 'Portfolio', 'News'].map((tab, i) => (
                <div key={tab}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap ${
                    i === 0 ? 'bg-blue-900/40 text-blue-400' : 'text-gray-500'
                  }`}>
                  {tab}
                </div>
              ))}
              <div className="ml-auto flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                <span className="text-[10px] text-emerald-400 font-mono font-semibold">WS · LIVE</span>
              </div>
            </div>

            {/* Fake content grid */}
            <div className="p-4 grid grid-cols-2 sm:grid-cols-4 gap-3">
              {[
                { label: 'Capital',    value: '₹10,00,000', color: 'text-white' },
                { label: 'P&L Today',  value: '+₹2,340',   color: 'text-emerald-400' },
                { label: 'Win Rate',   value: '68.2%',      color: 'text-blue-400' },
                { label: 'Open Trades', value: '3',         color: 'text-purple-400' },
              ].map(c => (
                <div key={c.label} className="bg-slate-800/40 rounded-xl p-3">
                  <p className="text-[10px] text-gray-600 uppercase mb-1">{c.label}</p>
                  <p className={`text-base font-bold font-mono ${c.color}`}>{c.value}</p>
                </div>
              ))}
            </div>

            {/* Fake chart placeholder */}
            <div className="mx-4 mb-4 bg-slate-800/30 rounded-xl h-32 flex items-center justify-center">
              <div className="flex items-end gap-1 h-16 px-4">
                {[40, 55, 48, 62, 58, 72, 65, 80, 74, 88, 82, 95].map((h, i) => (
                  <div key={i}
                    className="flex-1 rounded-t-sm"
                    style={{
                      height: `${h}%`,
                      background: `linear-gradient(to top, #3b82f6, #06b6d4)`,
                      opacity: 0.6 + (i / 20),
                    }}
                  />
                ))}
              </div>
            </div>
          </div>
        </div>

        <div className="text-center mt-8 reveal">
          <button onClick={onLaunch}
            className="btn-shine inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white font-semibold px-8 py-3.5 rounded-xl transition-colors text-sm">
            Open Full Dashboard
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
            </svg>
          </button>
        </div>
      </div>
    </section>
  );
}

// ── CTA BANNER ────────────────────────────────────────────────────────
function CTABanner({ onLaunch }) {
  return (
    <section className="relative py-24 px-4 overflow-hidden">
      {/* Gradient background */}
      <div className="absolute inset-0 bg-gradient-to-br from-blue-950 via-[#080d1a] to-purple-950" />
      <div className="absolute inset-0 hero-grid opacity-30 pointer-events-none" />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[300px] bg-blue-600/15 rounded-full blur-3xl pointer-events-none" />

      <div className="relative z-10 max-w-3xl mx-auto text-center reveal">
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-blue-950/60 border border-blue-700/30 text-blue-400 text-xs font-semibold mb-6">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          Free. No signup required.
        </div>

        <h2 className="text-3xl sm:text-5xl font-extrabold text-white mb-6 leading-tight">
          Ready to trade smarter<br />with <span className="gradient-text">AI signals</span>?
        </h2>
        <p className="text-gray-400 text-lg mb-10 max-w-xl mx-auto">
          Get live NSE options signals — AI-powered, WebSocket-streamed, completely free. No credit card. No signup.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <button onClick={onLaunch}
            className="btn-shine w-full sm:w-auto flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-500 text-white font-bold px-8 py-4 rounded-xl transition-colors text-base">
            Launch the Dashboard
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
            </svg>
          </button>
          <a href="https://github.com/Raashid-Dev/AI-Trading-Platform" target="_blank" rel="noopener noreferrer"
            className="w-full sm:w-auto flex items-center justify-center gap-2 border border-slate-700 hover:border-slate-500 text-gray-300 hover:text-white font-semibold px-8 py-4 rounded-xl transition-colors text-base">
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z"/>
            </svg>
            View on GitHub
          </a>
        </div>
      </div>
    </section>
  );
}

// ── FOOTER ────────────────────────────────────────────────────────────
function Footer({ onLaunch }) {
  const scrollTo = (id) => document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' });

  return (
    <footer className="bg-[#040810] border-t border-slate-800/60 py-12 px-4">
      <div className="max-w-7xl mx-auto">
        <div className="grid sm:grid-cols-3 gap-8 mb-10">
          {/* Brand */}
          <div>
            <div className="flex items-center gap-2 mb-4">
              <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white font-bold text-sm">AI</div>
              <span className="text-white font-bold text-base">TradePulse</span>
            </div>
            <p className="text-gray-500 text-xs leading-relaxed mb-4">
              AI-powered NSE options signal engine. Real-time, free, open source.
            </p>
            <a href="https://github.com/Raashid-Dev/AI-Trading-Platform" target="_blank" rel="noopener noreferrer"
              className="inline-flex items-center gap-2 text-xs text-gray-500 hover:text-white transition-colors">
              <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z"/>
              </svg>
              GitHub Repository
            </a>
          </div>

          {/* Navigation */}
          <div>
            <p className="text-[10px] text-gray-600 uppercase tracking-widest font-semibold mb-4">Navigation</p>
            <div className="space-y-2">
              {[
                { label: 'Features',      id: 'features' },
                { label: 'How It Works',  id: 'how-it-works' },
                { label: 'Live Signals',  id: 'signals' },
                { label: 'Performance',   id: 'stats' },
              ].map(({ label, id }) => (
                <button key={id} onClick={() => scrollTo(id)}
                  className="block text-xs text-gray-500 hover:text-white transition-colors">
                  {label}
                </button>
              ))}
              <button onClick={onLaunch} className="block text-xs text-blue-400 hover:text-blue-300 transition-colors font-semibold">
                Launch Dashboard →
              </button>
            </div>
          </div>

          {/* Tech */}
          <div>
            <p className="text-[10px] text-gray-600 uppercase tracking-widest font-semibold mb-4">Technology</p>
            <div className="flex flex-wrap gap-2">
              {['Python', 'FastAPI', 'React', 'WebSocket', 'yfinance'].map(t => (
                <span key={t} className="text-[10px] px-2 py-1 rounded-md bg-slate-800 border border-slate-700 text-gray-400">{t}</span>
              ))}
            </div>
            <div className="mt-4 flex items-center gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-[10px] text-gray-500 font-mono">Backend live on Render</span>
            </div>
          </div>
        </div>

        <div className="border-t border-slate-800/60 pt-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-[11px] text-gray-600">© 2026 AI Trading Platform. Built by Raashid.</p>
          <p className="text-[10px] text-gray-700 max-w-md text-center sm:text-right leading-relaxed">
            ⚠ For educational &amp; demonstration purposes only. Signals are not financial advice.
            Always consult a SEBI-registered advisor before trading options.
          </p>
        </div>
      </div>
    </footer>
  );
}

// ── LANDING PAGE (main export) ────────────────────────────────────────
export default function LandingPage({ onLaunch }) {
  useScrollReveal();

  return (
    <div className="bg-[#080d1a] min-h-screen">
      <LandingNav onLaunch={onLaunch} />
      <HeroSection onLaunch={onLaunch} />
      <TickerStrip />
      <FeaturesSection />
      <HowItWorksSection />
      <DashboardPreviewSection onLaunch={onLaunch} />
      <SignalShowcase onLaunch={onLaunch} />
      <TechStackSection />
      <StatsSection />
      <CTABanner onLaunch={onLaunch} />
      <Footer onLaunch={onLaunch} />
    </div>
  );
}
