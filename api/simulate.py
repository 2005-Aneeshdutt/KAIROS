from __future__ import annotations

import json
import random
from functools import lru_cache
from pathlib import Path

import pandas as pd

ART = Path(__file__).resolve().parents[1] / "ml" / "artifacts"

AOV = 116.36
DISCOUNT = 0.20
SEND_COST = {"Email": 0.05, "Push": 0.08, "SMS": 0.25, "WhatsApp": 0.15}
CHANNELS = ["Email", "Push", "SMS", "WhatsApp"]

ARCH = {
    "Persuadable":  {"ctrl": 0.08, "best": 0.46, "wrong": 0.19, "annoy": 0.02},
    "Sure Thing":   {"ctrl": 0.55, "best": 0.60, "wrong": 0.57, "annoy": 0.04},
    "Sleeping Dog": {"ctrl": 0.24, "best": 0.10, "wrong": 0.07, "annoy": 0.22},
    "Lost Cause":   {"ctrl": 0.02, "best": 0.05, "wrong": 0.03, "annoy": 0.06},
}

MESSAGES = {
    "Persuadable": "Your size is back in stock — here's 20% off, today only 🎁",
    "Sure Thing": "Thanks for being a loyal customer ❤️",
    "Sleeping Dog": "Don't miss out! 50% off everything!!! Buy now!!!",
    "Lost Cause": "We miss you — come back?",
}

@lru_cache(maxsize=1)
def _population() -> pd.DataFrame:
    df = pd.read_parquet(ART / "scores.parquet")
    try:
        learned = json.loads((ART / "bandit.json").read_text())["learned_best_channel"]
    except Exception:
        learned = {}
    seg = df["bucket"].astype(str) + " · " + df["history_segment"].astype(str)
    df["best_channel"] = [learned.get(s, random.choice(CHANNELS)) for s in seg]
    return df

def _new_world() -> dict:
    return {"gross": 0.0, "discount": 0.0, "send_cost": 0.0, "net": 0.0,
            "conversions": 0, "touches": 0, "unsubscribes": 0, "customers": 0}

def _settle(w: dict) -> dict:
    w["net"] = round(w["gross"] - w["discount"] - w["send_cost"], 2)
    for k in ("gross", "discount", "send_cost"):
        w[k] = round(w[k], 2)
    return w

def _featured(rng: random.Random, row, trad_actions, cond_actions,
              trad_outcome, cond_outcome) -> dict:
    return {
        "customer_id": row.customer_id,
        "bucket": row.bucket,
        "best_channel": row.best_channel,
        "traditional": {"messages": trad_actions, "outcome": trad_outcome},
        "conductor": {"messages": cond_actions, "outcome": cond_outcome},
    }

