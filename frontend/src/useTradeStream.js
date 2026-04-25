/**
 * useTradeStream
 *
 * Connects to the backend WebSocket for real-time state pushes.
 * Falls back to HTTP polling if WebSocket is unavailable.
 * Periodically retries the WebSocket while in polling mode.
 *
 * Returned shape:
 *   { state, connected, transport, lastUpdate, error }
 *
 *   transport: "websocket" | "polling" | "connecting"
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { fetchState } from './api';

// ── Config ─────────────────────────────────────────────────
const WS_URL  = import.meta.env.VITE_WS_URL  || 'ws://localhost:8000/ws';
const POLL_MS = parseInt(import.meta.env.VITE_POLL_MS || '10000', 10);

// PART 7 — fixed backoff schedule (ms): 1s → 2s → 5s → 10s → 10s → …
const WS_BACKOFF     = [1000, 2000, 5000, 10000];
const WS_MAX_RETRIES = 8;

// While in polling-fallback mode, attempt WS reconnect every 30 s
const WS_RETRY_FROM_POLL_MS = 30_000;

const EMPTY_STATE = {
  capital:       { capital: 0, max_capital: 0, drawdown_pct: 0 },
  signals:       [],
  open_trades:   [],
  closed_trades: [],
  performance:   {},
  diagnostics:   {},
};

// ── Hook ───────────────────────────────────────────────────
export default function useTradeStream() {
  const [state,      setState]      = useState(EMPTY_STATE);
  const [connected,  setConnected]  = useState(false);
  const [transport,  setTransport]  = useState('connecting');
  const [lastUpdate, setLastUpdate] = useState(null);
  const [error,      setError]      = useState(null);

  const wsRef           = useRef(null);
  const retryCount      = useRef(0);
  const retryTimer      = useRef(null);
  const pollTimer       = useRef(null);
  const wsRetryInterval = useRef(null);   // periodic WS re-attempt while polling
  const usingFallback   = useRef(false);
  const unmounted       = useRef(false);
  const connectRef      = useRef(null);   // forward ref to break circular dep

  // ── State applicator ─────────────────────────────────────
  const applyState = useCallback((raw) => {
    if (unmounted.current) return;
    if (raw?.type === 'ping') return;
    if (raw?.status === 'waiting') return;

    setState(prev => ({ ...EMPTY_STATE, ...raw }));
    setConnected(true);
    setLastUpdate(new Date());
    setError(null);
  }, []);

  // ── Stop polling + periodic WS retry ─────────────────────
  const stopPolling = useCallback(() => {
    if (pollTimer.current)       { clearInterval(pollTimer.current);       pollTimer.current       = null; }
    if (wsRetryInterval.current) { clearInterval(wsRetryInterval.current); wsRetryInterval.current = null; }
  }, []);

  // ── Polling fallback ─────────────────────────────────────
  const startPolling = useCallback(() => {
    if (pollTimer.current) return;   // already polling
    usingFallback.current = true;
    setTransport('polling');

    const poll = async () => {
      if (unmounted.current) return;
      try {
        const data = await fetchState();
        applyState(data);
      } catch (err) {
        if (!unmounted.current) {
          setConnected(false);
          setError(err?.response?.data?.detail || err.message || 'Poll failed');
        }
      }
    };

    poll();
    pollTimer.current = setInterval(poll, POLL_MS);

    // PART 7 — auto-retry WebSocket every 30 s while in polling mode
    wsRetryInterval.current = setInterval(() => {
      if (unmounted.current || !usingFallback.current) return;
      retryCount.current = 0;             // fresh backoff sequence
      connectRef.current?.();
    }, WS_RETRY_FROM_POLL_MS);
  }, [applyState]);

  // ── WebSocket connection ──────────────────────────────────
  const connect = useCallback(() => {
    if (unmounted.current) return;

    // Tear down any stale socket
    if (wsRef.current) {
      wsRef.current.onopen    = null;
      wsRef.current.onmessage = null;
      wsRef.current.onerror   = null;
      wsRef.current.onclose   = null;
      wsRef.current.close();
      wsRef.current = null;
    }

    // Don't clobber "polling" badge if we're mid-polling retry
    if (!usingFallback.current) setTransport('connecting');

    let ws;
    try {
      ws = new WebSocket(WS_URL);
    } catch {
      startPolling();
      return;
    }

    wsRef.current = ws;

    ws.onopen = () => {
      if (unmounted.current) return;
      retryCount.current    = 0;
      usingFallback.current = false;
      setTransport('websocket');
      stopPolling();
    };

    ws.onmessage = (evt) => {
      if (unmounted.current) return;
      try { applyState(JSON.parse(evt.data)); } catch { /* malformed — ignore */ }
    };

    ws.onerror = () => { /* always followed by onclose */ };

    ws.onclose = (evt) => {
      if (unmounted.current) return;
      setConnected(false);

      const isAbnormal = evt.code !== 1000 && evt.code !== 1001;

      if (retryCount.current < WS_MAX_RETRIES && isAbnormal) {
        // PART 7 — fixed schedule: 1s, 2s, 5s, 10s, 10s, …
        const delay = WS_BACKOFF[Math.min(retryCount.current, WS_BACKOFF.length - 1)];
        retryCount.current++;
        setError(
          `WS closed (${evt.code}) — reconnecting in ${(delay / 1000).toFixed(0)}s ` +
          `(attempt ${retryCount.current}/${WS_MAX_RETRIES})`
        );
        retryTimer.current = setTimeout(connect, delay);
      } else {
        // Exhausted retries → polling; periodic 30 s WS retry starts inside startPolling
        setError('WebSocket unavailable — using HTTP polling fallback');
        startPolling();
      }
    };
  }, [applyState, startPolling, stopPolling]);

  // Keep connectRef in sync (avoids stale-closure in setInterval)
  useEffect(() => { connectRef.current = connect; }, [connect]);

  // ── Lifecycle ─────────────────────────────────────────────
  useEffect(() => {
    unmounted.current = false;
    connect();

    return () => {
      unmounted.current = true;
      clearTimeout(retryTimer.current);
      stopPolling();
      if (wsRef.current) {
        wsRef.current.onopen    = null;
        wsRef.current.onmessage = null;
        wsRef.current.onerror   = null;
        wsRef.current.onclose   = null;
        wsRef.current.close(1000, 'component unmounted');
      }
    };
  }, [connect, stopPolling]);

  return { state, connected, transport, lastUpdate, error };
}
