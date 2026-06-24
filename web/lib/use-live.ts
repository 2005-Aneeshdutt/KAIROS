"use client";

import { useEffect } from "react";

/**
 * Live data via Server-Sent Events with an automatic polling fallback.
 * Tries `/api{path}/stream`; if it errors OR sends nothing within 4s
 * (e.g. a buffering proxy), it falls back to polling `/api{path}`.
 */
export function useLiveData<T>(path: string, onData: (d: T) => void, pollMs = 2500) {
  useEffect(() => {
    let es: EventSource | null = null;
    let poll: ReturnType<typeof setInterval> | null = null;
    let stopped = false;
    let got = false;

    const startPoll = () => {
      if (poll || stopped) return;
      const f = () =>
        fetch(`/api${path}`, { cache: "no-store" })
          .then((r) => (r.ok ? r.json() : null))
          .then((d) => { if (d && !stopped) onData(d as T); })
          .catch(() => {});
      f();
      poll = setInterval(f, pollMs);
    };

    // Paint immediately — don't wait for the first SSE push (kills perceived latency).
    fetch(`/api${path}`, { cache: "no-store" })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => { if (d && !stopped && !got) onData(d as T); })
      .catch(() => {});

    try {
      es = new EventSource(`/api${path}/stream`);
      es.onmessage = (e) => {
        got = true;
        try { onData(JSON.parse(e.data) as T); } catch { /* ignore */ }
      };
      es.onerror = () => { es?.close(); es = null; startPoll(); };
      setTimeout(() => { if (!got && !stopped) { es?.close(); es = null; startPoll(); } }, 4000);
    } catch {
      startPoll();
    }

    return () => { stopped = true; es?.close(); if (poll) clearInterval(poll); };
  }, [path]);
}