def run_simulation(sample_size: int = 4000, ticks: int = 40, seed: int | None = None):
    rng = random.Random(seed if seed is not None else random.randrange(1 << 30))
    pop = _population()
    sample = pop.sample(min(sample_size, len(pop)), random_state=rng.randint(0, 1 << 30))
    rows = list(sample.itertuples(index=False))
    rng.shuffle(rows)

    thr = sample["base_rate"].median()

    trad, cond = _new_world(), _new_world()
    batch = max(1, len(rows) // ticks)
    spotlight_order = ["Persuadable", "Sure Thing", "Sleeping Dog", "Lost Cause"]

    for t in range(ticks):
        chunk = rows[t * batch:(t + 1) * batch] if t < ticks - 1 else rows[t * batch:]
        spotlight_bucket = spotlight_order[t % 4]
        featured = None
        recos: list[dict] = []

        for row in chunk:
            a = ARCH[row.bucket]

            t_actions, t_outcome = [], "ignored"
            trad["customers"] += 1
            if row.base_rate >= thr:
                touches = 2
                trad["touches"] += touches
                trad["send_cost"] += SEND_COST["Email"] + SEND_COST["SMS"]
                t_actions = [f"Email: {MESSAGES[row.bucket]}", "SMS: Flash sale ends tonight!"]
                p = a["wrong"] if row.best_channel != "Email" else a["best"]
                if rng.random() < a["annoy"] * touches:
                    trad["unsubscribes"] += 1
                    t_outcome = "unsubscribed"
                elif rng.random() < p:
                    trad["conversions"] += 1
                    trad["gross"] += AOV
                    trad["discount"] += AOV * DISCOUNT
                    t_outcome = "converted"
            else:
                if rng.random() < a["ctrl"]:
                    trad["conversions"] += 1
                    trad["gross"] += AOV
                    t_outcome = "converted (organic)"

            c_actions, c_outcome = [], "ignored"
            cond["customers"] += 1
            if row.bucket == "Persuadable":
                cond["touches"] += 1
                cond["send_cost"] += SEND_COST.get(row.best_channel, 0.1)
                c_actions = [f"{row.best_channel}: {MESSAGES['Persuadable']}"]
                if rng.random() < a["best"]:
                    cond["conversions"] += 1
                    cond["gross"] += AOV
                    cond["discount"] += AOV * DISCOUNT
                    c_outcome = "converted"
            else:
                if row.bucket == "Sure Thing":
                    c_outcome = "held (buys at full price)"
                elif row.bucket == "Sleeping Dog":
                    c_outcome = "suppressed (left alone)"
                else:
                    c_outcome = "skipped"
                if rng.random() < a["ctrl"]:
                    cond["conversions"] += 1
                    cond["gross"] += AOV
                    c_outcome = ("converted at full price" if row.bucket == "Sure Thing"
                                 else "converted (organic)")

            if featured is None and row.bucket == spotlight_bucket:
                featured = _featured(rng, row, t_actions, c_actions, t_outcome, c_outcome)

            if len(recos) < 4:
                act = ("TARGET" if row.bucket == "Persuadable" else
                       "SUPPRESS" if row.bucket == "Sleeping Dog" else "HOLD")
                recos.append({
                    "customer_id": row.customer_id, "bucket": row.bucket, "action": act,
                    "channel": row.best_channel if act == "TARGET" else "—",
                    "message": MESSAGES["Persuadable"] if act == "TARGET" else
                               ("leave alone — contact backfires" if act == "SUPPRESS"
                                else "buys anyway — save the spend"),
                    "expected_lift": round(float(row.inc_revenue), 2) if act == "TARGET" else 0.0,
                })

        yield {
            "type": "tick",
            "tick": t + 1,
            "ticks": ticks,
            "progress": round((t + 1) / ticks, 3),
            "spotlight": spotlight_bucket,
            "worlds": {"traditional": _settle(dict(trad)), "conductor": _settle(dict(cond))},
            "featured": featured,
            "recommendations": recos,
        }

    _settle(trad); _settle(cond)
    yield {
        "type": "done",
        "worlds": {"traditional": trad, "conductor": cond},
        "delta": {
            "net_revenue": round(cond["net"] - trad["net"], 2),
            "touches_saved": trad["touches"] - cond["touches"],
            "unsubscribes_avoided": trad["unsubscribes"] - cond["unsubscribes"],
        },
    }

@lru_cache(maxsize=1)
def rct_validation() -> dict:
    df = pd.read_parquet(ART / "scores.parquet")
    aov = round(float(df.loc[df["conversion"] == 1, "spend"].mean()), 2)
    order = ["Persuadable", "Sure Thing", "Sleeping Dog", "Lost Cause"]
    buckets = []
    for b in order:
        g = df[df["bucket"] == b]
        t = g[g["treatment"] == 1]["conversion"]
        c = g[g["treatment"] == 0]["conversion"]
        tr = float(t.mean()) if len(t) else 0.0
        cr = float(c.mean()) if len(c) else 0.0
        lift = tr - cr
        buckets.append({
            "bucket": b,
            "n_treated": int(len(t)), "n_control": int(len(c)),
            "treated_conv_pct": round(100 * tr, 2),
            "control_conv_pct": round(100 * cr, 2),
            "abs_uplift_pp": round(100 * lift, 2),
            "rel_lift_pct": round(100 * lift / cr) if cr else None,
            "marketing_helps": lift > 0,
        })
    treated_all = float(df[df["treatment"] == 1]["conversion"].mean())
    control_all = float(df[df["treatment"] == 0]["conversion"].mean())
    pers = next(x for x in buckets if x["bucket"] == "Persuadable")
    dog = next(x for x in buckets if x["bucket"] == "Sleeping Dog")
    return {
        "source": "Hillstrom MineThatData email RCT",
        "is_real": True,
        "n_customers": int(len(df)),
        "n_treated": int((df["treatment"] == 1).sum()),
        "n_control": int((df["treatment"] == 0).sum()),
        "aov": aov,
        "overall_treated_conv_pct": round(100 * treated_all, 2),
        "overall_control_conv_pct": round(100 * control_all, 2),
        "buckets": buckets,
        "headline": {
            "persuadable_rel_lift_pct": pers["rel_lift_pct"],
            "sleeping_dog_abs_uplift_pp": dog["abs_uplift_pp"],
        },
    }

def benchmark(n: int = 5000, seed: int = 42) -> dict:
    rng = random.Random(seed)
    pop = _population()
    sample = pop.sample(min(n, len(pop)), random_state=seed)
    rows = list(sample.itertuples(index=False))
    thr = sample["base_rate"].median()
    trad, cond = _new_world(), _new_world()

    for row in rows:
        a = ARCH[row.bucket]
        trad["customers"] += 1
        if row.base_rate >= thr:
            trad["touches"] += 2
            trad["send_cost"] += SEND_COST["Email"] + SEND_COST["SMS"]
            if rng.random() < a["annoy"] * 2:
                trad["unsubscribes"] += 1
            else:
                p = a["wrong"] if row.best_channel != "Email" else a["best"]
                if rng.random() < p:
                    trad["conversions"] += 1
                    trad["gross"] += AOV
                    trad["discount"] += AOV * DISCOUNT
        elif rng.random() < a["ctrl"]:
            trad["conversions"] += 1
            trad["gross"] += AOV
        cond["customers"] += 1
        if row.bucket == "Persuadable":
            cond["touches"] += 1
            cond["send_cost"] += SEND_COST.get(row.best_channel, 0.1)
            if rng.random() < a["best"]:
                cond["conversions"] += 1
                cond["gross"] += AOV
                cond["discount"] += AOV * 0.10
        elif rng.random() < a["ctrl"]:
            cond["conversions"] += 1
            cond["gross"] += AOV

    _settle(trad); _settle(cond)

    def pct(new, old):
        return round(100 * (new - old) / old, 1) if old else None

    t_spend = round(trad["discount"] + trad["send_cost"], 2)
    c_spend = round(cond["discount"] + cond["send_cost"], 2)
    summarize = lambda w, spend: {
        **w, "spend": spend,
        "conv_rate": round(100 * w["conversions"] / max(w["customers"], 1), 2),
        "net_per_customer": round(w["net"] / max(w["customers"], 1), 3),
        "roi": round(w["net"] / spend, 2) if spend else None,
    }
    T, C = summarize(trad, t_spend), summarize(cond, c_spend)

    return {
        "n": len(rows), "seed": seed,
        "is_simulation": True,
        "validation": rct_validation(),
        "traditional": T, "conductor": C,
        "deltas": {
            "net_revenue": round(C["net"] - T["net"], 2),
            "net_revenue_pct": pct(C["net"], T["net"]),
            "messages_saved": T["touches"] - C["touches"],
            "messages_saved_pct": pct(C["touches"], T["touches"]),
            "discount_saved": round(T["discount"] - C["discount"], 2),
            "unsubs_avoided": T["unsubscribes"] - C["unsubscribes"],
            "spend_saved": round(t_spend - c_spend, 2),
            "roi_multiple": round(C["roi"] / T["roi"], 1) if (T["roi"] and C["roi"]) else None,
        },
    }

def sse_format(event: dict) -> str:
    return f"data: {json.dumps(event)}\n\n"
