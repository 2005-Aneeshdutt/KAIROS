from __future__ import annotations

import json
import time
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
import asyncio

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

import simulate as sim
import tracking as trk

ART = Path(__file__).resolve().parents[1] / "ml" / "artifacts"

app = FastAPI(title="Kairos API", version="0.1.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

BUCKET_ACTION = {
    "Persuadable": ("TARGET", "High incremental lift — spend here."),
    "Sure Thing": ("HOLD", "Buys anyway — marketing is wasted spend."),
    "Lost Cause": ("HOLD", "Won't convert regardless — don't waste budget."),
    "Sleeping Dog": ("SUPPRESS", "Marketing backfires — actively leave alone."),
}

@lru_cache(maxsize=1)
def scores() -> pd.DataFrame:
    f = ART / "scores.parquet"
    if not f.exists():
        raise HTTPException(503, "scores.parquet missing — run `python -m src.uplift`")
    return pd.read_parquet(f)

@lru_cache(maxsize=1)
def allocation() -> dict:
    f = ART / "allocation.json"
    if not f.exists():
        raise HTTPException(503, "allocation.json missing — run `python -m src.allocate`")
    return json.loads(f.read_text())

@lru_cache(maxsize=1)
def qini() -> dict:
    return json.loads((ART / "qini.json").read_text())

@lru_cache(maxsize=1)
def bandit() -> dict:
    f = ART / "bandit.json"
    if not f.exists():
        raise HTTPException(503, "bandit.json missing — run `python -m src.bandit`")
    return json.loads(f.read_text())

@app.get("/health")
def health():
    import db
    return {"status": "ok", "persistence": db.backend(),
            "live_model": trk.live_model_loaded(),
            "artifacts": [p.name for p in ART.glob("*")]}

@app.get("/segments")
def segments():
    df = scores()
    out = []
    for bucket, g in df.groupby("bucket"):
        action, why = BUCKET_ACTION.get(bucket, ("?", ""))
        out.append({
            "bucket": bucket,
            "count": int(len(g)),
            "pct": round(100 * len(g) / len(df), 1),
            "avg_uplift": round(float(g["uplift"].mean()), 4),
            "avg_base_rate": round(float(g["base_rate"].mean()), 4),
            "inc_revenue": round(float(g["inc_revenue"].sum()), 2),
            "action": action,
            "rationale": why,
        })
    return {"total_customers": int(len(df)), "segments": out}

@app.get("/customers")
def customers(
    bucket: str | None = None,
    limit: int = Query(100, le=2000),
    offset: int = 0,
):
    df = scores()
    if bucket:
        df = df[df["bucket"] == bucket]
    page = df.iloc[offset:offset + limit]
    return {"total": int(len(df)), "items": _rows(page)}

@app.get("/customers/{customer_id}")
def customer(customer_id: str):
    df = scores()
    row = df[df["customer_id"] == customer_id]
    if row.empty:
        raise HTTPException(404, f"no customer {customer_id}")
    return _rows(row)[0]

@app.get("/qini")
def qini_endpoint():
    return qini()

@app.get("/allocation")
def allocation_endpoint():
    return allocation()

class AllocateReq(BaseModel):
    budget: float

@app.get("/bandit")
def bandit_endpoint():
    return bandit()

@app.get("/simulate/stream")
async def simulate_stream(
    sample_size: int = Query(4000, le=20000),
    ticks: int = Query(40, ge=5, le=120),
    delay_ms: int = Query(220, ge=0, le=2000),
    seed: int | None = None,
):
    async def gen():
        for event in sim.run_simulation(sample_size=sample_size, ticks=ticks, seed=seed):
            yield sim.sse_format(event)
            if event.get("type") == "tick" and delay_ms:
                await asyncio.sleep(delay_ms / 1000)
    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

@app.get("/store/catalogue")
def catalogue():
    return {"products": trk.catalogue_cards(), "categories": trk.CATEGORIES}

@app.get("/store/product/{pid}")
def product(pid: str):
    d = trk.product_detail(pid)
    if not d:
        raise HTTPException(404, f"no product {pid}")
    return d

@app.get("/store/promotions")
def promotions():
    return trk.promotions()

class LoginReq(BaseModel):
    email: str
    name: str = ""
    guest_uid: str = ""

@app.post("/auth/login")
def auth_login(req: LoginReq):
    res = trk.login(req.email, req.name, req.guest_uid)
    if res.get("error"):
        raise HTTPException(400, res["error"])
    return res

@app.get("/people")
def people():
    return {"people": trk.list_people()}

@app.get("/identity/{core_id}")
def identity(core_id: str):
    """CORE ID resolution graph — one person resolved from email + devices + channels +
    sessions (including any stitched anonymous activity)."""
    return trk.identity_graph(core_id)

class SendMailReq(BaseModel):
    device: str = "desktop"

@app.post("/customer/{core_id}/send-mail")
def customer_send_mail(core_id: str, req: SendMailReq | None = None):
    """Marketer sends a targeted message to this customer; it lands in their inbox."""
    res = trk.send_marketer_mail(core_id, (req.device if req else "desktop"))
    if not res.get("ok"):
        raise HTTPException(400, res.get("error", "could not send"))
    return res

@app.get("/analytics/identity")
def analytics_identity():
    """Fleet-wide CORE ID resolution analytics (people resolved, cross-device, signals
    unified, anonymous sessions stitched)."""
    return trk.identity_summary()

@app.delete("/people/{core_id}")
def delete_person(core_id: str):
    return trk.delete_person(core_id)

@app.post("/admin/reset")
def admin_reset():
    return trk.reset_all()

@app.post("/admin/seed")
def admin_seed(reset: bool = True):
    """Populate the demo with realistic people, a cross-device merge, and revenue —
    so a freshly deployed instance isn't empty. Hit this once after deploy."""
    return trk.seed_demo(reset)

class ConsentReq(BaseModel):
    uid: str
    consent: bool

@app.post("/consent")
def consent(req: ConsentReq):
    return trk.set_consent(req.uid, req.consent)

@app.get("/customer/{core_id}/strategy")
def customer_strategy(core_id: str):
    import agent as ag
    v = trk.STORE.visitor(core_id)
    dev = v.devices[-1] if v.devices else "desktop"
    p = trk.profile(v)
    nba = trk.next_best_action(v, dev)
    analysis = trk.analyze_customer(v)        # real-time behavioural analysis (the brain)
    facts = trk.customer_facts(v)             # rich context for the LLM
    system = (
        "You are Kairos's marketing strategist advising on ONE specific shopper, using their REAL-TIME "
        "behaviour below. Analyse what they have actually done — what they bought vs. still want, cart, "
        "wishlist, uplift and intent — and recommend the single best move in 2-3 sentences: a decision "
        "(SPEND / HOLD / SUPPRESS / SKIP / NURTURE), the channel, and the offer (or none). Name the "
        "SPECIFIC product(s). Never re-pitch something they already bought — cross-sell instead. "
        "Emphasise incrementality and restraint (don't discount people who'd buy anyway; don't contact "
        "Sleeping Dogs). If consent is false, recommend no outbound contact. Be concrete; cite the numbers."
    )
    narrative, src = ag.llm_complete(system, facts, 240)
    if not narrative or not narrative.strip():
        narrative, src = analysis["narrative"], "analysis"     # analytical, action-specific fallback
    return {"segment": p["segment"], "decision": analysis["decision"],
            "next_best_action": nba, "narrative": narrative.strip(),
            "source": src, "consent": getattr(v, "consent", True)}

class ChatReq(BaseModel):
    uid: str
    message: str

@app.post("/chat")
def chat_endpoint(req: ChatReq):
    import chat as ch
    res = ch.answer(req.message, trk.PRODUCTS)
    top = res["products"][0]["id"] if res["products"] else None
    trk.STORE.track(req.uid, {"type": "chat", "product_id": top, "device": "desktop",
                              "meta": {"message": req.message[:200],
                                       "matched": [p["id"] for p in res["products"]]}})
    if top:
        trk.STORE.track(req.uid, {"type": "view_product", "product_id": top,
                                  "device": "desktop", "dwell_ms": 1500})
    return res

@app.get("/live-customers")
def live_customers():
    now = time.time()
    rows = sorted(trk.LIVE_SHOPPERS.values(), key=lambda r: r["ts"], reverse=True)
    counts: dict[str, int] = {}
    active_count = 0
    out = []
    for r in rows:
        secs = int(now - r["ts"])
        is_active = secs <= 120
        if is_active:
            active_count += 1
        counts[r["bucket"]] = counts.get(r["bucket"], 0) + 1
        if len(out) < 50:
            out.append({**r, "active": is_active, "seconds_ago": secs})
    return {"count": len(rows), "active_count": active_count,
            "buckets": counts, "shoppers": out}

class RedeemReq(BaseModel):
    uid: str
    reward_id: str

@app.post("/redeem")
def redeem(req: RedeemReq):
    return trk.STORE.redeem(req.uid, req.reward_id)

class TrackReq(BaseModel):
    uid: str
    type: str
    product_id: str | None = None
    device: str = "desktop"
    dwell_ms: int = 0
    meta: dict | None = None

@app.post("/track")
def track(req: TrackReq):
    v = trk.STORE.track(req.uid, req.model_dump())
    return {
        "stored_event": v.events[-1],
        "profile": trk.profile(v, record=True),
        "next_best_action": trk.next_best_action(v, req.device),
        "mail": trk.mail_simulation(v, req.device),
        "patterns": trk.detect_patterns(v),
        "bundle": trk.detect_bundle(v),
        "economics": trk.session_economics(v),
        "inbox": v.inbox[::-1],
    }

@app.get("/visitor/{uid}")
def visitor(uid: str):
    v = trk.STORE.visitor(uid)
    dev = v.devices[-1] if v.devices else "desktop"
    return {"profile": trk.profile(v, record=True), "next_best_action": trk.next_best_action(v, dev),
            "mail": trk.mail_simulation(v, dev), "recent": v.events[-25:][::-1],
            "patterns": trk.detect_patterns(v), "bundle": trk.detect_bundle(v),
            "economics": trk.session_economics(v), "inbox": v.inbox[::-1],
            "ended": v.ended,
            "cart": [trk.enrich(trk.PRODUCT_BY_ID[c]) for c in v.cart if c in trk.PRODUCT_BY_ID],
            "orders": v.orders[::-1]}

class SessionEndReq(BaseModel):
    uid: str
    device: str = "desktop"

@app.post("/session/end")
def session_end(req: SessionEndReq):
    return trk.STORE.end_session(req.uid, req.device)

class PurchaseReq(BaseModel):
    uid: str
    applied_points: int = 0

@app.post("/purchase")
def purchase(req: PurchaseReq):
    res = trk.STORE.purchase(req.uid, req.applied_points)
    if not res.get("ok"):
        raise HTTPException(400, res.get("error", "checkout failed"))
    return res

@app.get("/analytics/live")
def analytics_live():
    return trk.cohort_analytics()

@app.get("/strategy")
def strategy():
    return trk.strategy_report()

@app.get("/benchmark")
def benchmark(n: int = Query(5000, ge=200, le=64000), seed: int = Query(42, ge=0, le=2147483647)):
    return sim.benchmark(n=n, seed=seed)

@app.get("/inbox/{uid}")
def inbox(uid: str, device: str = "desktop"):
    v = trk.STORE.visitor(uid)
    return {"inbox": v.inbox[::-1]}

@app.get("/visitor/{uid}/suggestion")
def suggestion(uid: str, device: str = "mobile"):
    v = trk.STORE.visitor(uid)
    v.add_device(device)
    return {"identity_resolved": len(v.devices) > 1, "devices": v.devices,
            "profile": trk.profile(v, record=True), "next_best_action": trk.next_best_action(v, device),
            "mail": trk.mail_simulation(v, device)}

@app.get("/people/stream")
async def people_stream():
    async def gen():
        for _ in range(36000):
            yield sim.sse_format({"people": trk.list_people()})
            await asyncio.sleep(1.0)
    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

@app.get("/live-customers/stream")
async def live_customers_stream():
    async def gen():
        for _ in range(36000):
            yield sim.sse_format(live_customers())
            await asyncio.sleep(1.0)
    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

@app.get("/visitor/{uid}/stream")
async def visitor_stream(uid: str):
    async def gen():
        last = -1
        for _ in range(3000):
            v = trk.STORE.visitor(uid)
            if len(v.events) != last:
                last = len(v.events)
                payload = {
                    "profile": trk.profile(v, record=True),
                    "recent": v.events[-8:],
                    "next_best_action": trk.next_best_action(v, v.devices[-1] if v.devices else "desktop"),
                }
                yield sim.sse_format(payload)
            await asyncio.sleep(0.2)
    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

class ExplainReq(BaseModel):
    customer_id: str

@app.post("/explain")
def explain(req: ExplainReq):
    df = scores()
    row = df[df["customer_id"] == req.customer_id]
    if row.empty:
        raise HTTPException(404, f"no customer {req.customer_id}")
    r = row.iloc[0]
    action, _ = BUCKET_ACTION.get(r["bucket"], ("?", ""))
    facts = (
        f"Customer {r['customer_id']}: bucket={r['bucket']}, "
        f"baseline purchase probability={r['base_rate']:.1%}, "
        f"incremental lift from marketing={r['uplift']:+.1%}, "
        f"expected incremental revenue=${r['inc_revenue']:.0f}, "
        f"recency={int(r['recency'])} months, channel={r['channel']}. "
        f"Recommended action: {action}."
    )

    import agent as ag
    system = (
        "You are a marketing decisioning analyst. Explain in 3-4 sentences, "
        "in plain business English, why the system made this call. Emphasise "
        "INCREMENTALITY: we spend only where marketing changes the outcome. "
        "Be concrete and confident; no hedging."
    )
    text, src = ag.llm_complete(system, facts, 300)
    if text:
        return {"explanation": text, "source": src}
    return {"explanation": _fallback_explain(r, action), "source": "template"}

def _fallback_explain(r, action: str) -> str:
    if r["bucket"] == "Sure Thing":
        return (
            f"Hold. {r['customer_id']} already buys at a {r['base_rate']:.0%} baseline "
            f"rate, and marketing moves that by only {r['uplift']:+.1%}. Spending here "
            f"pays for a purchase that happens anyway — the budget is better spent on a "
            f"Persuadable."
        )
    if r["bucket"] == "Sleeping Dog":
        return (
            f"Suppress. For {r['customer_id']}, contact actually lowers conversion "
            f"({r['uplift']:+.1%}). Leaving them alone protects organic revenue that "
            f"marketing would otherwise erode."
        )
    if r["bucket"] == "Persuadable":
        return (
            f"Target. {r['customer_id']} has a modest {r['base_rate']:.0%} baseline but "
            f"marketing lifts conversion {r['uplift']:+.1%}, worth ~${r['inc_revenue']:.0f} "
            f"in incremental revenue. This is exactly where budget changes the outcome."
        )
    return (
        f"Hold. {r['customer_id']} won't convert with or without contact "
        f"({r['uplift']:+.1%} lift). Spending here is wasted."
    )

@app.post("/allocate")
def allocate(req: AllocateReq):
    alloc = allocation()
    from_curve = alloc["curve"]
    xs = [p["budget"] for p in from_curve]
    rev = float(np.interp(req.budget, xs, [p["revenue"] for p in from_curve]))
    cust = int(np.interp(req.budget, xs, [p["customers"] for p in from_curve]))
    knee = alloc.get("knee", {}) or {}
    past_knee = bool(knee.get("budget") is not None and req.budget > knee["budget"])
    return {
        "budget": req.budget,
        "revenue": round(rev, 2),
        "customers_targeted": cust,
        "knee": {"budget": knee.get("budget"), "revenue": knee.get("revenue"),
                 "customers": knee.get("customers")},
        "past_knee": past_knee,
        "note": ("This budget is past the marginal-ROI knee — every dollar beyond the knee earns "
                 "less; the optimal stop is the knee." if past_knee
                 else "This budget is at or below the optimal marginal-ROI knee."),
    }

class AgentReq(BaseModel):
    goal: str

@app.post("/agent")
def agent_endpoint(req: AgentReq):
    """A tool-using Claude agent that plans a campaign by calling the system's own
    functions (segments, allocation, benchmark, strategy) and grounding its answer in them."""
    import agent as ag
    executors = {
        "get_segments": lambda: segments(),
        "solve_allocation": lambda budget: allocate(AllocateReq(budget=float(budget))),
        "run_benchmark": lambda: {k: sim.benchmark(n=64000)[k]
                                  for k in ("traditional", "conductor", "deltas")},
        "get_strategy": lambda: trk.strategy_report(),
        "get_live_shoppers": lambda: {"shoppers": trk.live_shoppers_detail()},
    }
    return ag.run(req.goal, executors)

@app.get("/report")
def report():
    import agent as ag
    seg = segments()
    by = {s["bucket"]: s for s in seg["segments"]}
    total = seg["total_customers"]
    alloc = allocation()
    knee = alloc.get("knee", {}) or {}
    b = sim.benchmark(n=64000)
    d, C, T = b["deltas"], b["conductor"], b["traditional"]
    strat = trk.strategy_report()
    live = trk.live_shoppers_detail()
    pers = by.get("Persuadable", {})

    facts = (
        f"Customer base: {total:,}. Mix — Persuadable {pers.get('pct')}% ({pers.get('count'):,}), "
        f"Sure Thing {by.get('Sure Thing',{}).get('pct')}%, Sleeping Dog {by.get('Sleeping Dog',{}).get('pct')}%, "
        f"Lost Cause {by.get('Lost Cause',{}).get('pct')}%. "
        f"Optimal spend (marginal-ROI knee): ${knee.get('budget',0):,.0f} reaching {knee.get('customers',0):,} "
        f"customers for ${knee.get('revenue',0):,.0f} incremental revenue. "
        f"Vs traditional batch-and-blast: +{d.get('net_revenue_pct')}% net revenue, "
        f"{abs(d.get('messages_saved',0)):,} fewer messages, ${d.get('spend_saved',0):,.0f} less spend, "
        f"ROI {C.get('roi')}x vs {T.get('roi')}x. Live right now: {len(live)} shoppers on site."
    )
    system = ("You are a senior marketing strategy consultant. Using ONLY the numbers provided, write a "
              "3-4 sentence executive summary, then a line 'NEXT STEPS:' followed by 5 concrete, prioritised "
              "next steps. Emphasise incrementality (spend only where marketing changes the outcome) and "
              "restraint. Plain text, no markdown headers.")
    narrative, src = ag.llm_complete(system, facts, 520)
    if not narrative:
        src = "template"
        narrative = (
            f"Kairos targets the {pers.get('count',0):,} Persuadable customers ({pers.get('pct')}% of the base) "
            f"where marketing measurably changes the outcome, and deliberately holds back on the rest. The "
            f"marginal-ROI knee says the optimal spend is about ${knee.get('budget',0):,.0f}, reaching "
            f"{knee.get('customers',0):,} of the highest-uplift customers for ${knee.get('revenue',0):,.0f} in "
            f"incremental revenue — beyond that, every dollar earns less. Against a traditional batch-and-blast "
            f"campaign this delivers {d.get('net_revenue_pct')}% more net revenue with "
            f"{abs(d.get('messages_saved',0)):,} fewer messages.\n"
            f"NEXT STEPS:\n"
            f"1. Fund Persuadables up to the ${knee.get('budget',0):,.0f} knee; stop there.\n"
            f"2. Suppress Sleeping Dogs entirely — contact lowers their conversion.\n"
            f"3. Reward Sure Things with loyalty, never discounts, to protect margin.\n"
            f"4. Keep Lost Causes on cheap ambient channels only.\n"
            f"5. Right-size every Persuadable offer to its Minimum Effective Dose, not a blanket 20%."
        )

    return {
        "generated_at": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
        "total_customers": total,
        "segments": seg["segments"],
        "knee": knee,
        "benchmark": {"net_revenue_pct": d.get("net_revenue_pct"),
                      "messages_saved": d.get("messages_saved"),
                      "spend_saved": d.get("spend_saved"),
                      "roi": C.get("roi"), "trad_roi": T.get("roi")},
        "restraint": alloc.get("restraint_metrics", {}),
        "live": {"on_site": len(live), "funnel": strat.get("funnel", {}),
                 "recommendations": strat.get("recommendations", [])},
        "narrative": narrative, "source": src,
    }

def _rows(df: pd.DataFrame) -> list[dict]:
    recs = []
    for _, r in df.iterrows():
        action, why = BUCKET_ACTION.get(r["bucket"], ("?", ""))
        recs.append({
            "customer_id": r["customer_id"],
            "bucket": r["bucket"],
            "base_rate": round(float(r["base_rate"]), 4),
            "uplift": round(float(r["uplift"]), 4),
            "inc_revenue": round(float(r["inc_revenue"]), 2),
            "channel": str(r["channel"]),
            "recency": int(r["recency"]),
            "history_segment": str(r["history_segment"]),
            "action": action,
            "rationale": why,
        })
    return recs
