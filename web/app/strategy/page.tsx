"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { store, fmtUSD, BUCKET_COLOR } from "@/lib/api";

export default function StrategyPage() {
  const [s, setS] = useState<any>(null);
  const [bench, setBench] = useState<any>(null);
  const [benchLoading, setBenchLoading] = useState(false);

  useEffect(() => {
    const poll = () => store.strategy().then((d) => d && setS(d));
    poll();
    const t = setInterval(poll, 3000);
    return () => clearInterval(t);
  }, []);

  async function runBenchmark(seed = 42) {
    setBenchLoading(true);
    const b = await store.benchmark(5000, seed);
    if (b) setBench(b);
    setBenchLoading(false);
  }
  useEffect(() => { runBenchmark(42); }, []);

  const h = s?.headline ?? {};
  const f = s?.funnel ?? {};
  const segs = s?.segments ?? [];
  const recs = s?.recommendations ?? [];
  const channels = s?.channels ?? [];

  const funnelSteps = [
    { k: "Visitors", v: f.visitors ?? 0 },
    { k: "Browsed", v: f.browsed ?? 0 },
    { k: "Carted", v: f.carted ?? 0 },
    { k: "Bought", v: f.bought ?? 0 },
  ];
  const maxF = Math.max(1, ...funnelSteps.map((x) => x.v));

  const PRIORITY = { High: "bg-rose-500/20 text-rose-300", Medium: "bg-amber-500/20 text-amber-300", Low: "bg-slate-500/20 text-slate-300" } as Record<string, string>;
  const KIND = { "on-site": "text-emerald-300", "off-site": "text-sky-300", ambient: "text-violet-300", "in-store": "text-amber-300" } as Record<string, string>;

  return (
    <main className="max-w-[1300px] mx-auto px-6 py-7">
      <header className="flex items-end justify-between mb-6">
        <div>
          <div className="flex items-center gap-3">
            <div className="w-2.5 h-7 bg-epsilon rounded-sm" />
            <h1 className="text-2xl font-bold tracking-tight">Marketing Strategy</h1>
            <span className="flex items-center gap-1.5 text-xs text-emerald-400 ml-1"><span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" /> live</span>
          </div>
          <p className="text-slate-400 text-sm mt-1.5 ml-6">How to market to each shopper — data-backed, computed live from who's in the store right now.</p>
        </div>
        <div className="flex gap-4 text-sm">
          <Link href="/" className="text-slate-400 hover:text-white">← Dashboard</Link>
          <Link href="/store" className="text-epsilon font-semibold hover:underline">Storefront →</Link>
        </div>
      </header>

      {/* Headline stats */}
      <section className="grid grid-cols-2 md:grid-cols-6 gap-3 mb-6">
        <Stat label="Visitors" value={`${h.visitors ?? 0}`} />
        <Stat label="Buyers" value={`${h.buyers ?? 0}`} accent="text-persuadable" />
        <Stat label="Conversion" value={`${h.conversion_pct ?? 0}%`} />
        <Stat label="Revenue" value={fmtUSD(h.revenue ?? 0)} accent="text-sure" live />
        <Stat label="Revenue at risk" value={fmtUSD(h.revenue_at_risk ?? 0)} accent="text-dog" sub="abandoned bags" />
        <Stat label="Margin right-sized" value={fmtUSD(h.margin_right_sized ?? 0)} accent="text-epsilon" sub={h.avg_discount_depth != null ? `avg dose ${h.avg_discount_depth}% vs flat 20%` : "Minimum Effective Dose"} />
      </section>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Funnel */}
        <div className="card lg:col-span-1">
          <div className="card-title">Conversion funnel</div>
          <div className="space-y-2 mt-2">
            {funnelSteps.map((x, i) => (
              <div key={x.k}>
                <div className="flex justify-between text-xs text-slate-400 mb-1"><span>{x.k}</span><span className="tabular-nums text-slate-200">{x.v}</span></div>
                <div className="h-3 bg-panel2 rounded-full overflow-hidden">
                  <div className="h-full bg-epsilon/70" style={{ width: `${(x.v / maxF) * 100}%` }} />
                </div>
                {i < funnelSteps.length - 1 && (
                  <div className="text-[10px] text-slate-500 text-right mt-0.5">
                    {i === 0 ? "" : ""}
                    {i === 1 && `${f.browse_to_cart_pct ?? 0}% browse→cart`}
                    {i === 2 && `${f.cart_to_buy_pct ?? 0}% cart→buy`}
                  </div>
                )}
              </div>
            ))}
          </div>
          <p className="text-xs text-slate-500 mt-3">The drop-off between Carted and Bought is the abandoned-cart opportunity — {fmtUSD(h.revenue_at_risk ?? 0)} sitting in bags.</p>
        </div>

        {/* Recommendations */}
        <div className="card lg:col-span-2">
          <div className="card-title">Recommended plays <span className="text-[10px] font-normal text-slate-500">· prioritised by impact</span></div>
          {recs.length === 0 ? (
            <p className="text-sm text-slate-500 py-6 text-center">No shoppers yet — open the storefront and browse to populate the strategy.</p>
          ) : (
            <div className="space-y-2.5 mt-1">
              {recs.map((r: any, i: number) => (
                <div key={i} className="bg-panel2 border border-line rounded-xl p-3">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-slate-100 text-sm">{r.title}</span>
                    <span className={`pill text-[10px] ${PRIORITY[r.priority] ?? PRIORITY.Low}`}>{r.priority}</span>
                  </div>
                  <p className="text-xs text-slate-400 mt-1">{r.detail}</p>
                  <div className="text-[11px] text-epsilon font-semibold mt-1.5">→ {r.impact}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Segment playbook */}
      <section className="mt-6">
        <div className="card-title mb-2">The segment playbook — what to do, and why</div>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
          {segs.map((seg: any) => (
            <div key={seg.segment} className="card" style={{ borderTop: `3px solid ${seg.color}` }}>
              <div className="flex items-center justify-between">
                <span className="font-bold" style={{ color: seg.color }}>{seg.segment}</span>
                <span className="text-xs text-slate-400 tabular-nums">{seg.count} · {seg.pct}%</span>
              </div>
              <div className="text-sm font-semibold text-slate-100 mt-1">{seg.action}</div>
              <Row k="Channel" v={seg.channel} />
              <Row k="Discount" v={seg.discount} />
              <Row k="Message" v={seg.message} />
              <div className="text-[11px] text-slate-500 mt-2 border-t border-line pt-2">🧠 {seg.why}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Channel strategy */}
      <section className="mt-6 card">
        <div className="card-title">Channel strategy — the orchestration portfolio</div>
        <p className="text-xs text-slate-500 mb-3">Conductor picks from {channels.length} channels by context (cost × immediacy × timing). On-site we nudge in-app for free; off-site channels only fire once the shopper leaves.</p>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2">
          {channels.map((c: any) => (
            <div key={c.channel} className="bg-panel2 border border-line rounded-lg px-3 py-2 flex items-center justify-between">
              <div>
                <div className="text-sm font-semibold text-slate-100">{c.icon} {c.channel}</div>
                <div className={`text-[10px] ${KIND[c.kind] ?? "text-slate-400"}`}>{c.kind}</div>
              </div>
              <div className="text-right">
                <div className="text-[11px] text-slate-400 tabular-nums">${c.cost}</div>
                <div className="text-[9px] text-slate-500">immediacy {c.immediacy}/5</div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Head-to-head benchmark — reproducible proof of superiority */}
      <section className="card mt-6">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="card-title mb-0">Head-to-head benchmark <span className="text-[10px] font-normal text-slate-500">· {bench ? `${bench.n.toLocaleString()} customers, seed ${bench.seed}` : "Traditional vs Conductor"}</span></div>
          <div className="flex gap-2">
            <button onClick={() => runBenchmark(42)} disabled={benchLoading} className="text-xs font-semibold px-3 py-1.5 rounded-lg border border-line hover:bg-panel2 disabled:opacity-50">{benchLoading ? "Running…" : "Re-run (seed 42)"}</button>
            <button onClick={() => runBenchmark(Math.floor(Math.random() * 9999))} disabled={benchLoading} className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-epsilon/20 text-epsilon hover:bg-epsilon/30 disabled:opacity-50">Random seed</button>
          </div>
        </div>
        <p className="text-xs text-slate-500 mt-1 mb-3">Both strategies run on the <span className="text-slate-300">same</span> customers with the same response model — reproducible, not cherry-picked.</p>

        {bench ? (
          <>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
              <BenchDelta label="Net revenue" value={`+${fmtUSD(bench.deltas.net_revenue)}`} sub={`+${bench.deltas.net_revenue_pct}% vs Traditional`} />
              <BenchDelta label="Messages saved" value={`${bench.deltas.messages_saved.toLocaleString()}`} sub={`${Math.abs(bench.deltas.messages_saved_pct)}% fewer sends`} />
              <BenchDelta label="Discount saved" value={fmtUSD(bench.deltas.discount_saved)} sub="margin not given away" />
              <BenchDelta label="ROI multiple" value={`${bench.deltas.roi_multiple}×`} sub="return per $ spent" />
            </div>
            <div className="grid md:grid-cols-2 gap-3">
              <BenchWorld title="🚫 Traditional" tone="bad" w={bench.traditional} />
              <BenchWorld title="✅ Conductor" tone="good" w={bench.conductor} />
            </div>
            <p className="text-xs text-slate-500 mt-3">Traditional blasts the top half by propensity (2 touches + blanket 20% off); Conductor sends one right-sized touch to Persuadables only, holds Sure Things, suppresses Sleeping Dogs.</p>
          </>
        ) : (
          <p className="text-sm text-slate-500 py-6 text-center">{benchLoading ? "Running benchmark…" : "Benchmark unavailable."}</p>
        )}
      </section>

      <footer className="text-center text-xs text-slate-600 mt-8">
        Strategy recomputed live from the connected storefront · spend only where it changes the outcome.
      </footer>
    </main>
  );
}

function Stat({ label, value, accent, sub, live }: { label: string; value: string; accent?: string; sub?: string; live?: boolean }) {
  return (
    <div className="card">
      <div className="card-title mb-1 flex items-center gap-1.5">{label}{live && <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />}</div>
      <div className={`text-2xl font-bold tabular-nums ${accent ?? "text-slate-100"}`}>{value}</div>
      {sub && <div className="text-[10px] text-slate-500 mt-0.5">{sub}</div>}
    </div>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="mt-2">
      <div className="text-[10px] uppercase tracking-wider text-slate-500">{k}</div>
      <div className="text-xs text-slate-300">{v}</div>
    </div>
  );
}

function BenchDelta({ label, value, sub }: { label: string; value: string; sub: string }) {
  return (
    <div className="bg-epsilon/5 border border-epsilon/30 rounded-xl px-3 py-2.5">
      <div className="text-[10px] uppercase tracking-wider text-slate-500">{label}</div>
      <div className="text-xl font-bold text-epsilon tabular-nums">{value}</div>
      <div className="text-[10px] text-slate-500">{sub}</div>
    </div>
  );
}

function BenchWorld({ title, tone, w }: { title: string; tone: "good" | "bad"; w: any }) {
  const ring = tone === "good" ? "border-emerald-500/30 bg-emerald-500/5" : "border-rose-500/30 bg-rose-500/5";
  const c = tone === "good" ? "text-emerald-300" : "text-rose-300";
  const rows: [string, any][] = [
    ["Net revenue", `$${Math.round(w.net).toLocaleString()}`],
    ["Conversion rate", `${w.conv_rate}%`],
    ["Messages sent", w.touches.toLocaleString()],
    ["Discount given", `$${Math.round(w.discount).toLocaleString()}`],
    ["Unsubscribes", w.unsubscribes.toLocaleString()],
    ["ROI (net per $ spent)", w.roi != null ? `${w.roi}×` : "—"],
  ];
  return (
    <div className={`rounded-xl p-4 border ${ring}`}>
      <div className="font-semibold text-sm mb-2">{title}</div>
      {rows.map(([k, v]) => (
        <div key={k} className="flex items-center justify-between py-0.5 text-sm">
          <span className="text-slate-500 text-xs">{k}</span>
          <span className={`font-bold tabular-nums ${c}`}>{v}</span>
        </div>
      ))}
    </div>
  );
}
