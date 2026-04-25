import { useState } from 'react';
import useTradeStream from './useTradeStream';
import Header        from './components/Header';
import CapitalCard   from './components/CapitalCard';
import MarketOverview   from './components/MarketOverview';
import PriceChart       from './components/PriceChart';
import TechnicalPanel   from './components/TechnicalPanel';
import TipsPanel        from './components/TipsPanel';
import SignalTable      from './components/SignalTable';
import OpenTrades       from './components/OpenTrades';
import ClosedTrades     from './components/ClosedTrades';
import PerformancePanel from './components/PerformancePanel';
import EquityChart      from './components/EquityChart';

export default function App() {
  const { state, connected, transport, lastUpdate, error } = useTradeStream();
  const [selectedSymbol, setSelectedSymbol] = useState('NIFTY');

  const {
    capital, signals, open_trades, closed_trades,
    performance, diagnostics,
    price_history, symbol_snapshot,
  } = state;

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <div className="max-w-[1600px] mx-auto px-4 pb-10">

        <Header connected={connected} lastUpdate={lastUpdate} transport={transport} />

        {/* Error / degraded banners */}
        {error && !connected && (
          <div className="mb-4 px-4 py-3 rounded-lg bg-red-900/30 border border-red-700/40 text-red-400 text-sm flex items-center gap-2">
            <span>⚠</span> {error}
          </div>
        )}
        {error && connected && transport === 'polling' && (
          <div className="mb-4 px-4 py-3 rounded-lg bg-yellow-900/20 border border-yellow-700/30 text-yellow-400 text-sm flex items-center gap-2">
            <span>⚡</span> WebSocket unavailable — using polling fallback
          </div>
        )}

        <div className="space-y-4">

          {/* ── Row 1: Market Overview (symbol cards + sparklines) ── */}
          <MarketOverview
            symbolSnapshot={symbol_snapshot}
            priceHistory={price_history}
            onSelect={setSelectedSymbol}
            selected={selectedSymbol}
          />

          {/* ── Row 2: Price Chart + Technical Analysis ── */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div className="lg:col-span-2">
              <PriceChart
                symbol={selectedSymbol}
                priceHistory={price_history}
                symbolSnapshot={symbol_snapshot}
              />
            </div>
            <TechnicalPanel symbolSnapshot={symbol_snapshot} />
          </div>

          {/* ── Row 3: Capital + Performance ── */}
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
            <CapitalCard capital={capital} />
            <div className="lg:col-span-3">
              <PerformancePanel performance={performance} diagnostics={diagnostics} />
            </div>
          </div>

          {/* ── Row 4: AI Tips / Recommendations ── */}
          <TipsPanel signals={signals} />

          {/* ── Row 5: Signal Table (raw) ── */}
          <SignalTable signals={signals} />

          {/* ── Row 6: Open + Closed Trades ── */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <OpenTrades   trades={open_trades} />
            <ClosedTrades trades={closed_trades} />
          </div>

          {/* ── Row 7: Equity Curve ── */}
          <EquityChart closedTrades={closed_trades} initialCapital={100000} />

        </div>
      </div>
    </div>
  );
}
