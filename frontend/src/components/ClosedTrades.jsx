const REASON_STYLES = {
  TARGET:      'bg-green-900/40 text-green-400 border-green-700/30',
  SL:          'bg-red-900/40 text-red-400 border-red-700/30',
  TIME:        'bg-blue-900/40 text-blue-400 border-blue-700/30',
  NO_MOMENTUM: 'bg-orange-900/40 text-orange-400 border-orange-700/30',
  REVERSAL:    'bg-purple-900/40 text-purple-400 border-purple-700/30',
  TREND_WEAK:  'bg-yellow-900/40 text-yellow-400 border-yellow-700/30',
};

const ReasonBadge = ({ reason }) => {
  const cls = REASON_STYLES[reason] || 'bg-gray-800 text-gray-400 border-gray-700/30';
  return (
    <span className={`text-[10px] px-1.5 py-0.5 rounded border font-semibold whitespace-nowrap ${cls}`}>
      {reason || '–'}
    </span>
  );
};

const PnlCell = ({ pnl }) => {
  const val  = pnl || 0;
  const pos  = val > 0;
  const zero = val === 0;
  return (
    <span className={`font-mono font-bold text-xs ${
      zero ? 'text-gray-500' : pos ? 'text-green-400' : 'text-red-400'
    }`}>
      {pos ? '+' : ''}{val.toFixed(3)}%
    </span>
  );
};

export default function ClosedTrades({ trades }) {
  // show most recent first
  const sorted = [...trades].reverse();

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 shadow-lg flex flex-col">

      <div className="px-5 py-3.5 border-b border-gray-800 flex items-center justify-between shrink-0">
        <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-widest">
          Closed Trades
        </p>
        <span className="text-xs font-mono text-gray-600">{trades.length} total</span>
      </div>

      {trades.length === 0 ? (
        <div className="flex-1 py-10 text-center">
          <p className="text-gray-600 text-sm">No closed trades yet</p>
        </div>
      ) : (
        <div className="overflow-y-auto max-h-72">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-gray-900 z-10">
              <tr className="border-b border-gray-800">
                {['Symbol', 'Entry', 'Exit', 'PnL', 'Reason'].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-[10px] font-semibold text-gray-500 uppercase tracking-wider">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sorted.map((trade, i) => (
                <tr
                  key={i}
                  className={`border-b border-gray-800/40 hover:bg-gray-800/25 transition-colors ${
                    i === 0 ? 'bg-gray-800/10' : ''
                  }`}
                >
                  <td className="px-4 py-2.5">
                    <div className="font-bold text-white text-xs">{trade.symbol || '–'}</div>
                    <div className="text-[10px] text-gray-500 mt-0.5">{
                      trade.signal === 'BUY_CALL' ? '▲ CALL' : '▼ PUT'
                    }</div>
                  </td>
                  <td className="px-4 py-2.5 font-mono text-gray-400 text-xs">
                    {(trade.entry || 0).toFixed(2)}
                  </td>
                  <td className="px-4 py-2.5 font-mono text-gray-300 text-xs">
                    {trade.exit ? trade.exit.toFixed(2) : '–'}
                  </td>
                  <td className="px-4 py-2.5"><PnlCell pnl={trade.pnl} /></td>
                  <td className="px-4 py-2.5"><ReasonBadge reason={trade.exit_reason} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
