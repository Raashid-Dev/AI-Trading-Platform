import useTradeStream from './useTradeStream';
import Header from './components/Header';
import CapitalCard from './components/CapitalCard';
import SignalTable from './components/SignalTable';
import OpenTrades from './components/OpenTrades';
import ClosedTrades from './components/ClosedTrades';
import PerformancePanel from './components/PerformancePanel';
import EquityChart from './components/EquityChart';

export default function App() {
  const { state, connected, transport, lastUpdate, error } = useTradeStream();

  const { capital, signals, open_trades, closed_trades, performance, diagnostics } = state;

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <div className="max-w-[1600px] mx-auto px-4 pb-8">

        <Header connected={connected} lastUpdate={lastUpdate} transport={transport} />

        {/* Error banner */}
        {error && !connected && (
          <div className="mb-4 px-4 py-3 rounded-lg bg-red-900/30 border border-red-700/40 text-red-400 text-sm flex items-center gap-2">
            <span className="text-base">⚠</span>
            {error}
          </div>
        )}

        {/* Reconnecting banner (connected but degraded) */}
        {error && connected && transport === 'polling' && (
          <div className="mb-4 px-4 py-3 rounded-lg bg-yellow-900/20 border border-yellow-700/30 text-yellow-400 text-sm flex items-center gap-2">
            <span className="text-base">⚡</span>
            WebSocket unavailable — using polling fallback
          </div>
        )}

        <div className="space-y-4">

          {/* ── Row 1: Capital + Performance ── */}
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
            <CapitalCard capital={capital} />
            <div className="lg:col-span-3">
              <PerformancePanel performance={performance} diagnostics={diagnostics} />
            </div>
          </div>

          {/* ── Row 2: Live Signals ── */}
          <SignalTable signals={signals} />

          {/* ── Row 3: Open + Closed Trades ── */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <OpenTrades trades={open_trades} />
            <ClosedTrades trades={closed_trades} />
          </div>

          {/* ── Row 4: Equity Curve ── */}
          <EquityChart
            closedTrades={closed_trades}
            initialCapital={100000}
          />

        </div>
      </div>
    </div>
  );
}
