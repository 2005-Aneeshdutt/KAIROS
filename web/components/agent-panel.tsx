"use client";

import { useState } from "react";
import { store } from "@/lib/api";

const PRESETS = [
  "I have a $5,000 budget this week — where should I spend it and where should I hold back?",
  "Make the case for Kairos vs a traditional batch-and-blast campaign, with numbers.",
  "Which segment is bleeding the most budget right now, and what should I do?",
];

const TOOL_LABEL: Record<string, string> = {
  get_segments: "reading customer segments",
  solve_allocation: "solving budget allocation",
  run_benchmark: "running head-to-head benchmark",
  get_strategy: "pulling live store strategy",
};

export function AgentPanel({ hero = false }: { hero?: boolean }) {
  const [goal, setGoal] = useState("");
  const [res, setRes] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  async function ask(q?: string) {
    const g = (q ?? goal).trim();
    if (!g) return;
    setGoal(g);
    setLoading(true);
    setRes(null);
    const r = await store.agent(g);
    setRes(r);
    setLoading(false);
  }

  return (
    <section className={`card mb-6 relative overflow-hidden ${hero ? "border border-epsilon/40 ring-1 ring-epsilon/20" : "border border-epsilon/30"}`}>
      {hero && <div className="absolute inset-x-0 top-0 h-[2px] bg-gradient-to-r from-epsilon via-epsilon/40 to-transparent" />}

      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="card-title mb-0 flex items-center gap-2">
          <span className="text-base">🧠</span> AI Strategist
          <span className="pill text-[10px] bg-epsilon/15 text-epsilon border border-epsilon/30">tool-using agent</span>
        </div>
        <span className="text-[10px] text-slate-500">plans by calling the platform&apos;s own tools — grounded in the real numbers</span>
      </div>
      <p className="text-xs text-slate-500 mt-1 mb-3">
        Ask a goal in plain English. The agent decides which of the platform&apos;s tools to call —
        segments, allocation, benchmark, live strategy — then returns a grounded plan. Runs rule-based with
        no key; upgrades to a hosted LLM (via OpenRouter) automatically when a key is configured.
      </p>

      <div className="flex gap-2">
        <input
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && ask()}
          placeholder="Ask the strategist a goal…"
          className="flex-1 bg-panel2 border border-line rounded-lg px-3 py-2 text-sm outline-none focus:border-epsilon/50"
        />
        <button
          onClick={() => ask()}
          disabled={loading}
          className="text-xs font-semibold px-4 py-2 rounded-lg bg-epsilon/20 text-epsilon hover:bg-epsilon/30 disabled:opacity-50"
        >
          {loading ? "Thinking…" : "Ask"}
        </button>
      </div>

      <div className="flex flex-wrap gap-1.5 mt-2">
        {PRESETS.map((p) => (
          <button
            key={p}
            onClick={() => ask(p)}
            disabled={loading}
            className="text-[11px] text-slate-400 bg-panel2 border border-line rounded-full px-2.5 py-1 hover:text-slate-200"
          >
            {p.length > 52 ? p.slice(0, 52) + "…" : p}
          </button>
        ))}
      </div>

      {loading && (
        <div className="mt-3 flex items-center gap-2 text-xs text-slate-400">
          <span className="w-3 h-3 rounded-full border-2 border-epsilon/40 border-t-epsilon animate-spin" />
          planning — selecting tools and pulling live numbers…
        </div>
      )}

      {res && (
        <div className="mt-3">
          {res.steps?.length > 0 && (
            <div className="mb-2.5">
              <div className="text-[10px] uppercase tracking-widest text-slate-500 mb-1.5">
                Reasoning trace · {res.steps.length} tool call{res.steps.length > 1 ? "s" : ""}
              </div>
              <ol className="space-y-1">
                {res.steps.map((s: any, i: number) => (
                  <li key={i} className="flex items-center gap-2 text-xs">
                    <span className="w-4 h-4 shrink-0 rounded-full bg-emerald-500/15 text-emerald-300 text-[10px] grid place-items-center font-bold">{i + 1}</span>
                    <span className="text-slate-300">{TOOL_LABEL[s.tool] ?? s.tool}</span>
                    <span className="font-mono text-[10px] text-emerald-300/80 bg-black/30 border border-line rounded px-1.5 py-0.5">
                      {s.tool}
                      {s.input && Object.keys(s.input).length ? `(${JSON.stringify(s.input)})` : "()"}
                    </span>
                    <span className="text-emerald-400/70 text-[11px]">✓</span>
                  </li>
                ))}
              </ol>
            </div>
          )}
          <div className="bg-panel2 border border-line rounded-xl p-3 text-sm text-slate-200 whitespace-pre-wrap leading-relaxed">
            {res.answer}
          </div>
          <div className="text-[10px] text-slate-500 mt-1.5">
            {res.source === "claude"
              ? "✦ reasoned by Claude over the tool results"
              : res.source === "openrouter"
                ? `✦ reasoned by ${res.model ?? "an LLM"} via OpenRouter`
                : res.source === "planner"
                  ? "✦ rule-based planner (no API key) — set OPENROUTER_API_KEY to reason with an LLM"
                  : `source: ${res.source}`}
          </div>
        </div>
      )}
    </section>
  );
}
