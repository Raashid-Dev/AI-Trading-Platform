const SignalPill = ({ sig }) => {
  const isCall = sig === 'BUY_CALL';
  return (
    <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold border ${
      isCall
        ? 'text-green-400 bg-green-900/30 border-green-700/30'
        : 'text-red-400 bg-red-900/30 border-red-700/30'
    }`}>
      {isCall ? '▲ CALL' : '▼ PUT'}
    </span>
  );
};

const SizeBar = ({ allocated, remaining }) => {
  const a = allocated || 1;
  const r = remaining || a;
  const pct = Math.min(100, (r / a) * 100);
  return (
    <div className="flex items-center gap-2">
      <div className="w-14 bg-gray-800 rounded-full h-1 overflow-hidden">
        <div className="h-full bg-blue-500 rounded-full" style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-mono text-gray-300">{r.toFixed(2)}x</span>
    </div>
  );
};

export default function OpenTrades({ trades }) {
  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 shadow-lg flex flex-col">

      <div className="px-5 py-3.5 border-b border-gray-800 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          {trades.length > 0 && (
            <span className="w-1.5 h-1.5 rounded-full bg-yellow-400 animate-pulse" />
          )}
          <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-widest">
            Open Trades
          </p>
        </div>
        <span className={`text-xs font-mono font-bold ${
          trades.length > 0 ? 'text-yellow-400' : 'text-gray-600'
        }`}>
          {trades.length} active
        </span>
      </div>

      {trades.length === 0 ? (
        <div className="flex-1 py-10 text-center">
          <p className="text-gray-600 text-sm">No open positions</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left border-b border-gray-800">
                {['Symbol', 'Signal', 'Entry', 'SL / Target', 'Size', 'Candles'].map(h => (
                  <th key={h} className="px-4 py-3 text-[10px] font-semibold text-gray-500 uppercase tracking-wider">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {trades.map((trade, i) => (
                <tr
                  key={i}
                  className="border-b border-gray-800/40 hover:bg-gray-800/25 transition-colors"
                >
                  <td className="px-4 py-3 font-bold text-white">{trade.symbol || '–'}</td>
                  <td className="px-4 py-3"><SignalPill sig={trade.signal} /></td>
                  <td className="px-4 py-3 font-mono text-gray-200 text-xs">
                    {(trade.entry || 0).toFixed(2)}
                  </td>
                  <td className="px-4 py-3 text-xs">
                    <span className="text-red-400 font-mono">{(trade.stop_loss || 0).toFixed(0)}</span>
                    <span className="text-gray-600 mx-1">/</span>
                    <span className="text-green-400 font-mono">{(trade.target || 0).toFixed(0)}</span>
                  </td>
                  <td className="px-4 py-3">
                    <SizeBar allocated={trade.allocated_size} remaining={trade.remaining_size} />
                  </td>
                  <td className="px-4 py-3 text-gray-400 font-mono text-xs">
                    {trade.candles_held ?? '–'}
                    {trade.partial_exit && (
                      <span className="ml-1.5 text-[9px] text-orange-400 bg-orange-900/30 px-1 py-0.5 rounded">½</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
