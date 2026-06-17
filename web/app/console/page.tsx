"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { store, getUid } from "@/lib/api";

const SEG_COLOR: Record<string, string> = {
  Persuadable: "#3b82f6", "Sure Thing": "#22c55e", "Lost Cause": "#ef4444",
  "Sleeping Dog": "#eab308", Converted: "#a855f7", Unknown: "#64748b",
};
const BRAND = "#e31837";

export default function ConsolePage() {
  const [uid, setUid] = useState("");
  const [data, setData] = useState<any>(null);
  const [tab, setTab] = useState<"data" | "with" | "without">("data");
  const timer = useRef<any>(null);

  useEffect(() => {
    const id = getUid();
    setUid(id);
    const poll = async () => { const d = await store.visitor(id); if (d) setData(d); };
    poll();
    timer.current = setInterval(poll, 1200);
    return () => clearInterval(timer.current);
  }, []);

  const p = data?.profile;
  const nba = data?.next_best_action;
  const mail = data?.mail;
  const events = data?.recent ?? [];
  const l = p?.loyalty;

  return (
    <main className="min-h-screen bg-ink text-slate-200">
      <header className="border-b border-line">
        <div className="max-w-[1100px] mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-2.5 h-7 bg-epsilon rounded-sm" />
            <h1 className="font-bold tracking-tight">Conductor Console</h1>
            <span className="flex items-center gap-1.5 text-xs text-emerald-400 ml-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" /> live · {uid}
            </span>
          </div>
          <div className="flex gap-4 text-sm">
            <Link href="/store" className="text-slate-400 hover:text-white">← Storefront</Link>
            <Link href="/" className="text-slate-400 hover:text-white">Analytics →</Link>
          </div>
        </div>
      </header>

      <div className="max-w-[1100px] mx-auto px-6 py-6">
        <p className="text-sm text-slate-500 mb-4">
          The marketer&apos;s real-time view of the shopper currently browsing the store (open the store in another tab and click — this updates live).
        </p>

        {!p || p.events === 0 ? (
          <div className="card text-center py-16 text-slate-500">
            No activity yet. <Link href="/store" className="text-epsilon underline">Open the storefront</Link> and start clicking.
          </div>
        ) : (
          <div className="grid md:grid-cols-[340px_1fr] gap-5">
            {/* left: live profile */}
            <div className="space-y-4">
              <div className="card">
                <div className="card-title">Live shopper profile</div>
                <div className="flex items-center justify-between mb-3">
                  <span className="pill" style={{ background: (SEG_COLOR[p.segment] ?? "#64748b") + "22", color: SEG_COLOR[p.segment] ?? "#94a3b8" }}>{p.segment}</span>
                  <span className="text-xs text-slate-400">{p.intent}</span>
                </div>
                <div className="flex justify-between text-[11px] text-slate-500 mb-1"><span>purchase intent</span><span>{p.intent_score}/100</span></div>
                <div className="h-2 bg-panel2 rounded-full overflow-hidden mb-3">
                  <div className="h-full transition-all duration-500" style={{ width: `${p.intent_score}%`, background: BRAND }} />
                </div>
                {p.uplift != null && (
                  <div className="bg-panel2 rounded-lg p-2.5 mb-3 border border-line">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] uppercase tracking-widest text-slate-500">Causal uplift</span>
                      <span className="text-[9px] text-emerald-400">● {p.scored_by}</span>
                    </div>
                    <div className="flex items-baseline gap-3 mt-1">
                      <span className="text-xl font-bold" style={{ color: p.uplift >= 0 ? "#22c55e" : "#ef4444" }}>{(p.uplift * 100).toFixed(1)}%</span>
                      <span className="text-xs text-slate-400">incremental lift</span>
                      <span className="text-xs text-slate-500 ml-auto">base {(p.base_rate * 100).toFixed(1)}% · +${p.inc_value}</span>
                    </div>
                    <div className="text-[10px] text-slate-500 mt-1">This is a model prediction on live behavior — not a rule.</div>
                  </div>
                )}
                <div className="grid grid-cols-4 gap-2 text-center">
                  {[["views", p.total_views], ["wish", p.wishlist.length], ["cart", p.cart.length], ["dev", p.devices.length]].map(([k, v]) => (
                    <div key={k as string} className="bg-panel2 rounded-lg py-1.5">
                      <div className="text-base font-bold tabular-nums">{v as any}</div>
                      <div className="text-[9px] uppercase tracking-wider text-slate-500">{k as string}</div>
                    </div>
                  ))}
                </div>
              </div>

              {l && (
                <div className="card">
                  <div className="card-title">Loyalty</div>
                  <div className="flex items-baseline justify-between">
                    <span className="text-2xl font-bold">{l.points} <span className="text-sm text-slate-500">pts</span></span>
                    <span className="pill bg-amber-500/20 text-amber-300">{l.tier}</span>
                  </div>
                  <div className="text-xs text-slate-500 mt-1">${l.dollar_value} value · {l.to_next} pts to {l.next_tier}</div>
                </div>
              )}

              {nba && (
                <div className="card">
                  <div className="card-title">Next best action</div>
                  <div className="text-sm font-semibold" style={{ color: nba.recommend ? "#22c55e" : "#94a3b8" }}>
                    {nba.recommend ? `TARGET · ${nba.channel}` : "HOLD / restraint"}
                  </div>
                  <div className="text-xs text-slate-400 mt-1">{nba.rationale}</div>
                </div>
              )}
            </div>

            {/* right: tabs */}
            <div className="card">
              <div className="flex gap-1 mb-3 text-xs">
                {([["data", "📡 Data layer"], ["with", "✅ With Conductor"], ["without", "🚫 Without Conductor"]] as const).map(([k, label]) => (
                  <button key={k} onClick={() => setTab(k)}
                    className={`px-3 py-1.5 rounded-lg font-semibold transition ${tab === k ? "bg-panel2 text-white" : "text-slate-500 hover:text-slate-300"}`}>{label}</button>
                ))}
              </div>
              {tab === "data" && <DataLayer events={events} />}
              {tab === "with" && <WithConductor mail={mail} />}
              {tab === "without" && <WithoutConductor mail={mail} />}
            </div>
          </div>
        )}
      </div>
    </main>
  );
}

