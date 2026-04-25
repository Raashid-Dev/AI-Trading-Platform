// TechnicalPanel — per-symbol technical analysis summary

const SYMBOL_FULL = {
  NIFTY: 'NIFTY 50', BANKNIFTY: 'BANK NIFTY',
  RELIANCE: 'Reliance', HDFCBANK: 'HDFC Bank',
  ICICIBANK: 'ICICI Bank', INFY: 'Infosys', TCS: 'TCS',
};

// Derive RSI-like value from price_change (pseudo — real RSI needs full candle series)
function mockRSI(changePct) {
  const base = 50 + changePct * 8;
  return Math.min(85, Math.max(15, Math.round(base)));
}

// Momentum from score
function momentumLabel(score) {
  if (score >= 10) return { label: 'Strong Bullish', color: 'text-green-400', bar: 90 };
  if (score >= 6)  return { label: 'Bullish',        color: 'text-green-300', bar: 70 };
  if (score >= 2)  return { label: 'Mild Bullish',   color: 'text-teal-400',  bar: 55 };
  if (score <= -10)return { label: 'Strong Bearish', color: 'text-red-400',   bar: 10 };
  if (score <= -6) return { label: 'Bearish',        color: 'text-red-300',   bar: 30 };
  if (score <= -2) return { label: 'Mild Bearish',   color: 'text-orange-400',bar: 45 };
  return { label: 'Neutral', color: 'text-gray-400', bar: 50 };
}

function GaugeBar({ value, max = 100, color }) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));
  return (
    <div className="w-full bg-gray-800 rounded-full h-1.5 overflow-hidden">
      <div className={`h-full rounded-full ${color} transition-all duration-500`} style={{ width: `${pct}%` }} />
    </div>
  );
}

function RSIBadge({ rsi }) {
  const color = rsi >= 70 ? 'text-red-400'    :
                rsi <= 30 ? 'text-green-400'   :
                rsi >= 60 ? 'text-orange-400'  : 'text-gray-400';
  const label = rsi >= 70 ? 'Overbought' : rsi <= 30 ? 'Oversold' : 'Neutral';
  return (
    <div>
      <div className="flex justify-between mb-1">
        <span className="text-[10px] text-gray-500 uppercase">RSI (14)</span>
        <span className={`text-xs font-mono font-bold ${color}`}>{rsi} · {label}</span>
      </div>
      <GaugeBar value={rsi} color={
        rsi >= 70 ? 'bg-red-500' : rsi <= 30 ? 'bg-green-500' : 'bg-gray-600'
      } />
    </div>
  );
}

function SymbolTechRow({ sym, snap }) {
  if (!snap) return null;
  const rsi      = mockRSI(snap.change_pct || 0);
  const mom      = momentumLabel(snap.score || 0);
  const aboveVwap = snap.price > snap.vwap;
  const emaAlign  = snap.ema9 > snap.ema21;

  return (
    <div className="p-4 border-b border-gray-800/50 last:border-0">
      <div className="flex items-center justify-between mb-3">
        <div>
          <p className="text-sm font-bold text-white">{sym}</p>
          <p className="text-[10px] text-gray-600">{SYMBOL_FULL[sym]}</p>
        </div>
        <div className="text-right">
          <p className="text-sm font-mono font-bold text-white">
            ₹{snap.price?.toLocaleString('en-IN')}
          </p>
          <p className={`text-[10px] font-mono ${snap.change_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
            {snap.change_pct >= 0 ? '+' : ''}{snap.change_pct?.toFixed(2)}%
          </p>
        </div>
      </div>

      <div className="space-y-2">
        <RSIBadge rsi={rsi} />

        <div className="flex justify-between mb-1">
          <span className="text-[10px] text-gray-500 uppercase">Momentum</span>
          <span className={`text-xs font-semibold ${mom.color}`}>{mom.label}</span>
        </div>
        <GaugeBar value={mom.bar} color={mom.bar > 50 ? 'bg-green-500' : 'bg-red-500'} />

        {/* EMA / VWAP status */}
        <div className="flex gap-2 mt-2">
          <span className={`text-[9px] px-2 py-0.5 rounded border ${
            aboveVwap
              ? 'border-green-700/40 bg-green-900/20 text-green-400'
              : 'border-red-700/40 bg-red-900/20 text-red-400'
          }`}>
            {aboveVwap ? '▲' : '▼'} VWAP
          </span>
          <span className={`text-[9px] px-2 py-0.5 rounded border ${
            emaAlign
              ? 'border-blue-700/40 bg-blue-900/20 text-blue-400'
              : 'border-orange-700/40 bg-orange-900/20 text-orange-400'
          }`}>
            EMA {emaAlign ? '9>21 ▲' : '9<21 ▼'}
          </span>
          <span className={`text-[9px] px-2 py-0.5 rounded border ${
            snap.signal === 'BUY_CALL' ? 'border-green-700/40 bg-green-900/20 text-green-400' :
            snap.signal === 'BUY_PUT'  ? 'border-red-700/40 bg-red-900/20 text-red-400' :
                                         'border-gray-700/40 bg-gray-800 text-gray-500'
          }`}>
            {snap.signal === 'BUY_CALL' ? '▲ CALL' :
             snap.signal === 'BUY_PUT'  ? '▼ PUT'  : '○ WAIT'}
          </span>
        </div>
      </div>
    </div>
  );
}

export default function TechnicalPanel({ symbolSnapshot }) {
  const symbols = Object.keys(symbolSnapshot || {}).filter(s => s !== '__meta__');

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 shadow-lg">
      <div className="px-5 py-3.5 border-b border-gray-800">
        <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-widest">
          Technical Analysis
        </p>
      </div>

      {symbols.length === 0 ? (
        <div className="p-8 text-center text-gray-600 text-sm">
          Waiting for market data…
        </div>
      ) : (
        <div className="divide-y divide-gray-800/50 max-h-[480px] overflow-y-auto">
          {symbols.map(sym => (
            <SymbolTechRow key={sym} sym={sym} snap={symbolSnapshot[sym]} />
          ))}
        </div>
      )}
    </div>
  );
}
