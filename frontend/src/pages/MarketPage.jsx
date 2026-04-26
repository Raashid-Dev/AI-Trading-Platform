import { useState } from 'react';
import MarketOverview   from '../components/MarketOverview';
import PriceChart       from '../components/PriceChart';
import TechnicalPanel   from '../components/TechnicalPanel';
import CapitalCard      from '../components/CapitalCard';
import PerformancePanel from '../components/PerformancePanel';
import OIPanel          from '../components/OIPanel';

export default function MarketPage({ state }) {
  const [selectedSymbol, setSelectedSymbol] = useState('NIFTY');
  const [oiSymbol, setOiSymbol]             = useState('NIFTY');
  const { capital, performance, diagnostics, price_history, symbol_snapshot } = state;

  const handleSelect = (sym) => {
    setSelectedSymbol(sym);
    if (sym === 'BANKNIFTY') setOiSymbol('BANKNIFTY');
    else setOiSymbol('NIFTY');
  };

  return (
    <div className="space-y-4">
      <MarketOverview
        symbolSnapshot={symbol_snapshot}
        priceHistory={price_history}
        onSelect={handleSelect}
        selected={selectedSymbol}
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <PriceChart symbol={selectedSymbol} symbolSnapshot={symbol_snapshot} />
        </div>
        <TechnicalPanel symbolSnapshot={symbol_snapshot} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Capital + Performance */}
        <div className="lg:col-span-2 grid grid-cols-1 lg:grid-cols-4 gap-4">
          <CapitalCard capital={capital} />
          <div className="lg:col-span-3">
            <PerformancePanel performance={performance} diagnostics={diagnostics} />
          </div>
        </div>

        {/* Open Interest */}
        <div className="space-y-2">
          <div className="flex gap-2">
            {['NIFTY', 'BANKNIFTY'].map(s => (
              <button key={s} onClick={() => setOiSymbol(s)}
                className={`px-3 py-1 text-xs font-semibold rounded-lg transition-all border ${
                  oiSymbol === s
                    ? 'bg-blue-900/30 border-blue-600 text-blue-300'
                    : 'bg-gray-800/50 border-gray-700/50 text-gray-500 hover:text-white'
                }`}>{s}</button>
            ))}
          </div>
          <OIPanel symbol={oiSymbol} />
        </div>
      </div>
    </div>
  );
}
