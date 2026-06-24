"use client";

import { useEffect, useState } from "react";
import { store, BUCKET_COLOR, fmtUSD, deletePerson, resetDemo } from "@/lib/api";
import { useLiveData } from "@/lib/use-live";
import { Shell } from "@/components/shell";

const EVENT_ICON: Record<string, string> = {
  view_product: "👁️", view_detail: "🔍", view_reviews: "⭐", add_to_cart: "🛒",
  remove_from_cart: "✖️", add_to_wishlist: "🤍", remove_from_wishlist: "💔",
  purchase: "💳", checkout: "🧾", checkout_start: "🧾", chat: "💬", search: "🔎",
  filter_category: "🗂️", back_to_browse: "↩️", redeem: "🎁",
};

function ago(ts: number) {
  if (!ts) return "—";
  const s = Math.max(0, Math.floor(Date.now() / 1000 - ts));
  if (s < 5) return "now";
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}

export default function PeoplePage() {
  const [people, setPeople] = useState<any[]>([]);
  const [sel, setSel] = useState<string | null>(null);
  const [detail, setDetail] = useState<any>(null);
  const [prods, setProds] = useState<Record<string, string>>({});
  const [strat, setStrat] = useState<any>(null);
  const [stratLoading, setStratLoading] = useState(false);
  const [drivers, setDrivers] = useState<any>(null);
  const [ident, setIdent] = useState<any>(null);
  const [idSummary, setIdSummary] = useState<any>(null);
  const [sending, setSending] = useState(false);
  const [sentMail, setSentMail] = useState<any>(null);

  async function sendMail(cid: string) {
    setSending(true); setSentMail(null);
    const r = await store.sendMail(cid);
    setSending(false);
    if (r?.ok) setSentMail(r);
    else alert(r?.error || "Could not send (customer may have opted out).");
  }

  useEffect(() => {
    store.catalogue().then((d) => {
      const m: Record<string, string> = {};
      (d.products || []).forEach((p: any) => { m[p.id] = p.name; });
      setProds(m);
    });
  }, []);

  useLiveData<{ people: any[] }>("/people", (d) => setPeople(d.people || []));

  useEffect(() => {
    const poll = () => store.identitySummary().then((d) => d && setIdSummary(d));
    poll();
    const t = setInterval(poll, 3000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    setStrat(null); setSentMail(null); setDrivers(null);
    if (!sel) { setDetail(null); setIdent(null); return; }
    store.customerDrivers(sel).then((d) => d && setDrivers(d));   // once per selection (compute-heavy)
    const poll = () => {
      store.visitor(sel).then((d) => d && setDetail(d));
      store.identity(sel).then((d) => d && setIdent(d));
    };
    poll();
    const t = setInterval(poll, 2000);
    return () => clearInterval(t);
  }, [sel]);

  useEffect(() => {
    if (!sel && people.length) setSel(people[0].core_id);
  }, [people, sel]);

  async function remove(cid: string) {
    if (!confirm("Delete this customer and all their activity? This cannot be undone.")) return;
    await deletePerson(cid);
    setSel(null);
    setDetail(null);
    const d = await store.people();
    setPeople(d.people || []);
  }

  async function askStrategist(cid: string) {
    setStrat(null);
    setStratLoading(true);
    const r = await store.customerStrategy(cid);
    setStrat(r);
    setStratLoading(false);
  }

  async function doReset() {
    if (!confirm("Reset ALL demo data? This deletes every customer and their activity.")) return;
    await resetDemo();
    setSel(null);
    setDetail(null);
    const d = await store.people();
    setPeople(d.people || []);
  }

  const selPerson = people.find((p) => p.core_id === sel);
  const prof = detail?.profile;
  const events: any[] = detail?.recent ?? [];
  const nba = detail?.next_best_action;

  return (
    <Shell>
    <main className="max-w-[1400px] mx-auto px-6 py-7">
      <header className="flex items-end justify-between mb-5">
        <div>
          <div className="flex items-center gap-3">
            <div className="w-2.5 h-7 bg-epsilon rounded-sm" />
            <h1 className="text-2xl font-bold tracking-tight">Customers</h1>
            <span className="flex items-center gap-1.5 text-xs text-emerald-400 ml-1"><span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" /> live</span>
          </div>
          <p className="text-slate-400 text-sm mt-1.5 ml-6">Every signed-in person, resolved to one CORE&nbsp;ID — click to see their live profile and full activity log.</p>
        </div>
        <button onClick={doReset} className="text-xs text-slate-400 border border-line rounded-md px-2.5 py-1.5 hover:bg-panel2 shrink-0">↺ Reset demo data</button>
      </header>

      {idSummary && (
        <section className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-5">
          <IdStat label="People resolved" value={`${idSummary.resolved}/${idSummary.people}`} sub="≥2 signals" accent="text-epsilon" />
          <IdStat label="Cross-device" value={`${idSummary.cross_device}`} sub="2+ devices, one ID" />
          <IdStat label="Signals unified" value={`${idSummary.signals_unified}`} sub={`avg ${idSummary.avg_signals}/person`} />
          <IdStat label="Guest sessions stitched" value={`${idSummary.stitched_sessions}`} sub={`${idSummary.stitched_people} merges`} accent="text-sure" />
          <IdStat label="Channels unified" value={`${Object.keys(idSummary.channels || {}).length}`} sub={Object.keys(idSummary.channels || {}).join(" · ") || "—"} />
        </section>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Left: people list */}
        <div className="card lg:col-span-1 p-0 overflow-hidden">
          <div className="card-title px-4 pt-4 flex items-center justify-between">
            <span>People</span>
            <span className="text-[10px] font-normal text-slate-500">{people.length} registered · {people.filter((p) => p.online).length} online</span>
          </div>
          <div className="mt-2 max-h-[640px] overflow-y-auto">
            {people.length === 0 ? (
              <p className="text-sm text-slate-500 p-6 text-center">No customers yet — sign in on the storefront and they appear here.</p>
            ) : people.map((p) => (
              <button key={p.core_id} onClick={() => setSel(p.core_id)}
                className={`w-full text-left px-4 py-3 border-l-2 transition ${sel === p.core_id ? "bg-panel2 border-epsilon" : "border-transparent hover:bg-panel2/50"}`}>
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-slate-100 text-sm flex items-center gap-2">
                    <span className={`w-1.5 h-1.5 rounded-full ${p.online ? "bg-emerald-400" : "bg-slate-600"}`} />
                    {p.name}
                  </span>
                  <span className="pill text-[9px]" style={{ background: (BUCKET_COLOR[p.segment] ?? "#64748b") + "22", color: BUCKET_COLOR[p.segment] ?? "#94a3b8" }}>{p.segment}</span>
                </div>
                <div className="flex items-center justify-between mt-1">
                  <span className="text-[10px] text-slate-500 font-mono">{p.core_id}</span>
                  <span className="text-[10px] text-slate-500">{p.events} events · {ago(p.last_seen)}</span>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Right: detail */}
        <div className="lg:col-span-2 space-y-5">
          {!selPerson ? (
            <div className="card text-center text-slate-500 py-16">Select a customer to view their profile and logs.</div>
          ) : (
            <>
              {ident && <IdentityGraph g={ident} />}
              <div className="card">
                <div className="flex items-start justify-between flex-wrap gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <h2 className="text-xl font-bold">{selPerson.name}</h2>
                      <span className="pill text-[10px]" style={{ background: (BUCKET_COLOR[selPerson.segment] ?? "#64748b") + "22", color: BUCKET_COLOR[selPerson.segment] ?? "#94a3b8" }}>{selPerson.segment}</span>
                      {selPerson.online && <span className="text-[10px] text-emerald-400 flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />online</span>}
                      {selPerson.consent === false
                        ? <span className="pill text-[9px] bg-amber-500/15 text-amber-300">⚠ personalisation off</span>
                        : <span className="pill text-[9px] bg-emerald-500/10 text-emerald-300">✓ consented</span>}
                    </div>
                    <div className="text-xs text-slate-500 mt-1">{selPerson.email} · <span className="font-mono">{selPerson.core_id}</span>{prof?.devices?.length ? ` · ${prof.devices.join(", ")}` : ""}</div>
                  </div>
                  <button onClick={() => remove(selPerson.core_id)}
                    className="text-xs text-rose-300 border border-rose-500/30 rounded-md px-2.5 py-1.5 hover:bg-rose-500/10 shrink-0">
                    🗑 Delete customer
                  </button>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mt-4">
                  <Metric label="Intent" value={`${prof?.intent_score ?? 0}`} />
                  <Metric label="Uplift" value={prof?.uplift != null ? `${(prof.uplift * 100).toFixed(1)}%` : "—"} accent={prof?.uplift > 0 ? "text-sure" : "text-lost"} />
                  <Metric label="Baseline" value={prof?.base_rate != null ? `${(prof.base_rate * 100).toFixed(0)}%` : "—"} />
                  <Metric label="Orders" value={`${selPerson.orders}`} />
                  <Metric label="Spent" value={fmtUSD(selPerson.revenue || 0)} accent="text-persuadable" />
                </div>
                {/* Recent products & per-product intent (the live consideration set) */}
                {prof?.interests?.length > 0 && (
                  <div className="mt-4">
                    <div className="text-[10px] uppercase tracking-widest text-slate-500 mb-2">Recently browsed · live intent</div>
                    <div className="space-y-1.5">
                      {prof.interests.map((it: any) => (
                        <div key={it.id} className="flex items-center gap-2">
                          <span className="text-base">{it.emoji}</span>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center justify-between">
                              <span className="text-xs text-slate-200 truncate">{it.name}</span>
                              <span className="text-[10px] text-slate-400 tabular-nums ml-2">{it.intent}</span>
                            </div>
                            <div className="h-1.5 bg-panel2 rounded-full overflow-hidden mt-0.5">
                              <div className="h-full" style={{ width: `${it.intent}%`, background: it.bought ? "#a855f7" : BUCKET_COLOR.Persuadable }} />
                            </div>
                          </div>
                          {it.bought ? <span className="text-[9px] px-1 rounded bg-violet-500/20 text-violet-300">bought</span>
                            : it.in_cart ? <span className="text-[9px] px-1 rounded bg-emerald-500/20 text-emerald-300">cart</span>
                            : it.in_wishlist ? <span className="text-[9px] px-1 rounded bg-rose-500/20 text-rose-300">wish</span>
                            : <span className="text-[9px] text-slate-500">{it.views}×</span>}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {drivers?.available && drivers.drivers?.length > 0 && (
                  <div className="mt-4">
                    <div className="text-[10px] uppercase tracking-widest text-slate-500 mb-1.5">
                      Why this decision — causal drivers <span className="text-slate-600 normal-case">· ablation on the uplift model</span>
                    </div>
                    <div className="space-y-1.5">
                      {drivers.drivers.map((d: any, i: number) => {
                        const pos = d.contribution_pp >= 0;
                        const peak = Math.abs(drivers.drivers[0].contribution_pp) || 1;
                        const mag = Math.min(100, (Math.abs(d.contribution_pp) / peak) * 100);
                        return (
                          <div key={i} className="flex items-center gap-2 text-xs">
                            <span className="w-44 truncate text-slate-300">{d.feature} <span className="text-slate-500">×{d.value}</span></span>
                            <div className="flex-1 h-1.5 bg-panel2 rounded-full overflow-hidden">
                              <div className="h-full" style={{ width: `${mag}%`, background: pos ? "#22c55e" : "#ef4444" }} />
                            </div>
                            <span className={`tabular-nums w-14 text-right ${pos ? "text-emerald-300" : "text-rose-300"}`}>{pos ? "+" : ""}{d.contribution_pp}pp</span>
                          </div>
                        );
                      })}
                    </div>
                    <p className="text-[10px] text-slate-600 mt-1.5">Each bar = how much that behaviour moves this shopper&apos;s incremental uplift — the model&apos;s own reasoning, not a rule.</p>
                  </div>
                )}

                {nba && (
                  <div className="mt-4 bg-panel2 border border-line rounded-xl p-3">
                    <div className="flex items-center justify-between gap-2">
                      <div className="text-[10px] uppercase tracking-widest text-epsilon">Kairos next best action</div>
                      <button onClick={() => sendMail(selPerson.core_id)} disabled={sending || selPerson.consent === false}
                        className="text-[11px] font-semibold px-2.5 py-1 rounded-md bg-epsilon/20 text-epsilon hover:bg-epsilon/30 disabled:opacity-40 shrink-0"
                        title={selPerson.consent === false ? "Customer opted out of personalisation" : "Send this targeted message to the customer's inbox"}>
                        {sending ? "Sending…" : "📧 Send mail"}
                      </button>
                    </div>
                    <div className="text-sm text-slate-200 mt-1">{nba.headline || nba.action || nba.title || "—"}{nba.channel ? ` · via ${nba.channel}` : ""}</div>
                    {(nba.message) && <div className="text-xs text-slate-400 mt-0.5">{nba.message}</div>}
                    {(nba.reason || nba.rationale || nba.why) && <div className="text-xs text-slate-500 mt-1">{nba.reason || nba.rationale || nba.why}</div>}
                  </div>
                )}

                {sentMail && (
                  <div className="mt-2 bg-emerald-500/10 border border-emerald-500/30 rounded-xl p-3">
                    <div className="text-xs text-emerald-300 font-semibold">✓ Sent to {sentMail.to || "the customer"} via {sentMail.channel} — it&apos;s in their inbox now.</div>
                    <div className="text-sm text-slate-200 mt-1">{sentMail.mail?.subject}</div>
                    <div className="text-xs text-slate-500">{sentMail.mail?.preview}</div>
                  </div>
                )}
                <div className="mt-3">
                  <button onClick={() => askStrategist(selPerson.core_id)} disabled={stratLoading}
                    className="text-xs font-semibold px-3 py-2 rounded-lg bg-epsilon/20 text-epsilon hover:bg-epsilon/30 disabled:opacity-50">
                    {stratLoading ? "Thinking…" : "🧠 Ask the AI Strategist about this customer"}
                  </button>
                  {strat && (
                    <div className="mt-2 bg-panel2 border border-epsilon/30 rounded-xl p-3">
                      {strat.decision && <div className="text-sm font-bold text-epsilon mb-1">{strat.decision}</div>}
                      <div className="text-sm text-slate-200 whitespace-pre-wrap leading-relaxed">{strat.narrative}</div>
                      <div className="text-[10px] text-slate-500 mt-1.5">
                        {strat.source === "openrouter" ? "✦ reasoned live by the LLM (OpenRouter)"
                          : strat.source === "claude" ? "✦ reasoned live by Claude"
                          : "✦ Kairos real-time behavioural analysis"}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                <div className="card">
                  <div className="card-title">Cart · {detail?.cart?.length ?? 0}</div>
                  {detail?.cart?.length ? detail.cart.map((c: any) => (
                    <div key={c.id} className="flex items-center justify-between text-sm py-1">
                      <span className="text-slate-300">{c.emoji} {c.name}</span>
                      <span className="text-slate-400">{fmtUSD(c.sale_price ?? c.price)}</span>
                    </div>
                  )) : <p className="text-sm text-slate-500 py-3">Empty cart.</p>}
                </div>
                <div className="card">
                  <div className="card-title">Orders · {detail?.orders?.length ?? 0}</div>
                  {detail?.orders?.length ? detail.orders.map((o: any) => (
                    <div key={o.order_id} className="flex items-center justify-between text-sm py-1">
                      <span className="text-slate-400 text-xs font-mono">{o.order_id}</span>
                      <span className="text-sure font-semibold">{fmtUSD(o.grand_total)}</span>
                    </div>
                  )) : <p className="text-sm text-slate-500 py-3">No orders yet.</p>}
                </div>
              </div>

              <div className="card">
                <div className="card-title flex items-center justify-between">
                  <span>Activity log</span>
                  <span className="text-[10px] font-normal text-slate-500">{selPerson.events} total events · live</span>
                </div>
                {events.length === 0 ? (
                  <p className="text-sm text-slate-500 py-4">No activity yet.</p>
                ) : (
                  <ol className="mt-2 space-y-1.5 max-h-[420px] overflow-y-auto">
                    {events.map((e, i) => (
                      <li key={i} className="flex items-center gap-3 text-sm border-b border-line/50 pb-1.5">
                        <span className="w-6 text-center">{EVENT_ICON[e.type] ?? "•"}</span>
                        <span className="text-slate-300 flex-1">
                          {e.type.replace(/_/g, " ")}
                          {e.product_id && <span className="text-slate-500"> · {prods[e.product_id] || e.product_id}</span>}
                          {e.meta?.message && <span className="text-slate-400 italic"> “{e.meta.message}”</span>}
                        </span>
                        {e.points_earned ? <span className="text-[10px] text-amber-300">+{e.points_earned}</span> : null}
                        <span className="text-[10px] text-slate-500 tabular-nums w-16 text-right">{ago(e.ts)}</span>
                      </li>
                    ))}
                  </ol>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </main>
    </Shell>
  );
}

function IdStat({ label, value, sub, accent }: { label: string; value: string; sub?: string; accent?: string }) {
  return (
    <div className="card !p-3">
      <div className="text-[10px] uppercase tracking-wider text-slate-500">{label}</div>
      <div className={`text-2xl font-bold tabular-nums ${accent ?? "text-slate-100"}`}>{value}</div>
      {sub && <div className="text-[10px] text-slate-500 truncate">{sub}</div>}
    </div>
  );
}

function IdentityGraph({ g }: { g: any }) {
  const devices = (g.devices ?? []).map((d: string) => ({ icon: d === "mobile" ? "📱" : d === "tablet" ? "📟" : "💻", label: d[0].toUpperCase() + d.slice(1) }));
  const CHAN_ICON: Record<string, string> = { Web: "🌐", Chatbot: "💬", Email: "📬" };
  const channels = (g.channels ?? []).map((c: string) => ({ icon: CHAN_ICON[c] ?? "🔗", label: c }));
  const merged = (g.merged_from ?? []).length > 0;
  return (
    <div className="card" style={{ background: "linear-gradient(180deg,rgba(230,0,90,0.05),transparent)" }}>
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="card-title mb-0 flex items-center gap-2">🔗 Identity Resolution <span className="text-[10px] font-normal text-slate-500">CORE&nbsp;ID graph</span></div>
        <span className="pill text-[10px] bg-epsilon/15 text-epsilon">1 person · resolved from {g.signal_count} signals</span>
      </div>

      {/* hub + spokes */}
      <div className="mt-4 flex flex-col items-center">
        <div className="text-center bg-ink border border-epsilon/40 rounded-2xl px-5 py-3 shadow-lg">
          <div className="text-[10px] uppercase tracking-widest text-epsilon">CORE ID</div>
          <div className="font-mono font-bold text-slate-100">{g.core_id}</div>
          <div className="text-xs text-slate-400">{g.name}{g.email ? ` · ${g.email}` : ""}</div>
        </div>
        <div className="w-px h-4 bg-line" />
        <div className="flex flex-wrap items-start justify-center gap-2">
          {g.signals.map((s: any, i: number) => (
            <div key={i} className="flex flex-col items-center">
              <div className="w-px h-3 bg-line" />
              <div className={`flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs border ${s.type === "email" ? "border-epsilon/40 bg-epsilon/10 text-epsilon" : s.type === "device" ? "border-sky-500/30 bg-sky-500/10 text-sky-300" : "border-violet-500/30 bg-violet-500/10 text-violet-300"}`}>
                <span>{s.icon}</span><span>{s.label}</span>
                <span className="text-[8px] uppercase tracking-wider opacity-60">{s.type}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-4 gap-2 mt-5 text-center">
        <Metric label="Devices" value={`${g.devices?.length ?? 0}`} />
        <Metric label="Channels" value={`${g.channels?.length ?? 0}`} />
        <Metric label="Sessions" value={`${g.sessions ?? 0}`} />
        <Metric label="Events" value={`${g.events ?? 0}`} />
      </div>

      {merged && (
        <div className="mt-3 text-xs text-emerald-300 bg-emerald-500/10 border border-emerald-500/30 rounded-lg px-3 py-2">
          ✓ Anonymous → known: stitched {g.merged_from.reduce((a: number, m: any) => a + (m.events || 0), 0)} guest event(s)
          {g.merged_sessions ? ` across ${g.merged_sessions} guest session(s)` : ""} into this CORE&nbsp;ID on sign-in.
        </div>
      )}
      <p className="text-[11px] text-slate-500 mt-2">One unified person resolved from {channels.length} channel(s) and {devices.length} device(s) — deterministic identity resolution, the foundation of seamless cross-channel journeys.</p>

      <div className="mt-3 border-t border-line pt-3">
        <div className="flex items-center justify-between">
          <span className="text-[10px] uppercase tracking-widest text-slate-500">🔒 Privacy &amp; consent ledger</span>
          {g.consent === false
            ? <span className="pill text-[9px] bg-amber-500/15 text-amber-300">⚠ opted out</span>
            : <span className="pill text-[9px] bg-emerald-500/15 text-emerald-300">✓ consented</span>}
        </div>
        {g.consent_log?.length ? (
          <ul className="mt-1.5 space-y-1">
            {g.consent_log.slice(0, 4).map((c: any, i: number) => (
              <li key={i} className="flex items-center justify-between text-[11px]">
                <span className={c.consent ? "text-emerald-300" : "text-amber-300"}>
                  {c.consent ? "✓ Consent granted" : "⛔ Consent withdrawn"}
                </span>
                <span className="text-slate-500 tabular-nums">{ago(c.ts)}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-[11px] text-slate-500 mt-1">Consented at sign-in · no changes. Every touch checks this first.</p>
        )}
        <p className="text-[10px] text-slate-600 mt-1.5">Privacy-safe CORE&nbsp;ID — outreach is suppressed the instant consent is withdrawn.</p>
      </div>
    </div>
  );
}

function Metric({ label, value, accent }: { label: string; value: string; accent?: string }) {
  return (
    <div className="bg-panel2 border border-line rounded-xl px-3 py-2.5">
      <div className="text-[10px] uppercase tracking-wider text-slate-500">{label}</div>
      <div className={`text-lg font-bold tabular-nums ${accent ?? "text-slate-100"}`}>{value}</div>
    </div>
  );
}
