"use client";

import { useEffect, useState } from "react";
import { store, fmtUSD, BUCKET_COLOR } from "@/lib/api";
import { AgentPanel } from "@/components/agent-panel";
import { Shell } from "@/components/shell";

function buildReportHtml(r: any): string {
  const [summaryRaw, stepsRaw] = String(r.narrative || "").split(/NEXT STEPS:/i);
  const steps = (stepsRaw || "").split("\n").map((s: string) => s.trim()).filter(Boolean);
  const segRows = (r.segments || []).map((s: any) =>
    `<tr><td><b>${s.bucket}</b></td><td>${(s.count || 0).toLocaleString()} (${s.pct}%)</td><td>${(s.avg_uplift * 100).toFixed(1)}%</td><td>${fmtUSD(s.inc_revenue)}</td></tr>`).join("");
  const stepItems = steps.map((s: string) => `<li>${s.replace(/^\d+[\).\s]*/, "")}</li>`).join("");
  const recs = (r.live?.recommendations || []).map((x: any) => `<li><b>${x.title}</b> — ${x.detail} <i>(${x.impact})</i></li>`).join("");
  const b = r.benchmark || {};
  return `<!doctype html><html><head><meta charset="utf-8"><title>Kairos Strategy Report</title>
<style>
body{font-family:-apple-system,Segoe UI,Roboto,sans-serif;color:#1a2233;max-width:820px;margin:40px auto;padding:0 24px;line-height:1.55}
h1{font-size:28px;margin:0}.accent{color:#e6005a}
.sub{color:#667;margin:4px 0 24px}
h2{font-size:14px;text-transform:uppercase;letter-spacing:.5px;color:#e6005a;border-bottom:2px solid #f0d0dd;padding-bottom:6px;margin-top:30px}
table{width:100%;border-collapse:collapse;margin:8px 0}td,th{text-align:left;padding:8px;border-bottom:1px solid #eee;font-size:14px}
th{color:#889;font-size:11px;text-transform:uppercase}
.cards{display:flex;gap:12px;flex-wrap:wrap}.card{flex:1;min-width:140px;border:1px solid #eee;border-radius:10px;padding:12px}
.card .v{font-size:22px;font-weight:800;color:#e6005a}.card .l{font-size:11px;color:#889;text-transform:uppercase}
ul{padding-left:20px}li{margin:6px 0;font-size:14px}
.foot{margin-top:40px;color:#aab;font-size:12px;border-top:1px solid #eee;padding-top:12px}
@media print{body{margin:0}}
</style></head><body>
<h1><span class="accent">●</span> Kairos — Strategy Report</h1>
<div class="sub">Causal marketing decisioning · generated ${r.generated_at} · ${(r.total_customers || 0).toLocaleString()} customers</div>
<h2>Executive summary</h2>
<p>${(summaryRaw || "").trim().replace(/\n/g, "<br>")}</p>
<h2>Segment breakdown</h2>
<table><tr><th>Segment</th><th>Customers</th><th>Avg uplift</th><th>Incremental rev</th></tr>${segRows}</table>
<h2>Optimal spend &amp; measured impact</h2>
<div class="cards">
<div class="card"><div class="l">Optimal budget (knee)</div><div class="v">${fmtUSD(r.knee?.budget)}</div></div>
<div class="card"><div class="l">Customers funded</div><div class="v">${(r.knee?.customers || 0).toLocaleString()}</div></div>
<div class="card"><div class="l">Incremental revenue</div><div class="v">${fmtUSD(r.knee?.revenue)}</div></div>
</div>
<div class="cards" style="margin-top:12px">
<div class="card"><div class="l">vs Batch-and-blast</div><div class="v">+${b.net_revenue_pct}%</div><div class="l">net revenue</div></div>
<div class="card"><div class="l">Messages saved</div><div class="v">${Math.abs(b.messages_saved || 0).toLocaleString()}</div></div>
<div class="card"><div class="l">Spend saved</div><div class="v">${fmtUSD(b.spend_saved)}</div></div>
<div class="card"><div class="l">ROI</div><div class="v">${b.roi}&times;</div><div class="l">vs ${b.trad_roi}&times; traditional</div></div>
</div>
<h2>Live snapshot</h2>
<p>${r.live?.on_site || 0} shopper(s) on site now. Funnel: ${r.live?.funnel?.visitors || 0} visitors &rarr; ${r.live?.funnel?.carted || 0} carted &rarr; ${r.live?.funnel?.bought || 0} bought.</p>
${recs ? `<ul>${recs}</ul>` : ""}
<h2>Recommended next steps</h2>
<ul>${stepItems}</ul>
<div class="foot">Kairos · spend only where it changes the outcome · head-to-head is an illustrative simulation; bucket lift validated on the Hillstrom RCT.</div>
</body></html>`;
}

