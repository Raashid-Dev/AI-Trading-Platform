import { useState, useEffect, useCallback } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import PriceChart from '../components/PriceChart';

const API_BASE = (() => {
  const v = import.meta.env.VITE_API_URL || import.meta.env.VITE_BASE_URL || '';
  return v.startsWith('http') ? v : 'http://localhost:8000';
})();

const SYMBOLS = ['NIFTY', 'BANKNIFTY', 'RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK'];

// ── Helpers ───────────────────────────────────────────────────
function fmt(v, digits = 2) {
  if (v == null) return '—';
  return typeof v === 'number' ? v.toFixed(digits) : v;
}
function fmtCr(v) {
  if (v == null) return '—';
  return v >= 100000 ? `₹${(v / 100000).toFixed(1)}L Cr` : `₹${(v / 1000).toFixed(0)}K Cr`;
}

// ── Sub-components ────────────────────────────────────────────
function StatBadge({ label, value, color = 'text-white' }) {
  return (
    <div className="bg-gray-800/60 rounded-xl p-3">
      <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">{label}</p>
      <p className={`text-base font-bold font-mono ${color}`}>{value}</p>
    </div>
  );
}

function LiveBadge({ source }) {
  const live = source && source.includes('finnhub');
  return (
    <span className={`text-[9px] px-1.5 py-0.5 rounded-full border font-semibold ${
      live ? 'text-green-400 bg-green-900/20 border-green-800/30'
           : 'text-gray-500 bg-gray-800/30 border-gray-700/30'
    }`}>
      {live ? '● LIVE' : '● FY25 Static'}
    </span>
  );
}

