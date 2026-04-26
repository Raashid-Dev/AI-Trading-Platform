import { useState } from 'react';
import useTradeStream from './useTradeStream';
import Header        from './components/Header';
import MarketPage    from './pages/MarketPage';
import StocksPage    from './pages/StocksPage';
import SignalsPage   from './pages/SignalsPage';
import PortfolioPage from './pages/PortfolioPage';
import NewsPage      from './pages/NewsPage';
import LandingPage   from './pages/LandingPage';

// Show landing page on first load unless user came back to the app directly
function getInitialView() {
  try {
    // If URL hash is #/app, skip landing
    if (window.location.hash === '#/app') return 'dashboard';
  } catch (_) {}
  return 'landing';
}

export default function App() {
  const [view, setView] = useState(getInitialView);
  const { state, connected, transport, lastUpdate, error } = useTradeStream();
  const [page, setPage] = useState('market');
  const marketStatus = state.market_status || 'CLOSED';

  // ── Landing page ─────────────────────────────────────────────────
  if (view === 'landing') {
    return (
      <LandingPage
        onLaunch={() => {
          setView('dashboard');
          try { window.location.hash = '#/app'; } catch (_) {}
          window.scrollTo({ top: 0, behavior: 'instant' });
        }}
      />
    );
  }

  // ── Dashboard ────────────────────────────────────────────────────
  const renderPage = () => {
    switch (page) {
      case 'market':    return <MarketPage    state={state} />;
      case 'stocks':    return <StocksPage    state={state} />;
      case 'signals':   return <SignalsPage   state={state} />;
      case 'portfolio': return <PortfolioPage state={state} />;
      case 'news':      return <NewsPage />;
      default:          return <MarketPage    state={state} />;
    }
  };

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <div className="max-w-[1600px] mx-auto px-4 pb-10">

        <Header
          connected={connected}
          lastUpdate={lastUpdate}
          transport={transport}
          page={page}
          onPageChange={setPage}
          marketStatus={marketStatus}
          onHome={() => {
            setView('landing');
            try { window.location.hash = ''; } catch (_) {}
            window.scrollTo({ top: 0, behavior: 'instant' });
          }}
        />

        {/* Connection banners */}
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

        {/* Page content */}
        <div className="mt-4">
          {renderPage()}
        </div>

      </div>
    </div>
  );
}
