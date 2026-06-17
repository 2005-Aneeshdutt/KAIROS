"""End-to-end campaign simulation — Traditional vs Conductor on the same customers.

We replay a marketing campaign tick by tick over a real population of scored
customers, running two strategies side by side on identical people:

  TRADITIONAL  — target everyone with high purchase propensity, spray generic
                 channels, no restraint. Wastes discounts on Sure Things, annoys
                 Sleeping Dogs into unsubscribing.
  CONDUCTOR    — target only Persuadables on their best channel (one touch),
                 hold Sure Things, suppress Sleeping Dogs.

Each tick we process a batch of customers, simulate their response, accumulate
metrics for both worlds, and emit an event the dashboard animates in real time —
including a "featured" customer for the phone view and live next-best-action
recommendations.

The behavioural model is archetype-based (clearly a simulation) but seeded from each
customer's real bucket and scores, so the story is grounded, not arbitrary.
"""
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

# Per-bucket behaviour: conversion prob with no contact (ctrl), with the RIGHT
# channel (best), with a generic/wrong channel (wrong), and the chance an extra
# touch annoys them into unsubscribing (annoy).
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
    """Yield one event dict per tick (plus a final summary)."""
    rng = random.Random(seed if seed is not None else random.randrange(1 << 30))
    pop = _population()
    sample = pop.sample(min(sample_size, len(pop)), random_state=rng.randint(0, 1 << 30))
    rows = list(sample.itertuples(index=False))
    rng.shuffle(rows)

    # Traditional targets the top half by baseline propensity (its only signal).
    thr = sample["base_rate"].median()

    trad, cond = _new_world(), _new_world()
    batch = max(1, len(rows) // ticks)
    # Rotate the phone spotlight through the four archetypes so each is seen.
    spotlight_order = ["Persuadable", "Sure Thing", "Sleeping Dog", "Lost Cause"]

    for t in range(ticks):
        chunk = rows[t * batch:(t + 1) * batch] if t < ticks - 1 else rows[t * batch:]
        spotlight_bucket = spotlight_order[t % 4]
        featured = None
        recos: list[dict] = []

        for row in chunk:
            a = ARCH[row.bucket]

            # ---- TRADITIONAL: propensity-targets, generic Email + a second blast ----
            t_actions, t_outcome = [], "ignored"
            trad["customers"] += 1
            if row.base_rate >= thr:
                touches = 2                      # spray: two generic touches
                trad["touches"] += touches
                trad["send_cost"] += SEND_COST["Email"] + SEND_COST["SMS"]
                t_actions = [f"Email: {MESSAGES[row.bucket]}", "SMS: Flash sale ends tonight!"]
                # generic channel rarely matches the customer's true best channel
                p = a["wrong"] if row.best_channel != "Email" else a["best"]
                if rng.random() < a["annoy"] * touches:
                    trad["unsubscribes"] += 1
                    t_outcome = "unsubscribed"
                elif rng.random() < p:
                    trad["conversions"] += 1
                    trad["gross"] += AOV
                    trad["discount"] += AOV * DISCOUNT     # discount given to all targeted
                    t_outcome = "converted"
            else:
                if rng.random() < a["ctrl"]:
                    trad["conversions"] += 1
                    trad["gross"] += AOV
                    t_outcome = "converted (organic)"

            # ---- CONDUCTOR: only Persuadables, best channel, one touch ----
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
                # Held / suppressed — they act on their own (no discount, no annoyance).
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

            # Featured customer for the phone view (first match of the spotlight bucket).
            if featured is None and row.bucket == spotlight_bucket:
                featured = _featured(rng, row, t_actions, c_actions, t_outcome, c_outcome)

            # Recommendations feed (a few Conductor decisions per tick).
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

    # Final summary with the headline deltas.
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


def benchmark(n: int = 5000, seed: int = 42) -> dict:
    """Head-to-head benchmark over n customers — Traditional vs Conductor on the SAME
    population, with the same response model. Deterministic (seeded) so the numbers are
    reproducible and testable. Returns both worlds plus the deltas that prove the case.

    Traditional : blasts the top half by propensity with 2 generic touches + a blanket
                  20% discount; wrong channel often; over-contact drives unsubscribes.
    Conductor   : one touch to Persuadables only, on their best channel, with a
                  right-sized ~10% discount (Minimum Effective Dose); holds/suppresses
                  the rest, so Sure Things buy at full price and Sleeping Dogs are spared.
    """
    rng = random.Random(seed)
    pop = _population()
    sample = pop.sample(min(n, len(pop)), random_state=seed)
    rows = list(sample.itertuples(index=False))
    thr = sample["base_rate"].median()
    trad, cond = _new_world(), _new_world()

    for row in rows:
        a = ARCH[row.bucket]
        # ---- Traditional ----
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
                    trad["discount"] += AOV * DISCOUNT          # blanket 20% to everyone targeted
        elif rng.random() < a["ctrl"]:
            trad["conversions"] += 1
            trad["gross"] += AOV
        # ---- Conductor ----
        cond["customers"] += 1
        if row.bucket == "Persuadable":
            cond["touches"] += 1
            cond["send_cost"] += SEND_COST.get(row.best_channel, 0.1)
            if rng.random() < a["best"]:
                cond["conversions"] += 1
                cond["gross"] += AOV
                cond["discount"] += AOV * 0.10                  # Minimum Effective Dose (~10%)
        elif rng.random() < a["ctrl"]:                          # held/suppressed → organic, full price
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
