import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ReferenceLine, ResponsiveContainer
} from 'recharts';

/**
 * Reconstruct equity curve from closed trades.
 * Applies compound formula: capital *= (1 + pnl/100)
 */
function buildEquityCurve(closedTrades, startCapital) {
  const base = startCapital || 100_000;
  let capital = base;
  const data = [{ index: 0, capital: Math.round(capital), label: 'Start' }];

  for (let i = 0; i < closedTrades.length; i++) {
    const trade = closedTrades[i];
    const pnl   = trade.pnl || 0;
    capital     = capital * (1 + pnl / 100);
    data.push({
      index:   i + 1,
      capital: Math.round(capital),
      label:   trade.symbol || `T${i + 1}`,
      pnl:     pnl,
      reason:  trade.exit_reason || '',
    });
  }
  return { data, base };
}

const fmtK = (v) => {
  if (v >= 100_000) return `₹${(v / 1000).toFixed(0)}k`;
  return `₹${(v / 1000).toFixed(1)}k`;
};

const CustomTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  const isStart = d.index === 0;
  return (
    <div className="bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-xs shadow-xl">
      {isStart ? (
        <p className="text-gray-400">Starting capital</p>
      ) : (
        <>
          <p className="text-gray-400 mb-1">Trade #{d.index} · {d.label}</p>
          <p className={`font-bold ${(d.pnl || 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
            PnL {(d.pnl || 0) >= 0 ? '+' : ''}{(d.pnl || 0).toFixed(3)}%
          </p>
          {d.reason && <p className="text-gray-500 mt-0.5">{d.reason}</p>}
        </>
      )}
      <p className="text-white font-mono font-bold mt-1">
        ₹{d.capital.toLocaleString('en-IN')}
      </p>
    </div>
  );
};

export default function EquityChart({ closedTrades, initialCapital }) {
  if (!closedTrades || closedTrades.length === 0) {
    return (
      <div className="bg-gray-900 rounded-xl border border-gray-800 shadow-lg px-5 py-12 text-center">
        <p className="text-4xl mb-3">📈</p>
        <p className="text-gray-500 text-sm font-medium">Equity Curve</p>
        <p className="text-gray-700 text-xs mt-1">Will appear after the first trade closes</p>
      </div>
    );
  }

  const { data, base } = buildEquityCurve(closedTrades, initialCapital);
  const final    = data[data.length - 1]?.capital ?? base;
  const minVal   = Math.min(...data.map(d => d.capital));
  const maxVal   = Math.max(...data.map(d => d.capital));
  const isUp     = final >= base;
  const lineColor = isUp ? '#4ade80' : '#f87171';
  const changePct = ((final - base) / base * 100).toFixed(2);

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 shadow-lg">

      {/* Header */}
      <div className="px-5 py-3.5 border-b border-gray-800 flex items-center justify-between">
        <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-widest">
          Equity Curve
        </p>
        <div className="flex items-center gap-3">
          <span className="text-xs text-gray-500 font-mono">
            ₹{base.toLocaleString('en-IN')} → ₹{final.toLocaleString('en-IN')}
          </span>
          <span className={`text-xs font-bold font-mono px-2 py-0.5 rounded ${
            isUp
              ? 'text-green-400 bg-green-900/30'
              : 'text-red-400 bg-red-900/30'
          }`}>
            {isUp ? '+' : ''}{changePct}%
          </span>
        </div>
      </div>

      {/* Chart */}
      <div className="p-4 pt-5">
        <ResponsiveContainer width="100%" height={240}>
          <LineChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 20 }}>
            <defs>
              <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor={lineColor} stopOpacity={0.15} />
                <stop offset="95%" stopColor={lineColor} stopOpacity={0}    />
              </linearGradient>
            </defs>

            <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />

            <XAxis
              dataKey="index"
              stroke="#374151"
              tick={{ fontSize: 10, fill: '#6b7280' }}
              label={{ value: 'Trade #', position: 'insideBottom', offset: -10, fill: '#4b5563', fontSize: 10 }}
            />

            <YAxis
              stroke="#374151"
              tick={{ fontSize: 10, fill: '#6b7280' }}
              tickFormatter={fmtK}
              domain={[minVal * 0.995, maxVal * 1.005]}
              width={52}
            />

            <Tooltip content={<CustomTooltip />} />

            {/* Baseline reference */}
            <ReferenceLine
              y={base}
              stroke="#374151"
              strokeDasharray="4 4"
              label={{ value: 'Start', fill: '#4b5563', fontSize: 9, position: 'insideTopRight' }}
            />

            <Line
              type="monotone"
              dataKey="capital"
              stroke={lineColor}
              strokeWidth={2}
              dot={(props) => {
                const { cx, cy, payload } = props;
                if (payload.index === 0) return null;
                const isWin = (payload.pnl || 0) > 0;
                return (
                  <circle
                    key={payload.index}
                    cx={cx} cy={cy} r={3}
                    fill={isWin ? '#4ade80' : '#f87171'}
                    stroke="none"
                    opacity={0.7}
                  />
                );
              }}
              activeDot={{ r: 5, fill: lineColor, stroke: '#111827', strokeWidth: 2 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Footer: win/loss distribution mini-bar */}
      {closedTrades.length > 0 && (() => {
        const wins   = closedTrades.filter(t => (t.pnl || 0) > 0).length;
        const total  = closedTrades.length;
        const winPct = (wins / total) * 100;
        return (
          <div className="px-5 pb-4 flex items-center gap-3">
            <div className="flex-1 bg-gray-800 rounded-full h-1.5 overflow-hidden">
              <div className="h-full bg-green-500 rounded-full transition-all" style={{ width: `${winPct}%` }} />
            </div>
            <span className="text-[10px] text-gray-500 font-mono shrink-0">
              {wins}W / {total - wins}L  ·  {winPct.toFixed(0)}% WR
            </span>
          </div>
        );
      })()}

    </div>
  );
}
