import CapitalCard     from '../components/CapitalCard';
import PerformancePanel from '../components/PerformancePanel';
import OpenTrades       from '../components/OpenTrades';
import ClosedTrades     from '../components/ClosedTrades';
import EquityChart      from '../components/EquityChart';

export default function PortfolioPage({ state }) {
  const { capital, performance, diagnostics, open_trades, closed_trades } = state;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        <CapitalCard capital={capital} />
        <div className="lg:col-span-3">
          <PerformancePanel performance={performance} diagnostics={diagnostics} />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <OpenTrades   trades={open_trades} />
        <ClosedTrades trades={closed_trades} />
      </div>

      <EquityChart closedTrades={closed_trades} initialCapital={100000} />
    </div>
  );
}
