import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer, ReferenceLine,
} from 'recharts';

const SYMBOL_FULL = {
  NIFTY: 'NIFTY 50', BANKNIFTY: 'BANK NIFTY', RELIANCE: 'Reliance Industries',
  HDFCBANK: 'HDFC Bank', ICICIBANK: 'ICICI Bank', INFY: 'Infosys', TCS: 'TCS',
};

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-xs shadow-xl">
      <p className="text-gray-400 mb-1 font-mono">{label}</p>
      {payload.map((p, i) => (
        <p key={i} style={{ color: p.color }} className="font-mono">
          {p.name}: {p.value?.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
        </p>
      ))}
    </div>
  );
}

export default function PriceChart({ symbol, priceHistory, symbolSnapshot }) {
  const data = (priceHistory || {})[symbol] || [];
  const snap = (symbolSnapshot || {})[symbol] || {};

  const formatY = (v) => v?.toLocaleString('en-IN', { maximumFractionDigits: 0 });

  // Dynamic Y domain with 0.5% padding
  const prices = data.map(d => d.price).filter(Boolean);
  const minP = prices.length ? Math.min(...prices) : 0;
  const maxP = prices.length ? Math.max(...prices) : 1;
  const pad  = (maxP - minP) * 0.3 || maxP * 0.01;

  const up = snap.change_pct >= 0;

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 shadow-lg">
      {/* Header */}
      <div className="px-5 py-3.5 border-b border-gray-800 flex items-center justify-between flex-wrap gap-2">
        <div>
          <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-widest">
            {SYMBOL_FULL[symbol] || symbol} · Price Chart
          </p>
          {snap.price && (
            <p className="text-xl font-bold font-mono text-white mt-0.5">
              ₹{snap.price?.toLocaleString('en-IN')}
              <span className={`text-sm ml-2 ${up ? 'text-green-400' : 'text-red-400'}`}>
                {up ? '+' : ''}{snap.change_pct?.toFixed(2)}%
              </span>
            </p>
          )}
        </div>

        {/* Technical badges */}
        <div className="flex items-center gap-2 flex-wrap">
          {snap.ema9 && (
            <div className="text-[10px] px-2 py-1 rounded bg-blue-900/30 border border-blue-700/30">
              <span className="text-gray-500">EMA9 </span>
              <span className="text-blue-400 font-mono">{snap.ema9?.toLocaleString('en-IN')}</span>
            </div>
          )}
          {snap.ema21 && (
            <div className="text-[10px] px-2 py-1 rounded bg-orange-900/30 border border-orange-700/30">
              <span className="text-gray-500">EMA21 </span>
              <span className="text-orange-400 font-mono">{snap.ema21?.toLocaleString('en-IN')}</span>
            </div>
          )}
          {snap.vwap && (
            <div className="text-[10px] px-2 py-1 rounded bg-purple-900/30 border border-purple-700/30">
              <span className="text-gray-500">VWAP </span>
              <span className="text-purple-400 font-mono">{snap.vwap?.toLocaleString('en-IN')}</span>
            </div>
          )}
          {snap.trend_strength && (
            <div className="text-[10px] px-2 py-1 rounded bg-gray-800 border border-gray-700">
              <span className="text-gray-500">Trend </span>
              <span className={`font-semibold ${
                snap.trend_strength === 'STRONG_BULL' ? 'text-green-400' :
                snap.trend_strength === 'STRONG_BEAR' ? 'text-red-400' :
                snap.trend_strength === 'MODERATE'    ? 'text-yellow-400' : 'text-gray-500'
              }`}>{snap.trend_strength?.replace('_', ' ')}</span>
            </div>
          )}
        </div>
      </div>

      {/* Chart */}
      <div className="p-4">
        {data.length < 2 ? (
          <div className="h-52 flex items-center justify-center text-gray-600 text-sm">
            Collecting data… ({data.length} candle{data.length !== 1 ? 's' : ''})
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={data} margin={{ top: 4, right: 8, bottom: 4, left: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
              <XAxis
                dataKey="t"
                tick={{ fill: '#6b7280', fontSize: 10 }}
                axisLine={false}
                tickLine={false}
                interval="preserveStartEnd"
              />
              <YAxis
                domain={[minP - pad, maxP + pad]}
                tickFormatter={formatY}
                tick={{ fill: '#6b7280', fontSize: 10 }}
                axisLine={false}
                tickLine={false}
                width={60}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend
                wrapperStyle={{ fontSize: '10px', color: '#9ca3af' }}
                iconType="plainline"
                iconSize={12}
              />

              {/* VWAP reference line */}
              {snap.vwap && (
                <ReferenceLine y={snap.vwap} stroke="#9333ea" strokeDasharray="4 4" strokeOpacity={0.5} />
              )}

              <Line type="monotone" dataKey="price" name="Price"
                stroke="#ffffff" strokeWidth={2} dot={false} isAnimationActive={false} />
              <Line type="monotone" dataKey="ema9"  name="EMA 9"
                stroke="#3b82f6" strokeWidth={1.5} dot={false} isAnimationActive={false} strokeDasharray="4 2" />
              <Line type="monotone" dataKey="ema21" name="EMA 21"
                stroke="#f97316" strokeWidth={1.5} dot={false} isAnimationActive={false} strokeDasharray="4 2" />
              <Line type="monotone" dataKey="vwap"  name="VWAP"
                stroke="#9333ea" strokeWidth={1} dot={false} isAnimationActive={false} strokeDasharray="2 4" />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
