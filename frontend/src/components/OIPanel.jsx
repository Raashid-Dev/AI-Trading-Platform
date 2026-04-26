import { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';

const API_BASE = (() => {
  const v = import.meta.env.VITE_API_URL || import.meta.env.VITE_BASE_URL || '';
  return v.startsWith('http') ? v : 'http://localhost:8000';
})();

function fmt(v) {
  if (v == null || isNaN(v)) return '—';
  if (v >= 10_000_000) return `${(v / 10_000_000).toFixed(1)}Cr`;
  if (v >= 100_000)    return `${(v / 100_000).toFixed(1)}L`;
  if (v >= 1_000)      return `${(v / 1_000).toFixed(0)}K`;
  return String(v);
}

function PCRGauge({ pcr }) {
  // PCR < 0.7 = bearish, 0.7–1.2 = neutral, > 1.2 = bullish
  const pct  = Math.min(Math.max((pcr / 2) * 100, 0), 100);
  const bull  = pcr > 1.2;
  const bear  = pcr < 0.7;
  const color = bull ? '#10b981' : bear ? '#ef4444' : '#f59e0b';
  const label = bull ? 'BULLISH' : bear ? 'BEARISH' : 'NEUTRAL';

  return (
    <div className="flex flex-col items-center gap-1">
      <p className="text-[10px] text-gray-500 uppercase tracking-widest">Put-Call Ratio</p>
      <p className={`text-2xl font-bold font-mono`} style={{ color }}>
        {pcr?.toFixed(2)}
      </p>
      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
        bull ? 'bg-green-900/30 text-green-400' :
        bear ? 'bg-red-900/30 text-red-400' : 'bg-yellow-900/30 text-yellow-400'
      }`}>{label}</span>
      {/* bar */}
      <div className="w-full h-1.5 bg-gray-800 rounded-full mt-1">
        <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, background: color }} />
      </div>
    </div>
  );
}

function OIBarChart({ strikes }) {
  if (!strikes?.length) return null;
  const data = strikes.map(s => ({
    strike: s.strike,
    'CE OI': Math.round(s.ce_oi / 1000),
    'PE OI': Math.round(s.pe_oi / 1000),
  }));

  return (
    <ResponsiveContainer width="100%" height={180}>
      <BarChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: -10 }}>
        <XAxis dataKey="strike" tick={{ fill: '#6b7280', fontSize: 8 }} axisLine={false} tickLine={false}
          tickFormatter={v => v.toLocaleString('en-IN')} />
        <YAxis tick={{ fill: '#6b7280', fontSize: 8 }} axisLine={false} tickLine={false}
          tickFormatter={v => `${v}K`} />
        <Tooltip
          formatter={(v, name) => [`${v}K lots`, name]}
          contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8, fontSize: 10 }}
        />
        <Bar dataKey="CE OI" fill="#ef4444" radius={[2, 2, 0, 0]} maxBarSize={16} isAnimationActive={false} />
        <Bar dataKey="PE OI" fill="#10b981" radius={[2, 2, 0, 0]} maxBarSize={16} isAnimationActive={false} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export default function OIPanel({ symbol = 'NIFTY' }) {
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);
  const [lastFetch, setLastFetch] = useState(null);

  useEffect(() => {
    let cancelled = false;
    const fetch_ = async () => {
      setLoading(true);
      try {
        const res = await fetch(`${API_BASE}/oi/${symbol}`);
        const json = await res.json();
        if (json.error) throw new Error(json.error);
        if (!cancelled) { setData(json); setError(null); setLastFetch(new Date()); }
      } catch (e) {
        if (!cancelled) setError(e.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    fetch_();
    const id = setInterval(fetch_, 3 * 60_000);  // refresh every 3 min
    return () => { cancelled = true; clearInterval(id); };
  }, [symbol]);

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 p-4 space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-[10px] text-gray-500 uppercase tracking-widest font-semibold">
          Open Interest — {symbol}
        </p>
        {lastFetch && (
          <span className="text-[9px] text-gray-600">
            {lastFetch.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}
          </span>
        )}
      </div>

      {loading && (
        <div className="animate-pulse space-y-3">
          <div className="h-16 bg-gray-800/60 rounded-lg" />
          <div className="h-40 bg-gray-800/40 rounded-lg" />
        </div>
      )}

      {error && !loading && (
        <div className="text-xs text-gray-600 py-4 text-center">
          ⚠ OI data unavailable<br />
          <span className="text-[10px] text-gray-700">{error}</span><br />
          <span className="text-[10px] text-gray-700">Available during market hours only</span>
        </div>
      )}

      {data && !loading && (
        <>
          {/* Summary row */}
          <div className="grid grid-cols-3 gap-2 text-center">
            <div className="bg-red-900/10 border border-red-900/20 rounded-lg p-2">
              <p className="text-[9px] text-gray-500 uppercase">Total CE OI</p>
              <p className="text-sm font-bold text-red-400 font-mono">{fmt(data.total_ce_oi)}</p>
            </div>
            <div className="bg-gray-800/40 rounded-lg p-2 flex flex-col items-center justify-center">
              <PCRGauge pcr={data.pcr} />
            </div>
            <div className="bg-green-900/10 border border-green-900/20 rounded-lg p-2">
              <p className="text-[9px] text-gray-500 uppercase">Total PE OI</p>
              <p className="text-sm font-bold text-green-400 font-mono">{fmt(data.total_pe_oi)}</p>
            </div>
          </div>

          {/* Key levels */}
          <div className="grid grid-cols-2 gap-2">
            <div className="bg-gray-800/40 rounded-lg px-3 py-2">
              <p className="text-[9px] text-gray-500 uppercase">Underlying</p>
              <p className="text-sm font-bold text-white font-mono">
                ₹{data.underlying?.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
              </p>
            </div>
            <div className="bg-yellow-900/10 border border-yellow-900/20 rounded-lg px-3 py-2">
              <p className="text-[9px] text-gray-500 uppercase">Max Pain</p>
              <p className="text-sm font-bold text-yellow-400 font-mono">
                ₹{data.max_pain?.toLocaleString('en-IN')}
              </p>
            </div>
          </div>

          {/* OI by strike */}
          {data.strikes?.length > 0 && (
            <div>
              <p className="text-[9px] text-gray-600 uppercase mb-2">OI by Strike (K lots) — CE 🔴 PE 🟢</p>
              <OIBarChart strikes={data.strikes} />
            </div>
          )}

          {/* Strike table */}
          {data.strikes?.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-[10px]">
                <thead>
                  <tr className="text-gray-600 border-b border-gray-800">
                    <th className="text-left py-1">CE OI</th>
                    <th className="text-center py-1 text-white font-bold">Strike</th>
                    <th className="text-right py-1">PE OI</th>
                  </tr>
                </thead>
                <tbody>
                  {data.strikes.map((s, i) => {
                    const atm = Math.abs(s.strike - data.underlying) < 100;
                    return (
                      <tr key={i} className={`border-b border-gray-800/40 ${atm ? 'bg-yellow-900/10' : ''}`}>
                        <td className="py-1 text-red-400 font-mono">{fmt(s.ce_oi)}</td>
                        <td className={`py-1 text-center font-bold font-mono ${atm ? 'text-yellow-400' : 'text-gray-300'}`}>
                          {s.strike?.toLocaleString('en-IN')}
                          {atm && <span className="text-[8px] text-yellow-600 ml-1">ATM</span>}
                        </td>
                        <td className="py-1 text-right text-green-400 font-mono">{fmt(s.pe_oi)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}