export default function StrategyPage() {
  const [s, setS] = useState<any>(null);
  const [bench, setBench] = useState<any>(null);
  const [benchLoading, setBenchLoading] = useState(false);
  const [dl, setDl] = useState(false);

  async function downloadReport() {
    setDl(true);
    const r = await store.report();
    setDl(false);
    if (!r) return;
    const blob = new Blob([buildReportHtml(r)], { type: "text/html" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `Kairos-Strategy-Report-${new Date().toISOString().slice(0, 10)}.html`;
    a.click();
    URL.revokeObjectURL(url);
  }

  useEffect(() => {
    const poll = () => store.strategy().then((d) => d && setS(d));
    poll();
    const t = setInterval(poll, 3000);
    return () => clearInterval(t);
  }, []);

  async function runBenchmark(seed = 42) {
    setBenchLoading(true);
    const b = await store.benchmark(64000, seed);
    if (b) setBench(b);
    setBenchLoading(false);
  }
  useEffect(() => { runBenchmark(42); }, []);

  const h = s?.headline ?? {};
  const f = s?.funnel ?? {};
  const segs = s?.segments ?? [];
  const recs = s?.recommendations ?? [];

  const funnelSteps = [
    { k: "Visitors", v: f.visitors ?? 0 },
    { k: "Browsed", v: f.browsed ?? 0 },
    { k: "Carted", v: f.carted ?? 0 },
    { k: "Bought", v: f.bought ?? 0 },
  ];
  const maxF = Math.max(1, ...funnelSteps.map((x) => x.v));

  const PRIORITY = { High: "bg-rose-500/20 text-rose-300", Medium: "bg-amber-500/20 text-amber-300", Low: "bg-slate-500/20 text-slate-300" } as Record<string, string>;

  return (
    <Shell>
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
        <div className="flex flex-col items-end gap-2">
          <button onClick={downloadReport} disabled={dl}
            className="text-xs font-semibold px-3 py-2 rounded-lg bg-epsilon/20 text-epsilon hover:bg-epsilon/30 disabled:opacity-50">
            {dl ? "Preparing…" : "⬇ Download strategy report"}
          </button>
          <span className="flex items-center gap-1.5 text-xs text-emerald-400"><span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" /> recomputed live</span>
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

      <AgentPanel />

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

      {/* Real-RCT validation — the credibility anchor (measured, not modelled) */}
      {bench?.validation && <RctValidation v={bench.validation} />}

      {/* Head-to-head benchmark — illustrative simulation */}
      <section className="card mt-6">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="card-title mb-0 flex items-center gap-2">Head-to-head benchmark
            <span className="pill text-[10px] bg-amber-500/15 text-amber-300 border border-amber-500/30">illustrative simulation</span>
            <span className="text-[10px] font-normal text-slate-500">· {bench ? `${bench.n.toLocaleString()} customers, seed ${bench.seed}` : "Traditional vs Kairos"}</span></div>
          <div className="flex gap-2">
            <button onClick={() => runBenchmark(42)} disabled={benchLoading} className="text-xs font-semibold px-3 py-1.5 rounded-lg border border-line hover:bg-panel2 disabled:opacity-50">{benchLoading ? "Running…" : "Re-run (seed 42)"}</button>
            <button onClick={() => runBenchmark(Math.floor(Math.random() * 9999))} disabled={benchLoading} className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-epsilon/20 text-epsilon hover:bg-epsilon/30 disabled:opacity-50">Random seed</button>
          </div>
        </div>
        <p className="text-xs text-slate-500 mt-1 mb-3">A seeded, reproducible simulation on the <span className="text-slate-300">same</span> customers (archetype response model) — directional, for the demo. The numbers <span className="text-slate-300">proven on real data</span> are in the panel above.</p>

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
              <BenchWorld title="✅ Kairos" tone="good" w={bench.conductor} />
            </div>
            <p className="text-xs text-slate-500 mt-3">Traditional blasts the top half by propensity (2 touches + blanket 20% off); Kairos sends one right-sized touch to Persuadables only, holds Sure Things, suppresses Sleeping Dogs.</p>
          </>
        ) : (
          <p className="text-sm text-slate-500 py-6 text-center">{benchLoading ? "Running benchmark…" : "Benchmark unavailable."}</p>
        )}
      </section>

      <footer className="text-center text-xs text-slate-600 mt-8">
        Strategy recomputed live from the connected storefront · spend only where it changes the outcome.
      </footer>
    </main>
    </Shell>
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

function RctValidation({ v }: { v: any }) {
  const COLOR: Record<string, string> = {
    Persuadable: "#3b82f6", "Sure Thing": "#22c55e", "Sleeping Dog": "#f59e0b", "Lost Cause": "#ef4444",
  };
  // The action is the thesis; the pp lift is the real evidence behind it. We deliberately
  // avoid relative-% (a tiny base inflates it and invites "then why not market to them?").
  const ACTION: Record<string, { verb: string; good: boolean }> = {
    Persuadable: { verb: "Spend here — incremental", good: true },
    "Sure Thing": { verb: "Hold — buys anyway", good: false },
    "Sleeping Dog": { verb: "Suppress — contact backfires", good: false },
    "Lost Cause": { verb: "Skip — too small to fund", good: false },
  };
  return (
    <section className="card mt-6 border border-emerald-500/30">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="card-title mb-0 flex items-center gap-2">Validated on a real randomized experiment
          <span className="pill text-[10px] bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">measured, not modelled</span>
        </div>
        <span className="text-[10px] text-slate-500">{v.source} · {v.n_customers.toLocaleString()} customers ({v.n_treated.toLocaleString()} treated / {v.n_control.toLocaleString()} control)</span>
      </div>
      <p className="text-xs text-slate-500 mt-1 mb-3">
        Conversion when contacted vs. a held-out control group, straight from the experiment — no assumptions.
        The four buckets aren&apos;t a story; they&apos;re visible in the raw treated-minus-control lift.
      </p>
      <div className="text-[11px] text-emerald-300/90 bg-emerald-500/5 border border-emerald-500/20 rounded-lg px-3 py-2 mb-3">
        🧪 <b>Always-on holdout:</b> that control group isn&apos;t a one-off — in production a small slice of every
        segment stays held out, so Kairos keeps <b>measuring true incremental lift</b> and never drifts into vanity metrics.
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        {v.buckets.map((b: any) => (
          <div key={b.bucket} className="bg-panel2 border border-line rounded-xl p-3" style={{ borderTop: `3px solid ${COLOR[b.bucket]}` }}>
            <div className="flex items-center justify-between">
              <span className="font-bold text-sm" style={{ color: COLOR[b.bucket] }}>{b.bucket}</span>
              <span className={`text-[10px] font-bold ${b.marketing_helps ? "text-emerald-300" : "text-rose-300"}`}>
                {b.abs_uplift_pp > 0 ? "+" : ""}{b.abs_uplift_pp}pp
              </span>
            </div>
            <div className="flex items-end gap-3 mt-2 text-xs">
              <div><div className="text-slate-500 text-[10px]">contacted</div><div className="tabular-nums font-semibold text-slate-100">{b.treated_conv_pct}%</div></div>
              <div><div className="text-slate-500 text-[10px]">control</div><div className="tabular-nums font-semibold text-slate-400">{b.control_conv_pct}%</div></div>
            </div>
            <div className={`text-[11px] mt-2 font-semibold ${b.bucket === "Persuadable" ? "text-emerald-400" : b.bucket === "Sleeping Dog" ? "text-rose-400" : "text-slate-400"}`}>
              → {ACTION[b.bucket]?.verb ?? (b.marketing_helps ? "marketing helps" : "marketing hurts")}
            </div>
          </div>
        ))}
      </div>

      <div className="bg-rose-500/5 border border-rose-500/30 rounded-xl px-4 py-3 text-sm">
        <span className="font-semibold text-rose-300">The proof restraint pays:</span>{" "}
        <span className="text-slate-300">
          In this real experiment, contacting <b>Sleeping Dogs</b> cut their conversion by{" "}
          <b className="text-rose-300">{Math.abs(v.headline.sleeping_dog_abs_uplift_pp)}pp</b> — every message there
          destroyed organic revenue. Meanwhile marketing lifted <b>Persuadables</b> by{" "}
          <b className="text-emerald-300">{v.headline.persuadable_rel_lift_pct}%</b>. Spend on one, suppress the other —
          and now it&apos;s measured, not asserted.
        </span>
      </div>
    </section>
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
