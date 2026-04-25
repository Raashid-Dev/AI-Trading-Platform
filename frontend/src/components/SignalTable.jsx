const confidenceBar = (conf) => {
  const pct = Math.round((conf || 0) * 100);
  const color = pct >= 75 ? 'bg-green-500' : pct >= 65 ? 'bg-yellow-500' : 'bg-orange-500';
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 bg-gray-800 rounded-full h-1.5 overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className={`font-mono text-xs font-semibold ${
        pct >= 70 ? 'text-green-400' : pct >= 60 ? 'text-yellow-400' : 'text-orange-400'
      }`}>
        {pct}%
      </span>
    </div>
  );
};

const SignalBadge = ({ sig }) => {
  const isCall = sig === 'BUY_CALL';
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-bold ${
      isCall
        ? 'bg-green-900/50 text-green-400 border border-green-700/40'
        : 'bg-red-900/50 text-red-400 border border-red-700/40'
    }`}>
      {isCall ? '▲' : '▼'} {isCall ? 'CALL' : 'PUT'}
    </span>
  );
};

const RegimeBadge = ({ regime }) => {
  const colors = {
    TREND: 'text-blue-400 bg-blue-900/30 border-blue-700/30',
    RANGE: 'text-yellow-400 bg-yellow-900/30 border-yellow-700/30',
    MIXED: 'text-gray-400 bg-gray-800 border-gray-700/30',
  };
  const cls = colors[regime] || colors.MIXED;
  return regime ? (
    <span className={`text-[10px] px-1.5 py-0.5 rounded border font-medium ${cls}`}>
      {regime}
    </span>
  ) : <span className="text-gray-600">–</span>;
};

export default function SignalTable({ signals }) {
  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 shadow-lg">

      {/* Header */}
      <div className="px-5 py-3.5 border-b border-gray-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-blue-400 animate-pulse" />
          <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-widest">
            Live Signals
          </p>
        </div>
        <span className="text-xs font-mono text-gray-600">
          {signals.length} signal{signals.length !== 1 ? 's' : ''}
        </span>
      </div>

      {signals.length === 0 ? (
        <div className="py-10 text-center">
          <p className="text-gray-600 text-sm">No actionable signals this candle</p>
          <p className="text-gray-700 text-xs mt-1">Waiting for next candle…</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left border-b border-gray-800">
                {['Symbol', 'Signal', 'Confidence', 'Direction', 'Trend', 'Score', 'Regime', 'VIX'].map(h => (
                  <th key={h} className="px-4 py-3 text-[10px] font-semibold text-gray-500 uppercase tracking-wider">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {signals.map((sig, i) => (
                <tr
                  key={i}
                  className="border-b border-gray-800/40 hover:bg-gray-800/25 transition-colors duration-100"
                >
                  <td className="px-4 py-3 font-bold text-white">{sig.symbol || '–'}</td>
                  <td className="px-4 py-3"><SignalBadge sig={sig.signal} /></td>
                  <td className="px-4 py-3">{confidenceBar(sig.confidence)}</td>
                  <td className="px-4 py-3 text-gray-300 text-xs">{sig.direction || '–'}</td>
                  <td className="px-4 py-3 text-gray-400 text-xs">{sig.trend_strength || sig.trend || '–'}</td>
                  <td className={`px-4 py-3 font-mono font-semibold text-xs ${
                    (sig.score || 0) > 0 ? 'text-green-400' : (sig.score || 0) < 0 ? 'text-red-400' : 'text-gray-400'
                  }`}>
                    {sig.score != null ? (sig.score > 0 ? `+${sig.score}` : sig.score) : '–'}
                  </td>
                  <td className="px-4 py-3"><RegimeBadge regime={sig.regime} /></td>
                  <td className="px-4 py-3 text-gray-400 text-xs">{sig.vix_tier || '–'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
