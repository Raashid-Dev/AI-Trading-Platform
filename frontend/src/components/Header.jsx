const TRANSPORT_LABELS = {
  websocket:  { label: 'WS · LIVE',   dot: 'bg-green-400 animate-pulse', badge: 'bg-green-900/20 border-green-700/40 text-green-400' },
  polling:    { label: 'POLLING',      dot: 'bg-yellow-400 animate-pulse', badge: 'bg-yellow-900/20 border-yellow-700/40 text-yellow-400' },
  connecting: { label: 'CONNECTING…', dot: 'bg-blue-400 animate-pulse',   badge: 'bg-blue-900/20 border-blue-700/40 text-blue-400' },
};
const DISCONNECTED = { label: 'DISCONNECTED', dot: 'bg-red-400', badge: 'bg-red-900/20 border-red-700/40 text-red-400' };

const NAV_PAGES = [
  { id: 'market',    label: 'Market',    icon: '📊' },
  { id: 'stocks',    label: 'Stocks',    icon: '📈' },
  { id: 'signals',   label: 'Signals',   icon: '🎯' },
  { id: 'portfolio', label: 'Portfolio', icon: '💼' },
  { id: 'news',      label: 'News',      icon: '📰' },
];

export default function Header({ connected, lastUpdate, transport = 'connecting', page, onPageChange }) {
  const timeStr = lastUpdate
    ? lastUpdate.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    : null;

  const style = connected
    ? (TRANSPORT_LABELS[transport] ?? TRANSPORT_LABELS.connecting)
    : DISCONNECTED;

  return (
    <header className="sticky top-0 z-50 bg-gray-950/95 backdrop-blur-sm border-b border-gray-800/60">
      <div className="max-w-[1600px] mx-auto px-4">

        {/* Top row: logo + status */}
        <div className="flex items-center justify-between py-3">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-violet-600 flex items-center justify-center text-white font-black text-xs shadow-lg">
              AI
            </div>
            <div>
              <h1 className="text-sm font-bold text-white leading-tight">AI Trading Dashboard</h1>
              <p className="text-[10px] text-gray-600">NSE · Options · Multi-Symbol · Simulated</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {timeStr && (
              <span className="text-[11px] text-gray-600 hidden sm:block font-mono">
                {timeStr}
              </span>
            )}
            <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold border ${style.badge}`}>
              <span className={`w-1.5 h-1.5 rounded-full ${style.dot}`} />
              {style.label}
            </div>
          </div>
        </div>

        {/* Nav tabs */}
        <div className="flex gap-1 pb-0">
          {NAV_PAGES.map(p => (
            <button
              key={p.id}
              onClick={() => onPageChange(p.id)}
              className={`flex items-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-t-lg transition-all duration-150 border-b-2 ${
                page === p.id
                  ? 'text-blue-400 border-blue-500 bg-blue-900/10'
                  : 'text-gray-500 border-transparent hover:text-gray-300 hover:bg-gray-800/40'
              }`}
            >
              <span>{p.icon}</span>
              <span className="hidden sm:inline">{p.label}</span>
            </button>
          ))}
        </div>

      </div>
    </header>
  );
}
