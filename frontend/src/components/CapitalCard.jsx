const fmtINR = (n) =>
  new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(n || 0);

export default function CapitalCard({ capital }) {
  const bal      = capital?.capital      ?? 0;
  const peak     = capital?.max_capital  ?? 0;
  const drawdown = capital?.drawdown_pct ?? 0;

  const isDown    = drawdown < 0;
  const pnlChange = peak > 0 ? ((bal - peak) / peak) * 100 : 0;

  return (
    <div className="bg-gray-900 rounded-xl p-5 border border-gray-800 shadow-lg">

      <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-widest mb-4">
        Capital
      </p>

      {/* Main balance */}
      <div className="mb-4">
        <p className="text-3xl font-bold text-white font-mono tracking-tight">
          {fmtINR(bal)}
        </p>
        <p className="text-xs text-gray-500 mt-1">Current Balance</p>
      </div>

      {/* Peak + Drawdown row */}
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-gray-800/50 rounded-lg p-3">
          <p className="text-sm font-semibold text-gray-200 font-mono">{fmtINR(peak)}</p>
          <p className="text-xs text-gray-500 mt-0.5">Peak</p>
        </div>

        <div className={`rounded-lg p-3 ${isDown ? 'bg-red-900/20' : 'bg-green-900/20'}`}>
          <p className={`text-sm font-bold font-mono ${isDown ? 'text-red-400' : 'text-green-400'}`}>
            {drawdown >= 0 ? '+' : ''}{drawdown.toFixed(2)}%
          </p>
          <p className="text-xs text-gray-500 mt-0.5">Drawdown</p>
        </div>
      </div>

      {/* PnL from peak bar */}
      {peak > 0 && (
        <div className="mt-3">
          <div className="w-full bg-gray-800 rounded-full h-1">
            <div
              className={`h-1 rounded-full transition-all duration-500 ${isDown ? 'bg-red-500' : 'bg-green-500'}`}
              style={{ width: `${Math.min(100, Math.max(2, (bal / peak) * 100))}%` }}
            />
          </div>
          <p className="text-[10px] text-gray-600 mt-1 text-right">
            {((bal / Math.max(1, peak)) * 100).toFixed(1)}% of peak
          </p>
        </div>
      )}

    </div>
  );
}
