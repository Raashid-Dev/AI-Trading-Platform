import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const client = axios.create({
  baseURL: BASE_URL,
  timeout: 4000,
});

/**
 * Full snapshot: { capital, signals, open_trades, closed_trades, performance, diagnostics }
 */
export const fetchState = () =>
  client.get('/state').then(r => r.data);

/**
 * Latest filtered signals from the pipeline.
 * Array of { symbol, signal, confidence, direction, score, regime, vix_tier, … }
 */
export const fetchSignals = () =>
  client.get('/signals').then(r => r.data);

/**
 * Compact overview: { capital, signal_summary, performance, open_count, closed_count }
 */
export const fetchSummary = () =>
  client.get('/summary').then(r => r.data);

/**
 * Trade lists: { open: [...], closed: [...] }
 */
export const fetchTrades = () =>
  client.get('/trades').then(r => r.data);

/**
 * Capital state: { capital, max_capital, drawdown_pct }
 */
export const fetchCapital = () =>
  client.get('/capital').then(r => r.data);
