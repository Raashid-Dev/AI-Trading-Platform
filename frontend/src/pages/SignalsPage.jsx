import TipsPanel   from '../components/TipsPanel';
import SignalTable  from '../components/SignalTable';
import TechnicalPanel from '../components/TechnicalPanel';

export default function SignalsPage({ state }) {
  const { signals, symbol_snapshot } = state;

  return (
    <div className="space-y-4">
      <TipsPanel signals={signals} />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <SignalTable signals={signals} />
        </div>
        <TechnicalPanel symbolSnapshot={symbol_snapshot} />
      </div>
    </div>
  );
}
