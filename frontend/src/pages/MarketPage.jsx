import { useState } from 'react';
import MarketOverview from '../components/MarketOverview';
import PriceChart     from '../components/PriceChart';
import TechnicalPanel from '../components/TechnicalPanel';
import CapitalCard    from '../components/CapitalCard';
import PerformancePanel from '../components/PerformancePanel';

export default function MarketPage({ state }) {
  const [selectedSymbol, setSelectedSymbol] = useState('NIFTY');
  const { capital, performance, diagnostics, price_history, symbol_snapshot } = state;

  return (
    <div className="space-y-4">
      <MarketOverview
        symbolSnapshot={symbol_snapshot}
        priceHistory={price_history}
        onSelect={setSelectedSymbol}
        selected={selectedSymbol}
      />

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

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        <CapitalCard capital={capital} />
        <div className="lg:col-span-3">
          <PerformancePanel performance={performance} diagnostics={diagnostics} />
        </div>
      </div>
    </div>
  );
}
