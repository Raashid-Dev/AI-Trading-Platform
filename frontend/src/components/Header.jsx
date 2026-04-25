const TRANSPORT_LABELS = {
  websocket:  { label: 'WS · LIVE',    dot: 'bg-green-400 animate-pulse', badge: 'bg-green-900/20 border-green-700/40 text-green-400' },
  polling:    { label: 'POLLING',       dot: 'bg-yellow-400 animate-pulse', badge: 'bg-yellow-900/20 border-yellow-700/40 text-yellow-400' },
  connecting: { label: 'CONNECTING…',  dot: 'bg-blue-400 animate-pulse',   badge: 'bg-blue-900/20 border-blue-700/40 text-blue-400' },
};

const DISCONNECTED = { label: 'DISCONNECTED', dot: 'bg-red-400', badge: 'bg-red-900/20 border-red-700/40 text-red-400' };

export default function Header({ connected, lastUpdate, transport = 'connecting' }) {
  const timeStr = lastUpdate
    ? lastUpdate.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    : null;

  const style = connected
    ? (TRANSPORT_LABELS[transport] ?? TRANSPORT_LABELS.connecting)
    : DISCONNECTED;

  return (
    <header className="py-4 flex items-center justify-between border-b border-gray-800/60 mb-4">

      {/* Logo + title */}
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-500 to-blue-700 flex items-center justify-center text-white font-black text-sm shadow-lg shadow-blue-900/30">
          AI
        </div>
        <div>
          <h1 className="text-base font-bold text-white leading-tight tracking-tight">
            AI Trading Dashboard
          </h1>
          <p className="text-xs text-gray-500">NSE · Options · Multi-Symbol · Rule-Based</p>
        </div>
      </div>

      {/* Status */}
      <div className="flex items-center gap-4">
        {timeStr && (
          <span className="text-xs text-gray-600 hidden sm:block">
            Last update: <span className="text-gray-500 font-mono">{timeStr}</span>
          </span>
        )}

        <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-bold border transition-all ${style.badge}`}>
          <span className={`w-1.5 h-1.5 rounded-full ${style.dot}`} />
          {style.label}
        </div>
      </div>

    </header>
  );
}