function MetricGrid({ metrics, source }) {
  const rows = [
    { label: 'P/E Ratio',      value: metrics.pe          != null ? `${fmt(metrics.pe)}x`           : null },
    { label: 'P/BV',           value: metrics.pbv         != null ? `${fmt(metrics.pbv)}x`           : null },
    { label: 'Div Yield',      value: metrics.divYield    != null ? `${fmt(metrics.divYield)}%`      : null, green: true },
    { label: '52w High',       value: metrics['52wHigh']  != null ? `₹${fmt(metrics['52wHigh'], 0)}` : null },
    { label: '52w Low',        value: metrics['52wLow']   != null ? `₹${fmt(metrics['52wLow'], 0)}`  : null },
    { label: 'EPS (TTM)',      value: metrics.eps         != null ? `₹${fmt(metrics.eps)}`           : null },
    { label: 'Beta',           value: metrics.beta        != null ? fmt(metrics.beta)                : null },
    { label: 'ROE',            value: metrics.roe         != null ? `${fmt(metrics.roe)}%`           : null },
    { label: 'Net Margin',     value: metrics.netMargin   != null ? `${fmt(metrics.netMargin)}%`     : null },
    { label: 'Rev Growth YoY', value: metrics.revenueGrowth != null ? `${fmt(metrics.revenueGrowth)}%` : null },
  ].filter(r => r.value != null);

  if (rows.length === 0) return null;

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <p className="text-[10px] text-gray-500 uppercase tracking-widest">Key Metrics</p>
        <LiveBadge source={source} />
      </div>
      <div className="grid grid-cols-2 gap-2">
        {rows.map(r => (
          <div key={r.label} className="bg-gray-800/50 rounded-lg p-2">
            <p className="text-[10px] text-gray-600">{r.label}</p>
            <p className={`text-sm font-bold ${r.green ? 'text-green-400' : 'text-white'}`}>{r.value}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function RevenueChart({ data }) {
  if (!data || data.length === 0) return (
    <div className="h-28 flex items-center justify-center text-gray-600 text-sm">
      Revenue data not available for indices
    </div>
  );

  return (
    <div>
      <div className="grid grid-cols-2 gap-2 mb-3">
        {data.map((d, i) => {
          const prev   = data[i - 1];
          const qoq    = prev?.rev ? ((d.rev - prev.rev) / prev.rev * 100) : null;
          const netQoq = prev?.net ? ((d.net - prev.net) / prev.net * 100) : null;
          return (
            <div key={d.q}
              className={`rounded-xl p-3 ${i === data.length - 1
                ? 'bg-blue-900/20 border border-blue-700/30' : 'bg-gray-800/40'}`}>
              <p className="text-[10px] text-gray-500 mb-1">
                {d.q} {i === data.length - 1 && <span className="text-blue-400 font-bold">LATEST</span>}
              </p>
              <p className="text-sm font-bold text-white font-mono">{fmtCr(d.rev)}</p>
              <p className="text-[10px] text-gray-500">Revenue</p>
              {qoq != null && (
                <p className={`text-[10px] font-semibold mt-0.5 ${qoq >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {qoq >= 0 ? '+' : ''}{qoq.toFixed(1)}% QoQ
                </p>
              )}
              {d.net != null && (
                <p className="text-xs font-mono text-gray-300 mt-1">
                  {fmtCr(d.net)} <span className="text-gray-600">net</span>
                  {netQoq != null && (
                    <span className={`text-[10px] font-semibold ml-1 ${netQoq >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {netQoq >= 0 ? '+' : ''}{netQoq.toFixed(1)}%
                    </span>
                  )}
                </p>
              )}
            </div>
          );
        })}
      </div>

      <ResponsiveContainer width="100%" height={130}>
        <BarChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
          <XAxis dataKey="q" tick={{ fill: '#6b7280', fontSize: 9 }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fill: '#6b7280', fontSize: 9 }} axisLine={false} tickLine={false}
            tickFormatter={v => v >= 100000 ? `${(v / 100000).toFixed(0)}L` : `${(v / 1000).toFixed(0)}K`} />
          <Tooltip
            formatter={(v, n) => [fmtCr(v), n === 'rev' ? 'Revenue' : 'Net Profit']}
            contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8, fontSize: 11 }}
          />
          <Bar dataKey="rev" fill="#3b82f6" radius={[3, 3, 0, 0]} name="rev" isAnimationActive={false} />
          <Bar dataKey="net" fill="#10b981" radius={[3, 3, 0, 0]} name="net" isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function EarningsTable({ earnings }) {
  if (!earnings || earnings.length === 0) return null;
  return (
    <div>
      <p className="text-[10px] text-gray-500 uppercase tracking-widest mb-2">EPS: Actual vs Estimate</p>
      <div className="space-y-1">
        {earnings.map((e, i) => {
          const beat     = e.actual != null && e.estimate != null && e.actual >= e.estimate;
          const surprise = e.surprisePercent ?? e.surprisePct;
          return (
            <div key={i} className="flex items-center justify-between bg-gray-800/40 rounded-lg px-3 py-2">
              <span className="text-[10px] text-gray-500">{e.period}</span>
              <div className="flex items-center gap-3">
                <span className="text-xs font-mono text-gray-400">
                  Est: {e.estimate != null ? fmt(e.estimate) : '—'}
                </span>
                <span className={`text-xs font-bold font-mono ${beat ? 'text-green-400' : 'text-red-400'}`}>
                  Act: {e.actual != null ? fmt(e.actual) : '—'}
                </span>
                {surprise != null && (
                  <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${
                    beat ? 'bg-green-900/30 text-green-400' : 'bg-red-900/30 text-red-400'}`}>
                    {surprise >= 0 ? '+' : ''}{fmt(surprise)}%
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function NewsStrip({ symbol }) {
  const [news, setNews]       = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetch(`${API_BASE}/news/company/${symbol}`)
      .then(r => r.json())
      .then(d => { setNews(d.items || []); setLoading(false); })
      .catch(() => setLoading(false));
  }, [symbol]);

  if (loading) return (
    <div className="space-y-2 animate-pulse">
      {[1, 2, 3].map(i => <div key={i} className="h-12 bg-gray-800/50 rounded-lg" />)}
    </div>
  );
  if (news.length === 0) return (
    <p className="text-xs text-gray-600 py-2">No recent company news available.</p>
  );

  return (
    <div className="space-y-2">
      {news.slice(0, 6).map((n, i) => (
        <a key={i} href={n.link} target="_blank" rel="noopener noreferrer"
          className="block bg-gray-800/40 hover:bg-gray-800/70 rounded-lg px-3 py-2 transition-colors">
          <p className="text-xs font-medium text-gray-200 leading-snug line-clamp-2">{n.title}</p>
          <p className="text-[10px] text-gray-600 mt-0.5">{n.source}</p>
        </a>
      ))}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────
export default function StocksPage({ state }) {
  const [selected, setSelected]       = useState('TCS');
  const [fund, setFund]               = useState(null);
  const [fundLoading, setFundLoading] = useState(true);
  const { price_history, symbol_snapshot } = state;
  const snap = (symbol_snapshot || {})[selected] || {};

  const loadFundamentals = useCallback((sym) => {
    setFundLoading(true);
    fetch(`${API_BASE}/fundamentals/${sym}`)
      .then(r => r.json())
      .then(d => { setFund(d); setFundLoading(false); })
      .catch(() => setFundLoading(false));
  }, []);

  useEffect(() => { loadFundamentals(selected); }, [selected, loadFundamentals]);

  return (
    <div className="space-y-4">
      {/* Symbol selector */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-4">
        <p className="text-[10px] text-gray-500 uppercase tracking-widest mb-3">Select Symbol</p>
        <div className="flex flex-wrap gap-2">
          {SYMBOLS.map(sym => {
            const s  = (symbol_snapshot || {})[sym] || {};
            const up = (s.change_pct || 0) >= 0;
            return (
              <button key={sym} onClick={() => setSelected(sym)}
                className={`flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-semibold transition-all border ${
                  selected === sym
                    ? 'bg-blue-900/30 border-blue-600 text-blue-300'
                    : 'bg-gray-800/60 border-gray-700/50 text-gray-400 hover:border-gray-600 hover:text-white'
                }`}>
                <span>{sym}</span>
                {s.price && (
                  <span className={`font-mono ${up ? 'text-green-400' : 'text-red-400'}`}>
                    {up ? '+' : ''}{s.change_pct?.toFixed(2)}%
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Main grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

        {/* Left: chart + stats + news */}
        <div className="lg:col-span-2 space-y-4">
          <PriceChart symbol={selected} symbolSnapshot={symbol_snapshot} />

          {snap.price && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <StatBadge label="Price"    value={`₹${snap.price?.toLocaleString('en-IN')}`} />
              <StatBadge label="Change"   value={`${snap.change_pct >= 0 ? '+' : ''}${snap.change_pct?.toFixed(2)}%`}
                color={snap.change_pct >= 0 ? 'text-green-400' : 'text-red-400'} />
              <StatBadge label="EMA 9/21"
                value={`${snap.ema9?.toLocaleString('en-IN', { maximumFractionDigits: 0 })} / ${snap.ema21?.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`}
                color="text-blue-400" />
              <StatBadge label="VWAP"
                value={`₹${snap.vwap?.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`}
                color="text-purple-400" />
            </div>
          )}

          <div className="bg-gray-900 rounded-xl border border-gray-800 p-4">
            <p className="text-[10px] text-gray-500 uppercase tracking-widest mb-3">
              Latest News — {selected}
            </p>
            <NewsStrip symbol={selected} />
          </div>
        </div>

        {/* Right: fundamentals */}
        <div className="space-y-4">
          {fundLoading ? (
            <div className="bg-gray-900 rounded-xl border border-gray-800 p-4 animate-pulse space-y-3">
              <div className="h-4 w-3/4 bg-gray-800 rounded" />
              <div className="h-3 w-1/2 bg-gray-800 rounded" />
              <div className="h-20 bg-gray-800/60 rounded" />
            </div>
          ) : fund ? (
            <div className="bg-gray-900 rounded-xl border border-gray-800 p-4 space-y-4">
              <div>
                <p className="text-[10px] text-gray-500 uppercase tracking-widest mb-1">Company</p>
                <p className="text-sm font-bold text-white">{fund.meta?.fullName || selected}</p>
                <p className="text-[10px] text-blue-400 font-semibold mb-2">{fund.meta?.sector}</p>
                <p className="text-xs text-gray-400 leading-relaxed">{fund.meta?.description}</p>
              </div>
              {fund.metrics && <MetricGrid metrics={fund.metrics} source={fund.source} />}
              {fund.earnings?.length > 0 && <EarningsTable earnings={fund.earnings} />}
            </div>
          ) : null}

          <div className="bg-gray-900 rounded-xl border border-gray-800 p-4">
            <div className="flex items-center justify-between mb-3">
              <p className="text-[10px] text-gray-500 uppercase tracking-widest">Quarterly Revenue</p>
              {fund?.source && <LiveBadge source={fund.source} />}
            </div>
            <RevenueChart data={fund?.revenue} />
          </div>
        </div>
      </div>
    </div>
  );
}
