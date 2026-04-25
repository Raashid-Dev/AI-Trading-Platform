import { LineChart, Line, ResponsiveContainer } from 'recharts';

const SYMBOL_META = {
  NIFTY:     { label: 'NIFTY 50',    type: 'index' },
  BANKNIFTY: { label: 'BANK NIFTY',  type: 'index' },
  RELIANCE:  { label: 'RELIANCE',    type: 'stock' },
  HDFCBANK:  { label: 'HDFC BANK',   type: 'stock' },
  ICICIBANK: { label: 'ICICI BANK',  type: 'stock' },
  INFY:      { label: 'INFOSYS',     type: 'stock' },
  TCS:       { label: 'TCS',         type: 'stock' },
};

function Sparkline({ data }) {
  if (!data || data.length < 2) {
    return <div className="h-8 flex items-center text-gray-700 text-xs">–</div>;
  }
  const prices = data.map(d => ({ v: d.price }));
  const first  = prices[0].v;
  const last   = prices[prices.length - 1].v;
  const up     = last >= first;
  return (
    <ResponsiveContainer width="100%" height={32}>
      <LineChart data={prices}>
        <Line
          type="monotone"
          dataKey="v"
          stroke={up ? '#4ade80' : '#f87171'}
          strokeWidth={1.5}
          dot={false}
          isAnimationActive={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

function TrendBadge({ strength, direction }) {
  if (!strength || strength === 'WEAK' || direction === 'SIDEWAYS') {
    return <span className="text-[9px] px-1.5 py-0.5 rounded bg-gray-800 text-gray-500 font-medium">RANGE</span>;
  }
  if (direction === 'BULLISH') {
    return <span className="text-[9px] px-1.5 py-0.5 rounded bg-green-900/40 text-green-400 font-medium">▲ BULL</span>;
  }
  return <span className="text-[9px] px-1.5 py-0.5 rounded bg-red-900/40 text-red-400 font-medium">▼ BEAR</span>;
}

function SignalDot({ signal }) {
  if (signal === 'BUY_CALL') return <span className="text-green-400 text-xs font-bold" title="BUY CALL">●</span>;
  if (signal === 'BUY_PUT')  return <span className="text-red-400 text-xs font-bold"   title="BUY PUT">●</span>;
  return <span className="text-gray-700 text-xs">○</span>;
}

export default function MarketOverview({ symbolSnapshot, priceHistory, onSelect, selected }) {
  if (!symbolSnapshot || Object.keys(symbolSnapshot).length === 0) {
    return (
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-5">
        <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-widest mb-3">Market Overview</p>
        <p className="text-sm text-gray-600 text-center py-4">Waiting for market data…</p>
      </div>
    );
  }

  const symbols = Object.keys(SYMBOL_META).filter(s => symbolSnapshot[s]);

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 shadow-lg">
      <div className="px-5 py-3.5 border-b border-gray-800 flex items-center justify-between">
        <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-widest">Market Overview</p>
        <p className="text-[10px] text-gray-600">Click a symbol to view chart</p>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 divide-x divide-gray-800">
        {symbols.map(sym => {
          const snap  = symbolSnapshot[sym] || {};
          const hist  = (priceHistory || {})[sym] || [];
          const up    = snap.change_pct >= 0;
          const isSelected = selected === sym;

          return (
            <button
              key={sym}
              onClick={() => onSelect(sym)}
              className={`p-3 text-left transition-colors duration-150 hover:bg-gray-800/60 focus:outline-none
                ${isSelected ? 'bg-blue-900/20 border-b-2 border-blue-500' : ''}`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] text-gray-500 font-semibold">{sym}</span>
                <div className="flex items-center gap-1">
                  <SignalDot signal={snap.signal} />
                  <TrendBadge strength={snap.trend_strength} direction={snap.direction} />
                </div>
              </div>

              <p className="text-sm font-bold font-mono text-white">
                {snap.price?.toLocaleString('en-IN') ?? '–'}
              </p>

              <p className={`text-[10px] font-mono font-semibold ${up ? 'text-green-400' : 'text-red-400'}`}>
                {up ? '+' : ''}{snap.change_pct?.toFixed(2) ?? '0.00'}%
              </p>

              <div className="mt-1.5">
                <Sparkline data={hist} />
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