function DataLayer({ events }: { events: any[] }) {
  return (
    <div className="bg-black/40 border border-line rounded-xl p-3 font-mono text-[11px] max-h-[520px] overflow-auto">
      <div className="text-slate-500 mb-2">// every interaction is captured as a structured event</div>
      {events.length === 0 ? <div className="text-slate-600">awaiting clicks…</div> :
        events.map((e, i) => (
          <pre key={i} className="mb-2 leading-relaxed">
            <span className="text-slate-600">{"{"}</span>{"\n"}
            {Object.entries(e).map(([k, v]) => (
              <span key={k}>{"  "}<span className="text-sky-400">&quot;{k}&quot;</span>: <span className="text-emerald-300">{JSON.stringify(v)}</span>,{"\n"}</span>
            ))}
            <span className="text-slate-600">{"}"}</span>
          </pre>
        ))}
    </div>
  );
}

function WithConductor({ mail }: { mail: any }) {
  const c = mail?.conductor;
  if (!c) return <div className="text-sm text-slate-500 p-6 text-center">Awaiting a decision…</div>;
  return c.send ? (
    <div className="bg-panel2 border border-emerald-500/30 rounded-xl overflow-hidden">
      <div className="bg-emerald-500/10 px-4 py-2 text-xs text-emerald-300 flex justify-between"><span>📧 {c.channel} · {c.reward_type}</span><span>{c.timing}</span></div>
      <div className="p-4"><div className="font-semibold text-white">{c.subject}</div><div className="text-sm text-slate-400 mt-1">{c.body}</div></div>
      <div className="px-4 py-2 border-t border-line text-xs text-slate-500">🧠 {c.reason}</div>
    </div>
  ) : (
    <div className="bg-panel2 border border-slate-600/30 rounded-xl p-4">
      <div className="font-semibold text-slate-300">🔕 Deliberate silence</div>
      <div className="text-sm text-slate-500 mt-1">{c.reason}</div>
      <div className="text-xs text-emerald-400 mt-2">Restraint = budget saved + customer not annoyed.</div>
    </div>
  );
}

function WithoutConductor({ mail }: { mail: any }) {
  const blasts = mail?.traditional ?? [];
  return (
    <div className="bg-black/50 border border-line rounded-xl p-4 font-mono text-xs max-h-[520px] overflow-auto">
      <div className="text-amber-400 mb-2">$ legacy-crm --batch-blast --segment=ALL</div>
      {blasts.map((b: any, i: number) => (
        <div key={i} className="mb-2">
          <div className="text-slate-500">[{String(9 + i).padStart(2, "0")}:00] <span className="text-rose-400">SEND</span> {b.channel} → <span className="text-amber-300">{b.tag}</span></div>
          <div className="text-slate-300 pl-2">“{b.subject}”</div>
          <div className="text-slate-600 pl-2">{b.preview}</div>
        </div>
      ))}
      <div className="border-t border-line pt-2 mt-1 text-rose-400">⚠ {blasts.length} generic messages · no targeting · same to everyone</div>
    </div>
  );
}
