"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, BUCKET_COLOR, Customer, fmtUSD, Segment } from "@/lib/api";
import { BanditChart, MarginalRoiChart, QiniChart, SegmentScatter } from "@/components/charts";

export default function Page() {
  const [segments, setSegments] = useState<Segment[]>([]);
  const [total, setTotal] = useState(0);
  const [scatter, setScatter] = useState<any[]>([]);
  const [qini, setQini] = useState<any>(null);
  const [alloc, setAlloc] = useState<any>(null);
  const [bandit, setBandit] = useState<any>(null);
  const [budget, setBudget] = useState(0);
  const [live, setLive] = useState<{ revenue: number; customers_targeted: number }>();
  const [picked, setPicked] = useState<Customer | null>(null);
  const [explain, setExplain] = useState<string>("");
  const [loadingExplain, setLoadingExplain] = useState(false);

  useEffect(() => {
    api.segments().then((d) => { setSegments(d.segments); setTotal(d.total_customers); });
    api.qini().then(setQini);
    api.bandit().then(setBandit);
    api.allocation().then((a) => { setAlloc(a); setBudget(a?.knee?.budget ?? 0); });
    // Sample points across buckets for the scatter.
    Promise.all(
      ["Persuadable", "Sure Thing", "Lost Cause", "Sleeping Dog"].map((b) =>
        api.customers(b, 80).then((r) => r.items)
      )
    ).then((groups) => setScatter(groups.flat()));
  }, []);

  useEffect(() => {
    if (budget > 0) api.allocate(budget).then(setLive);
  }, [budget]);

  async function pick(id: string) {
    setExplain(""); setLoadingExplain(true);
    const c = scatter.find((p) => p.customer_id === id);
    setPicked(c ?? null);
    const r = await api.explain(id);
    setExplain(r.explanation); setLoadingExplain(false);
  }

  const m = alloc?.restraint_metrics ?? {};
  const econ = alloc?.economics ?? {};
  const maxBudget = alloc?.curve?.length ? alloc.curve[alloc.curve.length - 1].budget : 100;
  const persuadablePct = segments.find((s) => s.bucket === "Persuadable")?.pct ?? 0;

  return (
    <main className="max-w-[1400px] mx-auto px-6 py-7">
      {/* Header */}
      <header className="flex items-end justify-between mb-6">
        <div>
          <div className="flex items-center gap-3">
            <div className="w-2.5 h-7 bg-epsilon rounded-sm" />
            <h1 className="text-2xl font-bold tracking-tight">Epsilon Conductor</h1>
          </div>
          <p className="text-slate-400 text-sm mt-1.5 ml-6">
            Causal marketing decisioning — spend only where it changes the outcome.
          </p>
        </div>
        <div className="text-right text-sm text-slate-400">
          <div className="mb-1">
            <Link href="/store" className="text-epsilon font-semibold hover:underline">▶ Live cross-device demo</Link>
          </div>
          <div><span className="text-slate-200 font-semibold tabular-nums">{total.toLocaleString()}</span> customers · Qini AUUC <span className="text-epsilon font-semibold">+{(qini?.auuc ?? 0).toFixed(3)}</span></div>
        </div>
      </header>

      {/* The three restraint metrics */}
      <section className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <Metric label="Revenue Generated" value={fmtUSD(m.revenue_generated ?? 0)}
          sub="targeting Persuadables" color="text-persuadable" />
        <Metric label="Budget Saved" value={fmtUSD(m.budget_saved ?? 0)}
          sub="not discounting Sure Things" color="text-sure" />
        <Metric label="Revenue Protected" value={fmtUSD(m.revenue_protected ?? 0)}
          sub="not annoying Sleeping Dogs" color="text-dog" />
        <Metric label="Total Business Impact" value={fmtUSD(m.total_impact ?? 0)}
          sub="same budget, better outcome" color="text-epsilon" highlight />
      </section>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Segment scatter */}
        <div className="card lg:col-span-2">
          <div className="card-title">Customer base — only {persuadablePct}% are Persuadable</div>
          <SegmentScatter points={scatter} onPick={pick} />
          <div className="flex flex-wrap gap-3 mt-3">
            {segments.map((s) => (
              <span key={s.bucket} className="flex items-center gap-1.5 text-xs text-slate-300">
                <span className="w-2.5 h-2.5 rounded-full" style={{ background: BUCKET_COLOR[s.bucket] }} />
                {s.bucket} <span className="text-slate-500">{s.pct}%</span>
              </span>
            ))}
          </div>
        </div>

        {/* Customer inspector + Claude explanation */}
        <div className="card">
          <div className="card-title">Decision Inspector {picked ? `· ${picked.customer_id}` : ""}</div>
          {!picked ? (
            <p className="text-sm text-slate-500 py-10 text-center">
              Click any point to see the decision and why.
            </p>
          ) : (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="pill" style={{ background: BUCKET_COLOR[picked.bucket] + "22", color: BUCKET_COLOR[picked.bucket] }}>
                  {picked.bucket}
                </span>
                <ActionBadge action={picked.action} />
              </div>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <Stat k="Baseline P(buy)" v={(picked.base_rate * 100).toFixed(1) + "%"} />
                <Stat k="Incremental lift" v={(picked.uplift * 100).toFixed(1) + "%"}
                  accent={picked.uplift > 0 ? "text-sure" : "text-lost"} />
                <Stat k="Inc. revenue" v={fmtUSD(picked.inc_revenue)} />
                <Stat k="Pref. channel" v={picked.channel} />
              </div>
              <div className="bg-panel2 border border-line rounded-xl p-3 text-sm text-slate-300 leading-relaxed min-h-[92px]">
                <div className="text-[10px] uppercase tracking-widest text-epsilon mb-1.5">🤖 Conductor explains</div>
                {loadingExplain ? <span className="text-slate-500">Reasoning…</span> : explain}
              </div>
            </div>
          )}
        </div>

        {/* Marginal ROI + budget slider */}
        <div className="card lg:col-span-2">
          <div className="flex items-center justify-between">
            <div className="card-title mb-0">Budget allocation — marginal ROI</div>
            <div className="text-sm text-slate-300">
              Budget <span className="text-epsilon font-semibold tabular-nums">{fmtUSD(budget)}</span>
              {live && <> → <span className="text-persuadable font-semibold">{fmtUSD(live.revenue)}</span> from <span className="tabular-nums">{live.customers_targeted.toLocaleString()}</span> customers</>}
            </div>
          </div>
          <MarginalRoiChart curve={alloc?.curve ?? []} knee={alloc?.knee} budget={budget} />
          <input type="range" min={0} max={maxBudget} step={maxBudget / 200} value={budget}
            onChange={(e) => setBudget(Number(e.target.value))}
            className="w-full mt-2 accent-epsilon" />
          <p className="text-xs text-slate-500 mt-1">
            The green knee is where each extra rupee stops paying for itself. Past it, you spend more to earn less.
          </p>
        </div>

        {/* Qini */}
        <div className="card">
          <div className="card-title">Qini curve — causal validation</div>
          <QiniChart data={qini ?? { x: [], y: [], auuc: 0 }} />
          <p className="text-xs text-slate-500 mt-1">
            Conductor front-loads real lift vs. random targeting. AUUC <span className="text-epsilon">+{(qini?.auuc ?? 0).toFixed(3)}</span>.
          </p>
        </div>

        {/* Bandit */}
        <div className="card lg:col-span-3">
          <div className="flex items-center justify-between">
            <div className="card-title mb-0">Channel orchestration — self-optimizing bandit</div>
            {bandit?.summary && (
              <div className="text-sm text-slate-300">
                <span className="text-sure font-semibold">+{bandit.summary.lift_vs_random_pct}%</span> vs random ·{" "}
                <span className="text-slate-400">{bandit.summary.pct_of_oracle}% of oracle ceiling</span>
              </div>
            )}
          </div>
          <BanditChart curve={bandit?.curve ?? []} />
          <p className="text-xs text-slate-500 mt-1">
            A Thompson-sampling bandit learns the best channel per segment online — the gap above Random is money the system earns by adapting.
          </p>
        </div>
      </div>

      <footer className="text-center text-xs text-slate-600 mt-8">
        Epsilon Conductor · EconML X-Learner · PuLP knapsack · Thompson bandit · Claude ·
        {econ?.basis === "measured" ? " measured on Hillstrom RCT" : " projected at scale"}
      </footer>
    </main>
  );
}

function Metric({ label, value, sub, color, highlight }: any) {
  return (
    <div className={`card ${highlight ? "ring-1 ring-epsilon/40" : ""}`}>
      <div className="card-title mb-1">{label}</div>
      <div className={`metric ${color}`}>{value}</div>
      <div className="text-xs text-slate-500 mt-1">{sub}</div>
    </div>
  );
}

function Stat({ k, v, accent }: { k: string; v: string; accent?: string }) {
  return (
    <div className="bg-panel2 border border-line rounded-lg px-3 py-2">
      <div className="text-[10px] uppercase tracking-wider text-slate-500">{k}</div>
      <div className={`font-semibold ${accent ?? "text-slate-100"}`}>{v}</div>
    </div>
  );
}

function ActionBadge({ action }: { action: string }) {
  const map: Record<string, string> = {
    TARGET: "bg-persuadable/20 text-persuadable",
    HOLD: "bg-slate-500/20 text-slate-300",
    SUPPRESS: "bg-dog/20 text-dog",
  };
  return <span className={`pill ${map[action] ?? "bg-slate-700 text-slate-200"}`}>{action}</span>;
}
