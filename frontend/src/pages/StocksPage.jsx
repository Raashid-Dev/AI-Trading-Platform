import { useState, useMemo } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line } from 'recharts';
import PriceChart from '../components/PriceChart';
import { FUNDAMENTALS } from '../data/fundamentals';

const SYMBOLS = ['NIFTY', 'BANKNIFTY', 'RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK'];

function StatBadge({ label, value, color = 'text-white' }) {
  return (
    <div className="bg-gray-800/60 rounded-xl p-3">
      <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">{label}</p>
      <p className={`text-base font-bold font-mono ${color}`}>{value}</p>
    </div>
  );
}

function RevenueChart({ data }) {
  if (!data || data.length === 0) return (
    <div className="h-32 flex items-center justify-center text-gray-600 text-sm">
      Revenue data not available for indices
    </div>
  );

  const fmtCr = (v) => v >= 100000 ? `₹${(v/100000).toFixed(1)}L Cr` : `₹${(v/1000).toFixed(0)}K Cr`;

  return (
    <div>
      <div className="grid grid-cols-2 gap-3 mb-3">
        {data.map((d, i) => {
          const prev  = data[i - 1];
          const qoq   = prev ? ((d.rev - prev.rev) / prev.rev * 100) : null;
          const netQoq= prev ? ((d.net - prev.net) / prev.net * 100) : null;
          return (
            <div key={d.q} className={`rounded-xl p-3 ${i === data.length - 1 ? 'bg-blue-900/20 border border-blue-700/30' : 'bg-gray-800/40'}`}>
              <p className="text-[10px] text-gray-500 mb-1">{d.q} {i === data.length - 1 && <span className="text-blue-400 font-bold">LATEST</span>}</p>
              <p className="text-sm font-bold text-white font-mono">{fmtCr(d.rev)}</p>
              <p className="text-[10px] text-gray-500">Revenue</p>
              {qoq !== null && (
                <p className={`text-[10px] font-semibold mt-0.5 ${qoq >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {qoq >= 0 ? '+' : ''}{qoq.toFixed(1)}% QoQ
                </p>
              )}
              <p className="text-xs font-mono text-gray-300 mt-1">{fmtCr(d.net)} <span className="text-gray-600">net</span></p>
              {netQoq !== null && (
                <p className={`text-[10px] font-semibold ${netQoq >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {netQoq >= 0 ? '+' : ''}{netQoq.toFixed(1)}% net QoQ
                </p>
              )}
            </div>
          );
        })}
      </div>

      <ResponsiveContainer width="100%" height={140}>
        <BarChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
          <XAxis dataKey="q" tick={{ fill: '#6b7280', fontSize: 9 }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fill: '#6b7280', fontSize: 9 }} axisLine={false} tickLine={false}
            tickFormatter={v => v >= 100000 ? `${(v/100000).toFixed(0)}L` : `${(v/1000).toFixed(0)}K`} />
          <Tooltip
            formatter={(v, n) => [`₹${(v/1000).toFixed(0)}K Cr`, n === 'rev' ? 'Revenue' : 'Net Profit']}
            contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8, fontSize: 11 }}
          />
          <Bar dataKey="rev" fill="#3b82f6" radius={[3,3,0,0]} name="rev" />
          <Bar dataKey="net" fill="#10b981" radius={[3,3,0,0]} name="net" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export default function StocksPage({ state }) {
  const [selected, setSelected] = useState('TCS');
  const { price_history, symbol_snapshot } = state;
  const snap  = (symbol_snapshot || {})[selected] || {};
  const fund  = FUNDAMENTALS[selected] || {};

  return (
    <div className="space-y-4">
      {/* Symbol selector */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-4">
        <p className="text-[10px] text-gray-500 uppercase tracking-widest mb-3">Select Symbol</p>
        <div className="flex flex-wrap gap-2">
          {SYMBOLS.map(sym => {
            const s = (symbol_snapshot || {})[sym] || {};
            const up = (s.change_pct || 0) >= 0;
            return (
              <button
                key={sym}
                onClick={() => setSelected(sym)}
                className={`flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-semibold transition-all border ${
                  selected === sym
                    ? 'bg-blue-900/30 border-blue-600 text-blue-300'
                    : 'bg-gray-800/60 border-gray-700/50 text-gray-400 hover:border-gray-600 hover:text-white'
                }`}
              >
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

      {/* Main content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

        {/* Left: chart + price stats */}
        <div className="lg:col-span-2 space-y-4">
          <PriceChart symbol={selected} priceHistory={price_history} symbolSnapshot={symbol_snapshot} />

          {/* Price stats */}
          {snap.price && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <StatBadge label="Price" value={`₹${snap.price?.toLocaleString('en-IN')}`} />
              <StatBadge label="Change" value={`${snap.change_pct >= 0 ? '+' : ''}${snap.change_pct?.toFixed(2)}%`}
                color={snap.change_pct >= 0 ? 'text-green-400' : 'text-red-400'} />
              <StatBadge label="EMA 9 / 21"
                value={`${snap.ema9?.toLocaleString('en-IN', {maximumFractionDigits:0})} / ${snap.ema21?.toLocaleString('en-IN', {maximumFractionDigits:0})}`}
                color="text-blue-400" />
              <StatBadge label="VWAP" value={`₹${snap.vwap?.toLocaleString('en-IN', {maximumFractionDigits:0})}`} color="text-purple-400" />
            </div>
          )}
        </div>

        {/* Right: fundamentals */}
        <div className="space-y-4">
          {/* Company info */}
          <div className="bg-gray-900 rounded-xl border border-gray-800 p-4">
            <p className="text-[10px] text-gray-500 uppercase tracking-widest mb-2">Company</p>
            <p className="text-sm font-bold text-white">{fund.fullName || selected}</p>
            <p className="text-[10px] text-blue-400 font-semibold mb-2">{fund.sector}</p>
            <p className="text-xs text-gray-400 leading-relaxed">{fund.description}</p>

            {fund.type === 'stock' && (
              <div className="grid grid-cols-2 gap-2 mt-3">
                <div className="bg-gray-800/50 rounded-lg p-2">
                  <p className="text-[10px] text-gray-600">P/E Ratio</p>
                  <p className="text-sm font-bold text-white">{fund.pe}x</p>
                </div>
                <div className="bg-gray-800/50 rounded-lg p-2">
                  <p className="text-[10px] text-gray-600">P/BV</p>
                  <p className="text-sm font-bold text-white">{fund.pbv}x</p>
                </div>
                <div className="bg-gray-800/50 rounded-lg p-2">
                  <p className="text-[10px] text-gray-600">Div Yield</p>
                  <p className="text-sm font-bold text-green-400">{fund.divYield}%</p>
                </div>
                <div className="bg-gray-800/50 rounded-lg p-2">
                  <p className="text-[10px] text-gray-600">Mkt Cap</p>
                  <p className="text-sm font-bold text-white">{fund.marketCap}</p>
                </div>
              </div>
            )}
          </div>

          {/* QoQ Revenue */}
          <div className="bg-gray-900 rounded-xl border border-gray-800 p-4">
            <p className="text-[10px] text-gray-500 uppercase tracking-widest mb-3">
              Quarterly Revenue (₹ Cr)
            </p>
            <RevenueChart data={fund.revenue} />
          </div>
        </div>
      </div>
    </div>
  );
}
