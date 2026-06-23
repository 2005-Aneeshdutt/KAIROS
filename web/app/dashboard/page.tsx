"use client";

import { useEffect, useState } from "react";
import { api, store, BUCKET_COLOR, Customer, fmtUSD, Segment } from "@/lib/api";
import { BanditChart, MarginalRoiChart, QiniChart, SegmentScatter } from "@/components/charts";
import { AgentPanel } from "@/components/agent-panel";
import { Shell } from "@/components/shell";
import { useLiveData } from "@/lib/use-live";

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
  const [liveAnalytics, setLiveAnalytics] = useState<any>(null);
  const [liveShoppers, setLiveShoppers] = useState<any>(null);

  useEffect(() => {
    api.segments().then((d) => { setSegments(d.segments); setTotal(d.total_customers); });
    api.qini().then(setQini);
    api.bandit().then(setBandit);
    api.allocation().then((a) => { setAlloc(a); setBudget(a?.knee?.budget ?? 0); });

    Promise.all(
      ["Persuadable", "Sure Thing", "Lost Cause", "Sleeping Dog"].map((b) =>
        api.customers(b, 80).then((r) => r.items)
      )
    ).then((groups) => setScatter(groups.flat()));
  }, []);

  useEffect(() => {
    const poll = () => store.analytics().then((a) => a && setLiveAnalytics(a));
    poll();
    const t = setInterval(poll, 3000);
    return () => clearInterval(t);
  }, []);

  useLiveData<any>("/live-customers", (d) => d && setLiveShoppers(d));

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

  const liveRev = liveAnalytics?.revenue?.gross ?? 0;
  const revenueGenerated = (m.revenue_generated ?? 0) + liveRev;
  const totalImpact = (m.total_impact ?? 0) + liveRev;

  return (
    <Shell>
    <main className="max-w-[1400px] mx-auto px-6 py-7">

      <header className="flex items-end justify-between mb-6">
        <div>
          <div className="flex items-center gap-3">
            <div className="w-2.5 h-7 bg-epsilon rounded-sm" />
            <h1 className="text-2xl font-bold tracking-tight">Kairos</h1>
          </div>
          <p className="text-slate-400 text-sm mt-1.5 ml-6">
            Causal marketing decisioning — spend only where it changes the outcome.
          </p>
        </div>
        <div className="text-right text-sm text-slate-400">
          <div><span className="text-slate-200 font-semibold tabular-nums">{total.toLocaleString()}</span> customers · Qini AUUC <span className="text-epsilon font-semibold">+{(qini?.auuc ?? 0).toFixed(3)}</span></div>
        </div>
      </header>

      <section className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <Metric label="Revenue Generated" value={fmtUSD(revenueGenerated)}
          sub={liveRev > 0 ? `incl. ${fmtUSD(liveRev)} live store revenue` : "targeting Persuadables"} color="text-persuadable" live={liveRev > 0} />
        <Metric label="Budget Saved" value={fmtUSD(m.budget_saved ?? 0)}
          sub="not discounting Sure Things" color="text-sure" />
        <Metric label="Revenue Protected" value={fmtUSD(m.revenue_protected ?? 0)}
          sub="not annoying Sleeping Dogs" color="text-dog" />
        <Metric label="Total Business Impact" value={fmtUSD(totalImpact)}
          sub="same budget, better outcome" color="text-epsilon" highlight />
      </section>

      <AgentPanel hero />

      {liveAnalytics && liveAnalytics.funnel?.visitors > 0 && (
        <section className="card mb-6">
          <div className="flex items-center justify-between mb-3">
            <div className="card-title mb-0 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" /> Live storefront activity
            </div>
            <span className="text-xs text-slate-500">real-time · from the connected store</span>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <LiveStat label="Revenue (live)" value={fmtUSD(liveAnalytics.revenue?.gross ?? 0)} accent="text-persuadable" />
            <LiveStat label="Orders" value={`${liveAnalytics.revenue?.orders ?? 0}`} />
            <LiveStat label="AOV" value={fmtUSD(liveAnalytics.revenue?.aov ?? 0)} />
            <LiveStat label="Revenue at risk" value={fmtUSD(liveAnalytics.revenue_at_risk ?? 0)} accent="text-dog" sub="abandoned carts" />
            <LiveStat label="Incentive given" value={fmtUSD(liveAnalytics.revenue?.incentive_given ?? 0)} sub="discounts" />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
            <div>
              <div className="text-[10px] uppercase tracking-widest text-slate-500 mb-1.5">Funnel</div>
              <div className="flex items-center gap-2 text-sm">
                {[["Visitors", liveAnalytics.funnel.visitors], ["Browsed", liveAnalytics.funnel.browsed], ["Carted", liveAnalytics.funnel.carted], ["Bought", liveAnalytics.funnel.bought]].map(([k, v], i, arr) => (
                  <div key={k as string} className="flex items-center gap-2">
                    <div className="bg-panel2 border border-line rounded-lg px-3 py-1.5 text-center">
                      <div className="font-bold tabular-nums">{v as any}</div>
                      <div className="text-[9px] uppercase tracking-wider text-slate-500">{k as string}</div>
                    </div>
                    {i < arr.length - 1 && <span className="text-slate-600">→</span>}
                  </div>
                ))}
              </div>
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-widest text-slate-500 mb-1.5">Live segment mix</div>
              <div className="flex flex-wrap gap-2">
                {Object.entries(liveAnalytics.buckets ?? {}).map(([b, n]) => (
                  <span key={b} className="flex items-center gap-1.5 text-xs text-slate-300 bg-panel2 border border-line rounded-full px-2.5 py-1">
                    <span className="w-2 h-2 rounded-full" style={{ background: BUCKET_COLOR[b] ?? "#64748b" }} />
                    {b} <span className="text-slate-500 tabular-nums">{n as any}</span>
                  </span>
                ))}
                {(liveAnalytics.top_products ?? []).length > 0 && (
                  <span className="text-xs text-slate-500 ml-1">· hot: {liveAnalytics.top_products.slice(0, 3).map((p: any) => p.emoji).join(" ")}</span>
                )}
              </div>
            </div>
          </div>
        </section>
      )}

      <LiveShoppers data={liveShoppers} />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">

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
                <div className="text-[10px] uppercase tracking-widest text-epsilon mb-1.5">🤖 Kairos explains</div>
                {loadingExplain ? <span className="text-slate-500">Reasoning…</span> : explain}
              </div>
            </div>
          )}
        </div>

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

        <div className="card">
          <div className="card-title">Qini curve — causal validation</div>
          <QiniChart data={qini ?? { x: [], y: [], auuc: 0 }} />
          <p className="text-xs text-slate-500 mt-1">
            Kairos front-loads real lift vs. random targeting. AUUC <span className="text-epsilon">+{(qini?.auuc ?? 0).toFixed(3)}</span>.
          </p>
        </div>

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
        Kairos · EconML X-Learner · PuLP knapsack · Thompson bandit · OpenRouter LLM ·
        {econ?.basis === "measured" ? " measured on Hillstrom RCT" : " projected at scale"}
      </footer>
    </main>
    </Shell>
  );
}

