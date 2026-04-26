import { useEffect, useRef, useState, useCallback } from 'react';
import { createChart, CrosshairMode, ColorType, LineStyle } from 'lightweight-charts';

const API_BASE = (() => {
  const v = import.meta.env.VITE_API_URL || import.meta.env.VITE_BASE_URL || '';
  return v.startsWith('http') ? v : 'http://localhost:8000';
})();

const SYMBOL_FULL = {
  NIFTY: 'NIFTY 50', BANKNIFTY: 'BANK NIFTY', RELIANCE: 'Reliance Industries',
  HDFCBANK: 'HDFC Bank', ICICIBANK: 'ICICI Bank', INFY: 'Infosys', TCS: 'TCS',
};

const TIMEFRAMES = [
  { label: '1m',  interval: '1m',  period: '1d'  },
  { label: '5m',  interval: '5m',  period: '1d'  },
  { label: '15m', interval: '15m', period: '5d'  },
  { label: '1h',  interval: '60m', period: '1mo' },
  { label: '1D',  interval: '1d',  period: '3mo' },
  { label: '1W',  interval: '1wk', period: '1y'  },
];

// Auto-refresh intervals (ms) per timeframe — null = no auto-refresh
const REFRESH_MS = { '1m': 30_000, '5m': 60_000, '15m': 120_000 };

