import { useState, useEffect } from 'react';

const API_BASE = import.meta.env.VITE_BASE_URL?.startsWith('http')
  ? import.meta.env.VITE_BASE_URL
  : (import.meta.env.VITE_API_URL || 'http://localhost:8000');

function timeAgo(isoStr) {
  if (!isoStr) return '';
  const diff = (Date.now() - new Date(isoStr).getTime()) / 1000;
  if (diff < 60)   return `${Math.floor(diff)}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400)return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

const CATEGORIES = ['All', 'NIFTY', 'BANKNIFTY', 'RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK'];

function NewsCard({ item }) {
  const [expanded, setExpanded] = useState(false);
  const summary = item.summary?.replace(/<[^>]*>/g, '').trim();
  const previewLen = 160;
  const needsExpand = summary && summary.length > previewLen;

  return (
    <article className="bg-gray-900 rounded-xl border border-gray-800 p-4 hover:border-gray-700 transition-colors">
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-[10px] font-semibold text-blue-400 bg-blue-900/20 border border-blue-800/30 px-2 py-0.5 rounded-full uppercase tracking-wider">
            {item.source}
          </span>
          <span className="text-[10px] text-gray-600">{timeAgo(item.published)}</span>
        </div>
        <a
          href={item.link}
          target="_blank"
          rel="noopener noreferrer"
          className="text-gray-600 hover:text-blue-400 transition-colors flex-shrink-0"
          title="Open article"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
          </svg>
        </a>
      </div>

      <h3 className="text-sm font-semibold text-white leading-snug mb-2">
        <a href={item.link} target="_blank" rel="noopener noreferrer"
          className="hover:text-blue-300 transition-colors">
          {item.title}
        </a>
      </h3>

      {summary && (
        <p className="text-xs text-gray-400 leading-relaxed">
          {expanded || !needsExpand ? summary : `${summary.slice(0, previewLen)}…`}
          {needsExpand && (
            <button
              onClick={() => setExpanded(e => !e)}
              className="ml-1 text-blue-500 hover:text-blue-300 font-medium transition-colors"
            >
              {expanded ? 'less' : 'more'}
            </button>
          )}
        </p>
      )}
    </article>
  );
}

function SkeletonCard() {
  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 p-4 animate-pulse">
      <div className="flex gap-2 mb-3">
        <div className="h-4 w-16 bg-gray-800 rounded-full" />
        <div className="h-4 w-10 bg-gray-800 rounded-full" />
      </div>
      <div className="h-4 w-full bg-gray-800 rounded mb-1" />
      <div className="h-4 w-3/4 bg-gray-800 rounded mb-3" />
      <div className="h-3 w-full bg-gray-800/60 rounded mb-1" />
      <div className="h-3 w-5/6 bg-gray-800/60 rounded" />
    </div>
  );
}

export default function NewsPage() {
  const [news, setNews]         = useState([]);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState(null);
  const [filter, setFilter]     = useState('All');
  const [lastFetch, setLastFetch] = useState(null);

  const fetchNews = async () => {
    try {
      const res = await fetch(`${API_BASE}/news`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setNews(data.items || []);
      setLastFetch(new Date());
      setError(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNews();
    const interval = setInterval(fetchNews, 5 * 60 * 1000); // refresh every 5 min
    return () => clearInterval(interval);
  }, []);

  const filtered = filter === 'All'
    ? news
    : news.filter(n =>
        n.title?.toUpperCase().includes(filter) ||
        n.summary?.toUpperCase().includes(filter)
      );

  return (
    <div className="space-y-4">
      {/* Header row */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-bold text-white">Market News</h2>
          <p className="text-[10px] text-gray-500 mt-0.5">
            {lastFetch ? `Updated ${timeAgo(lastFetch.toISOString())}` : 'Fetching latest news…'}
            {' · '}Auto-refreshes every 5 minutes
          </p>
        </div>
        <button
          onClick={() => { setLoading(true); fetchNews(); }}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-blue-900/30 border border-blue-700/40 text-blue-300 hover:bg-blue-900/50 transition-colors disabled:opacity-40"
        >
          <svg className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Refresh
        </button>
      </div>

      {/* Filter pills */}
      <div className="flex flex-wrap gap-2">
        {CATEGORIES.map(cat => (
          <button
            key={cat}
            onClick={() => setFilter(cat)}
            className={`px-3 py-1.5 rounded-full text-xs font-semibold transition-all border ${
              filter === cat
                ? 'bg-blue-900/40 border-blue-600 text-blue-300'
                : 'bg-gray-800/50 border-gray-700/50 text-gray-400 hover:text-white hover:border-gray-600'
            }`}
          >
            {cat}
          </button>
        ))}
        {filter !== 'All' && (
          <span className="px-3 py-1.5 text-xs text-gray-500">
            {filtered.length} result{filtered.length !== 1 ? 's' : ''}
          </span>
        )}
      </div>

      {/* Error state */}
      {error && (
        <div className="bg-red-900/20 border border-red-700/30 rounded-xl p-4 text-sm text-red-400">
          ⚠ Could not load news: {error}. Check backend connection.
        </div>
      )}

      {/* Content */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => <SkeletonCard key={i} />)}
        </div>
      ) : filtered.length === 0 ? (
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-10 text-center">
          <p className="text-gray-500 text-sm">No news found{filter !== 'All' ? ` for "${filter}"` : ''}.</p>
          {filter !== 'All' && (
            <button onClick={() => setFilter('All')} className="mt-2 text-xs text-blue-400 hover:text-blue-300">
              Clear filter
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filtered.map((item, i) => <NewsCard key={i} item={item} />)}
        </div>
      )}

      {/* Footer */}
      {!loading && filtered.length > 0 && (
        <p className="text-center text-[10px] text-gray-700 pb-2">
          {filtered.length} articles · Sources: Economic Times, ET Markets, Live Mint
        </p>
      )}
    </div>
  );
}
