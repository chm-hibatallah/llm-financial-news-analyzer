/**
 * hooks/useApi.js
 * ----------------
 * React hook for fetching data from the FinSentiment FastAPI backend.
 *
 * Usage
 * -----
 *   const { data, loading, error, refetch } = useApi("/analysis/findings");
 *
 * The hook falls back to mock data when the backend is not available,
 * so the dashboard always renders something meaningful.
 *
 * Base URL is read from VITE_API_URL env var (default: http://localhost:8000)
 */

import { useState, useEffect, useCallback } from "react";

const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export function useApi(endpoint, options = {}) {
  const { fallback = null, deps = [] } = options;

  const [data,    setData]    = useState(fallback);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(null);

  const fetch_ = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${BASE_URL}${endpoint}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      setData(json);
    } catch (err) {
      setError(err.message);
      if (fallback !== null) setData(fallback);   // graceful degradation
    } finally {
      setLoading(false);
    }
  }, [endpoint, ...deps]);

  useEffect(() => { fetch_(); }, [fetch_]);

  return { data, loading, error, refetch: fetch_ };
}

export function usePipelineStatus() {
  const { data } = useApi("/models/status", { fallback: { running: false } });
  return data;
}

export function useLeaderboard(ticker = null) {
  const url = ticker ? `/models/leaderboard?ticker=${ticker}` : "/models/leaderboard";
  return useApi(url, { fallback: [] });
}

export function useImportances(model = null) {
  const url = model ? `/models/importances?model=${model}` : "/models/importances";
  return useApi(url, { fallback: {} });
}

export function useCorrelation(ticker = null) {
  const url = ticker ? `/analysis/correlation?ticker=${ticker}` : "/analysis/correlation";
  return useApi(url, { fallback: [] });
}

export function useGranger(ticker = null) {
  const url = ticker ? `/analysis/granger?ticker=${ticker}` : "/analysis/granger";
  return useApi(url, { fallback: [] });
}

export function useFindings() {
  return useApi("/analysis/findings", { fallback: { findings: [] } });
}

/**
 * Trigger a pipeline run and poll for completion.
 * Returns { trigger, running, lastRunAt }
 */
export function usePipelineTrigger(endpoint) {
  const [running, setRunning] = useState(false);
  const [lastRunAt, setLastRunAt] = useState(null);

  const trigger = useCallback(async (params = {}) => {
    setRunning(true);
    try {
      await fetch(`${BASE_URL}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(params),
      });
      // Poll status every 2s
      const poll = setInterval(async () => {
        try {
          const res  = await fetch(`${BASE_URL}${endpoint.replace("/run", "/status")}`);
          const json = await res.json();
          if (!json.running) {
            setRunning(false);
            setLastRunAt(json.last_run_at);
            clearInterval(poll);
          }
        } catch { clearInterval(poll); setRunning(false); }
      }, 2000);
    } catch { setRunning(false); }
  }, [endpoint]);

  return { trigger, running, lastRunAt };
}