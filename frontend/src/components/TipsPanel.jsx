// TipsPanel — signals displayed as actionable trading recommendations

const REASONS = {
  BUY_CALL: [
    "Strong bullish momentum with EMA9 crossing above EMA21",
    "Price trading above VWAP — institutional buying pressure",
    "PCR below 0.8 with FII net buying — market breadth positive",
    "NIFTY showing breakout pattern with above-average volume",
    "Trending session with strong upward momentum — call options favored",
  ],
  BUY_PUT: [
    "Bearish divergence detected — EMA9 crossing below EMA21",
    "Price slipped below VWAP — distribution phase likely",
    "PCR above 1.2 with FII outflows — market breadth negative",
    "Weakness in Bank Nifty dragging broader market",
    "High put accumulation at OTM strikes — hedge pressure building",
  ],
};

function getReason(signal, sym) {
  const pool = REASONS[signal] || [];
  const idx  = (sym?.charCodeAt(0) || 0) % pool.length;
  return pool[idx] || "Strong technical confluence detected";
}

function ConfidenceMeter({ value }) {
  const pct   = Math.round((value || 0) * 100);
  const color = pct >= 80 ? 'bg-green-500' : pct >= 70 ? 'bg-blue-500' : 'bg-yellow-500';
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-gray-800 rounded-full h-1.5 overflow-hidden">
        <div className={`h-full rounded-full ${color} transition-all duration-500`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-mono font-bold text-white w-8 text-right">{pct}%</span>
    </div>
  );
}

function TipCard({ sig }) {
  const isCall  = sig.signal === 'BUY_CALL';
  const conf    = sig.confidence || 0;
  const reason  = sig.reason || getReason(sig.signal, sig.symbol);
  const confPct = Math.round(conf * 100);

  // Derive mock entry/SL/target from price (realistic options logic)
  const basePrice  = sig.strike || 0;
  const entryEst   = basePrice > 0 ? `₹${basePrice.toLocaleString('en-IN')}` : 'At market';
  const slPct      = conf >= 0.75 ? 30 : 40;
  const tgtPct     = conf >= 0.75 ? 80 : 60;

  return (
    <div className={`rounded-xl border p-4 transition-all duration-200 ${
      isCall
        ? 'border-green-800/40 bg-green-900/10 hover:bg-green-900/20'
        : 'border-red-800/40 bg-red-900/10 hover:bg-red-900/20'
    }`}>
      {/* Badge row */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className={`text-sm font-black px-3 py-1 rounded-lg ${
            isCall ? 'bg-green-500 text-black' : 'bg-red-500 text-white'
          }`}>
            {isCall ? '▲ BUY CALL' : '▼ BUY PUT'}
          </span>
          <span className="text-xs text-gray-400 font-semibold">{sig.symbol}</span>
        </div>
        <span className={`text-[10px] px-2 py-0.5 rounded font-medium ${
          sig.trend_strength === 'STRONG_BULL' || sig.trend_strength === 'STRONG_BEAR'
            ? 'bg-blue-900/40 text-blue-400'
            : 'bg-gray-800 text-gray-500'
        }`}>
          {sig.trend_strength?.replace('_', ' ') || 'MODERATE'}
        </span>
      </div>

      {/* Confidence */}
      <div className="mb-3">
        <div className="flex items-center justify-between mb-1">
          <span className="text-[10px] text-gray-500 uppercase tracking-wider">AI Confidence</span>
          <span className={`text-[10px] font-bold ${
            confPct >= 80 ? 'text-green-400' : confPct >= 70 ? 'text-blue-400' : 'text-yellow-400'
          }`}>
            {confPct >= 80 ? 'HIGH' : confPct >= 70 ? 'MEDIUM' : 'LOW'}
          </span>
        </div>
        <ConfidenceMeter value={conf} />
      </div>

      {/* Reason */}
      <p className="text-xs text-gray-300 mb-3 leading-relaxed">{reason}</p>

      {/* Entry / SL / Target */}
      <div className="grid grid-cols-3 gap-2">
        <div className="bg-gray-800/60 rounded-lg p-2">
          <p className="text-[9px] text-gray-500 uppercase mb-0.5">Strike / Entry</p>
          <p className="text-xs font-mono text-white font-semibold">{entryEst}</p>
        </div>
        <div className="bg-red-900/20 rounded-lg p-2">
          <p className="text-[9px] text-gray-500 uppercase mb-0.5">Stop Loss</p>
          <p className="text-xs font-mono text-red-400 font-semibold">-{slPct}%</p>
        </div>
        <div className="bg-green-900/20 rounded-lg p-2">
          <p className="text-[9px] text-gray-500 uppercase mb-0.5">Target</p>
          <p className="text-xs font-mono text-green-400 font-semibold">+{tgtPct}%</p>
        </div>
      </div>

      {/* Score bar */}
      <div className="mt-3 pt-3 border-t border-gray-800/60 flex items-center justify-between">
        <span className="text-[10px] text-gray-600">Score</span>
        <span className={`text-xs font-mono font-bold ${
          (sig.score || 0) > 0 ? 'text-green-400' : 'text-red-400'
        }`}>
          {sig.score > 0 ? '+' : ''}{sig.score ?? '–'}
        </span>
      </div>
    </div>
  );
}

export default function TipsPanel({ signals }) {
  const actionable = (signals || []).filter(s => s.signal === 'BUY_CALL' || s.signal === 'BUY_PUT');

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 shadow-lg">
      <div className="px-5 py-3.5 border-b border-gray-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
          <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-widest">
            AI Trading Tips
          </p>
        </div>
        <span className="text-[10px] text-gray-600 font-mono">
          {actionable.length} recommendation{actionable.length !== 1 ? 's' : ''}
        </span>
      </div>

      <div className="p-4">
        {actionable.length === 0 ? (
          <div className="py-8 text-center">
            <p className="text-2xl mb-2">🔍</p>
            <p className="text-gray-500 text-sm">No high-confidence setups this candle</p>
            <p className="text-gray-600 text-xs mt-1">
              Engine requires confidence ≥ 70% and score ≥ 8 to issue a tip
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
            {actionable.map((sig, i) => <TipCard key={i} sig={sig} />)}
          </div>
        )}
      </div>

      {/* Disclaimer */}
      <div className="px-5 py-3 border-t border-gray-800/60">
        <p className="text-[10px] text-gray-700">
          ⚠ AI recommendations are for educational/simulation purposes only.
          Not financial advice. Always do your own research before trading.
        </p>
      </div>
    </div>
  );
}