function Metric({ label, value, sub, color, highlight, live }: any) {
  return (
    <div className={`card ${highlight ? "ring-1 ring-epsilon/40" : ""}`}>
      <div className="card-title mb-1 flex items-center gap-1.5">{label}{live && <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />}</div>
      <div className={`metric ${color}`}>{value}</div>
      <div className="text-xs text-slate-500 mt-1">{sub}</div>
    </div>
  );
}

function LiveStat({ label, value, accent, sub }: { label: string; value: string; accent?: string; sub?: string }) {
  return (
    <div className="bg-panel2 border border-line rounded-xl px-3 py-2.5">
      <div className="text-[10px] uppercase tracking-wider text-slate-500">{label}</div>
      <div className={`text-xl font-bold tabular-nums ${accent ?? "text-slate-100"}`}>{value}</div>
      {sub && <div className="text-[10px] text-slate-500">{sub}</div>}
    </div>
  );
}

function LiveShoppers({ data }: { data: any }) {
  const shoppers: any[] = data?.shoppers ?? [];
  const active = data?.active_count ?? 0;
  return (
    <section className="card mb-6">
      <div className="flex items-center justify-between mb-3">
        <div className="card-title mb-0 flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" /> Live shoppers — who&apos;s on the site now
        </div>
        <span className="text-xs text-slate-400">
          <span className="text-emerald-400 font-semibold tabular-nums">{active}</span> active · {shoppers.length} tracked
        </span>
      </div>
      {shoppers.length === 0 ? (
        <p className="text-sm text-slate-500 py-6 text-center">
          No shoppers yet — open the{" "}
          <a className="text-epsilon hover:underline" href="/store" target="_blank" rel="noreferrer">storefront</a>{" "}
          in another tab (or share the link with someone) and activity shows up here live.
        </p>
      ) : (
        <div className="overflow-hidden rounded-xl border border-line">
          <table className="w-full text-sm">
            <thead className="bg-panel2 text-[10px] uppercase tracking-wider text-slate-500">
              <tr>
                <th className="text-left font-medium px-3 py-2">Shopper</th>
                <th className="text-left font-medium px-3 py-2">Segment</th>
                <th className="text-left font-medium px-3 py-2">Intent</th>
                <th className="text-right font-medium px-3 py-2">Events</th>
                <th className="text-left font-medium px-3 py-2">Looking at</th>
                <th className="text-right font-medium px-3 py-2">Last seen</th>
              </tr>
            </thead>
            <tbody>
              {shoppers.slice(0, 12).map((s: any) => (
                <tr key={s.uid} className={`border-t border-line ${s.active ? "" : "opacity-50"}`}>
                  <td className="px-3 py-2 font-mono text-xs text-slate-300">
                    <span className={`inline-block w-1.5 h-1.5 rounded-full mr-2 ${s.active ? "bg-emerald-400" : "bg-slate-600"}`} />
                    {s.uid}{s.devices?.length > 1 && <span className="text-slate-500"> · {s.devices.length} dev</span>}
                  </td>
                  <td className="px-3 py-2">
                    <span className="pill text-[10px]" style={{ background: (BUCKET_COLOR[s.bucket] ?? "#64748b") + "22", color: BUCKET_COLOR[s.bucket] ?? "#94a3b8" }}>{s.bucket}</span>
                  </td>
                  <td className="px-3 py-2 w-28">
                    <div className="h-1.5 bg-panel2 rounded-full overflow-hidden">
                      <div className="h-full bg-epsilon" style={{ width: `${Math.min(s.intent_score ?? 0, 100)}%` }} />
                    </div>
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums text-slate-300">{s.events}</td>
                  <td className="px-3 py-2 text-slate-400 text-xs">{s.top_product ?? "—"}</td>
                  <td className="px-3 py-2 text-right text-xs text-slate-500 tabular-nums">{(s.seconds_ago ?? 0) <= 2 ? "now" : `${s.seconds_ago}s ago`}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
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
