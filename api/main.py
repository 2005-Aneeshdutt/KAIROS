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
        "profile": trk.profile(v),
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
    return {"profile": trk.profile(v), "next_best_action": trk.next_best_action(v, dev),
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
def benchmark(n: int = Query(5000, ge=200, le=64000), seed: int = 42):
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
            "profile": trk.profile(v), "next_best_action": trk.next_best_action(v, device),
            "mail": trk.mail_simulation(v, device)}

@app.get("/visitor/{uid}/stream")
async def visitor_stream(uid: str):
    async def gen():
        last = -1
        for _ in range(3000):
            v = trk.STORE.visitor(uid)
            if len(v.events) != last:
                last = len(v.events)
                payload = {
                    "profile": trk.profile(v),
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
    }
    return ag.run(req.goal, executors)

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