export default function PriceChart({ symbol, symbolSnapshot }) {
  const containerRef = useRef(null);
  const chartRef     = useRef(null);
  const seriesRef    = useRef({});

  const [timeframe, setTimeframe]     = useState('5m');
  const [loading, setLoading]         = useState(true);
  const [error, setError]             = useState(null);
  const [ohlcLatest, setOhlcLatest]   = useState(null);
  const [hovered, setHovered]         = useState(null);   // crosshair OHLCV

  const snap = (symbolSnapshot || {})[symbol] || {};
  const up   = (snap.change_pct || 0) >= 0;

  // ── Init chart once ────────────────────────────────────────
  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#6b7280',
        fontSize: 10,
      },
      grid: {
        vertLines: { color: '#1f2937', style: LineStyle.Solid },
        horzLines: { color: '#1f2937', style: LineStyle.Solid },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { color: '#374151', width: 1, style: LineStyle.Dashed, labelBackgroundColor: '#1f2937' },
        horzLine: { color: '#374151', width: 1, style: LineStyle.Dashed, labelBackgroundColor: '#1f2937' },
      },
      rightPriceScale: { borderColor: '#1f2937' },
      timeScale: {
        borderColor: '#1f2937',
        timeVisible: true,
        secondsVisible: false,
      },
      handleScroll: true,
      handleScale: true,
    });

    // Candlestick
    const candleSeries = chart.addCandlestickSeries({
      upColor:        '#10b981',
      downColor:      '#ef4444',
      borderUpColor:  '#10b981',
      borderDownColor:'#ef4444',
      wickUpColor:    '#10b981',
      wickDownColor:  '#ef4444',
    });

    // Volume bars (lower pane via price scale)
    const volSeries = chart.addHistogramSeries({
      priceFormat:   { type: 'volume' },
      priceScaleId:  'vol',
    });
    chart.priceScale('vol').applyOptions({
      scaleMargins: { top: 0.82, bottom: 0 },
    });

    // EMA 9
    const ema9Series = chart.addLineSeries({
      color: '#3b82f6', lineWidth: 1, lineStyle: LineStyle.Dashed,
      lastValueVisible: false, priceLineVisible: false,
    });

    // EMA 21
    const ema21Series = chart.addLineSeries({
      color: '#f97316', lineWidth: 1, lineStyle: LineStyle.Dashed,
      lastValueVisible: false, priceLineVisible: false,
    });

    // VWAP
    const vwapSeries = chart.addLineSeries({
      color: '#9333ea', lineWidth: 1, lineStyle: LineStyle.SparseDotted,
      lastValueVisible: false, priceLineVisible: false,
    });

    seriesRef.current = { candleSeries, volSeries, ema9Series, ema21Series, vwapSeries };
    chartRef.current  = chart;

    // Crosshair tooltip
    chart.subscribeCrosshairMove(param => {
      if (!param.point || !param.time) { setHovered(null); return; }
      const c = param.seriesData.get(candleSeries);
      const v = param.seriesData.get(volSeries);
      if (c) setHovered({ ...c, volume: v?.value ?? 0 });
    });

    // Responsive
    const ro = new ResizeObserver(entries => {
      for (const e of entries) chart.applyOptions({ width: e.contentRect.width });
    });
    ro.observe(containerRef.current);

    return () => { ro.disconnect(); chart.remove(); };
  }, []);

  // ── Fetch OHLCV whenever symbol or timeframe changes ───────
  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    const tf = TIMEFRAMES.find(t => t.label === timeframe) || TIMEFRAMES[1];

    try {
      const res  = await fetch(`${API_BASE}/chart/${symbol}?interval=${tf.interval}&period=${tf.period}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      if (!data.candles?.length) throw new Error('No data for this timeframe');

      const { candleSeries, volSeries, ema9Series, ema21Series, vwapSeries } = seriesRef.current;
      candleSeries?.setData(data.candles);
      volSeries?.setData(data.volume ?? []);
      ema9Series?.setData(data.ema9 ?? []);
      ema21Series?.setData(data.ema21 ?? []);
      vwapSeries?.setData(data.vwap ?? []);
      chartRef.current?.timeScale().fitContent();
      setOhlcLatest(data.latest);

    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [symbol, timeframe]);

  useEffect(() => {
    fetchData();
    const ms = REFRESH_MS[timeframe];
    if (!ms) return;
    const id = setInterval(fetchData, ms);
    return () => clearInterval(id);
  }, [fetchData]);

  // ── Display values: crosshair overrides latest ─────────────
  const display = hovered || ohlcLatest;

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 shadow-lg flex flex-col">

      {/* ── Header ── */}
      <div className="px-5 py-3 border-b border-gray-800 flex items-start justify-between gap-2 flex-wrap">
        <div>
          <p className="text-[10px] text-gray-500 uppercase tracking-widest font-semibold">
            {SYMBOL_FULL[symbol] || symbol} · Candlestick
          </p>
          {snap.price && (
            <div className="flex items-baseline gap-2 mt-0.5">
              <span className="text-xl font-bold font-mono text-white">
                ₹{snap.price?.toLocaleString('en-IN')}
              </span>
              <span className={`text-sm font-semibold ${up ? 'text-green-400' : 'text-red-400'}`}>
                {up ? '+' : ''}{snap.change_pct?.toFixed(2)}%
              </span>
            </div>
          )}
        </div>

        {/* Timeframe pills */}
        <div className="flex items-center gap-0.5 bg-gray-800/60 rounded-lg p-1">
          {TIMEFRAMES.map(tf => (
            <button key={tf.label} onClick={() => setTimeframe(tf.label)}
              className={`px-2.5 py-1 text-xs font-semibold rounded-md transition-all ${
                timeframe === tf.label
                  ? 'bg-blue-600 text-white shadow'
                  : 'text-gray-500 hover:text-white hover:bg-gray-700/60'
              }`}>
              {tf.label}
            </button>
          ))}
        </div>
      </div>

      {/* ── Technical badges ── */}
      <div className="px-5 py-2 border-b border-gray-800/40 flex items-center gap-2 flex-wrap">
        {snap.ema9  && <span className="text-[10px] px-2 py-0.5 rounded bg-blue-900/30 border border-blue-700/30 text-blue-400 font-mono">EMA9 {snap.ema9?.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</span>}
        {snap.ema21 && <span className="text-[10px] px-2 py-0.5 rounded bg-orange-900/30 border border-orange-700/30 text-orange-400 font-mono">EMA21 {snap.ema21?.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</span>}
        {snap.vwap  && <span className="text-[10px] px-2 py-0.5 rounded bg-purple-900/30 border border-purple-700/30 text-purple-400 font-mono">VWAP {snap.vwap?.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</span>}
        {snap.trend_strength && (
          <span className={`text-[10px] px-2 py-0.5 rounded bg-gray-800 border border-gray-700 font-semibold ${
            snap.trend_strength === 'STRONG_BULL' ? 'text-green-400' :
            snap.trend_strength === 'STRONG_BEAR' ? 'text-red-400' : 'text-yellow-400'
          }`}>{snap.trend_strength.replace('_', ' ')}</span>
        )}
        <div className="ml-auto flex items-center gap-3 text-[10px]">
          <span className="text-gray-600">— Price</span>
          <span className="text-blue-500">--- EMA9</span>
          <span className="text-orange-500">--- EMA21</span>
          <span className="text-purple-500">··· VWAP</span>
        </div>
      </div>

      {/* ── Chart ── */}
      <div className="relative flex-1">
        {loading && (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-gray-900/60 rounded-b-xl">
            <div className="flex items-center gap-2 text-gray-500 text-sm">
              <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
              </svg>
              Loading {timeframe} chart…
            </div>
          </div>
        )}
        {error && !loading && (
          <div className="h-52 flex flex-col items-center justify-center text-gray-600 text-sm gap-2">
            <span>⚠ {error}</span>
            <button onClick={fetchData} className="text-xs text-blue-500 hover:text-blue-400">Retry</button>
          </div>
        )}
        <div ref={containerRef} style={{ height: '280px' }} className="w-full" />
      </div>

      {/* ── OHLCV footer (crosshair or latest candle) ── */}
      {display && (
        <div className="px-5 py-2 border-t border-gray-800/40 flex items-center gap-4 text-[10px] text-gray-500 flex-wrap">
          <span className="text-gray-600">{hovered ? 'Hover' : 'Latest'}</span>
          <span>O <span className="text-white font-mono">{display.open?.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</span></span>
          <span>H <span className="text-green-400 font-mono">{display.high?.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</span></span>
          <span>L <span className="text-red-400 font-mono">{display.low?.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</span></span>
          <span>C <span className="text-white font-mono">{display.close?.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</span></span>
          {(display.volume ?? 0) > 0 && (
            <span>Vol <span className="text-blue-400 font-mono">
              {display.volume >= 1_000_000
                ? `${(display.volume / 1_000_000).toFixed(2)}M`
                : `${(display.volume / 1_000).toFixed(0)}K`}
            </span></span>
          )}
        </div>
      )}
    </div>
  );
}
