"""Budget allocation — the optimization layer.

Given a marketing budget, decide *which* customers to contact to maximize total
incremental revenue. This is a 0/1 knapsack:

    maximize   Σ inc_revenue_i · x_i
    subject to Σ contact_cost_i · x_i ≤ Budget,   x_i ∈ {0,1}

Two outputs:
  1. The marginal-ROI curve — sweep the budget 0→max and plot incremental revenue
     captured. It's concave (diminishing returns); the "knee" is where each extra
     rupee stops paying for itself. No team thinks like a CFO — this is that slide.
  2. The three restraint metrics: Revenue GENERATED, Budget SAVED, Revenue PROTECTED.

Run:  python -m src.allocate
Emits: ml/artifacts/allocation.json
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ART = Path(__file__).resolve().parents[1] / "artifacts"
SCORES = ART / "scores.parquet"

# Per-channel cost to send one message (USD). Email is cheap; SMS is dear.
# Each customer's contact cost = the cost of their cheapest effective channel.
CHANNEL_COST = {"Phone": 0.25, "Web": 0.05, "Multichannel": 0.15}
DEFAULT_COST = 0.10

# Promotional economics. The real waste in marketing isn't the send cost (pennies) —
# it's the INCENTIVE: every promo carries a discount, and handing it to someone who
# would have bought at full price gives away that margin for nothing.
DISCOUNT_RATE = 0.20          # a typical "20% off" campaign offer
# Business projection: Hillstrom is a single 2-week test on 64K customers. Real
# programs run many campaigns across a far larger base. SCALE_FACTOR projects the
# per-customer economics to an annual program; the dashboard exposes this as a
# slider so every number is honestly labeled "measured" vs "projected at scale".
SCALE_FACTOR = 1.0


def contact_cost(df: pd.DataFrame) -> np.ndarray:
    """Cost to reach each customer once, based on their acquisition channel."""
    return df["channel"].astype(str).map(CHANNEL_COST).fillna(DEFAULT_COST).values


def marginal_curve(inc_rev: np.ndarray, cost: np.ndarray, n_pts: int = 60):
    """Greedy-by-ROI frontier — optimal for the fractional knapsack and the exact
    concave envelope of the 0/1 problem. Sorting by revenue-per-rupee, then
    accumulating, traces incremental revenue vs. spend."""
    roi = inc_rev / cost
    order = np.argsort(-roi)
    cum_cost = np.cumsum(cost[order])
    cum_rev = np.cumsum(inc_rev[order])
    cum_n = np.arange(1, len(order) + 1)

    max_budget = cum_cost[-1]
    budgets = np.linspace(0, max_budget, n_pts)
    pts = []
    for b in budgets:
        k = int(np.searchsorted(cum_cost, b, side="right"))
        pts.append({
            "budget": round(float(b), 2),
            "revenue": round(float(cum_rev[k - 1]) if k > 0 else 0.0, 2),
            "customers": int(cum_n[k - 1]) if k > 0 else 0,
        })
    return pts, order, cum_cost, cum_rev


def find_knee(pts: list[dict]) -> dict:
    """The diminishing-returns knee: point of max distance from the chord between
    the first and last points. This is where we tell the marketer 'stop spending'."""
    x = np.array([p["budget"] for p in pts])
    y = np.array([p["revenue"] for p in pts])
    if x[-1] == x[0] or y[-1] == y[0]:
        return pts[-1]
    xn = (x - x[0]) / (x[-1] - x[0])
    yn = (y - y[0]) / (y[-1] - y[0])
    dist = yn - xn                      # vertical gap above the diagonal chord
    return pts[int(np.argmax(dist))]


def solve_optimal(inc_rev, cost, budget):
    """Formal 0/1 knapsack at a fixed budget via PuLP (demonstrates the LP), with a
    greedy fallback. Runs on positive-value candidates only to stay fast."""
    cand = np.where(inc_rev > 0)[0]
    try:
        import pulp
        prob = pulp.LpProblem("allocation", pulp.LpMaximize)
        x = {i: pulp.LpVariable(f"x_{i}", cat="Binary") for i in cand}
        prob += pulp.lpSum(inc_rev[i] * x[i] for i in cand)
        prob += pulp.lpSum(cost[i] * x[i] for i in cand) <= budget
        prob.solve(pulp.PULP_CBC_CMD(msg=0, timeLimit=30))
        chosen = [i for i in cand if x[i].value() and x[i].value() > 0.5]
        method = "PuLP CBC (0/1 knapsack)"
    except Exception as e:  # pragma: no cover
        print(f"[allocate] PuLP unavailable ({e!r}); greedy fallback")
        roi = inc_rev[cand] / cost[cand]
        order = cand[np.argsort(-roi)]
        cum = np.cumsum(cost[order])
        chosen = list(order[cum <= budget])
        method = "greedy-by-ROI"
    return chosen, method


def main() -> None:
    df = pd.read_parquet(SCORES)
    inc_rev = df["inc_revenue"].values
    cost = contact_cost(df)

    pts, order, cum_cost, cum_rev = marginal_curve(inc_rev, cost)
    knee = find_knee(pts)

    # Pick the operating budget at the knee and solve the formal knapsack there.
    chosen, method = solve_optimal(inc_rev, cost, knee["budget"])
    targeted = df.iloc[chosen]

    aov = float(df.loc[df.conversion == 1, "spend"].mean())
    offer_value = DISCOUNT_RATE * aov     # margin given away per redeemed promo (~$23)
    value_per_visit = float(df.loc[df.visit == 1, "conversion"].mean()) * aov

    # ---- The three restraint metrics ----
    # Revenue GENERATED: incremental revenue from the Persuadables we actually target.
    generated = float(targeted["inc_revenue"].sum())

    # Budget SAVED: a naive "target everyone likely to buy" strategy blasts the promo
    # to Sure Things too. They'd buy at full price, so every discount they redeem is
    # pure margin given away. Saved = (their full-price purchases) × discount value.
    sure = df[df.bucket == "Sure Thing"]
    saved = float((sure["base_conv"] * offer_value).sum() + contact_cost(sure).sum())

    # Revenue PROTECTED: Sleeping Dogs engage LESS when contacted (negative uplift).
    # Leaving them alone protects the organic revenue marketing would have destroyed,
    # valued with the same per-visit economics as everything else.
    dogs = df[df.bucket == "Sleeping Dog"]
    protected = float((-dogs["uplift"].clip(upper=0) * value_per_visit).sum())

    generated, saved, protected = (v * SCALE_FACTOR for v in (generated, saved, protected))

    out = {
        "curve": pts,
        "knee": knee,
        "optimal": {
            "method": method,
            "budget": round(knee["budget"], 2),
            "customers_targeted": len(chosen),
            "revenue_generated": round(generated, 2),
        },
        "restraint_metrics": {
            "revenue_generated": round(generated, 2),
            "budget_saved": round(saved, 2),
            "revenue_protected": round(protected, 2),
            "total_impact": round(generated + saved + protected, 2),
        },
        "economics": {
            "avg_order_value": round(aov, 2),
            "discount_rate": DISCOUNT_RATE,
            "offer_value": round(offer_value, 2),
            "scale_factor": SCALE_FACTOR,
            "basis": "measured" if SCALE_FACTOR == 1.0 else "projected_at_scale",
        },
    }
    (ART / "allocation.json").write_text(json.dumps(out, indent=2))

    print(f"[allocate] optimizer: {method}")
    print(f"[allocate] knee @ ${knee['budget']:,.0f} -> target {len(chosen):,} "
          f"customers for ${generated:,.0f} incremental revenue")
    print(f"[allocate] GENERATED ${generated:,.0f} | SAVED ${saved:,.0f} | "
          f"PROTECTED ${protected:,.0f} | TOTAL ${generated+saved+protected:,.0f}")
    print(f"[allocate] wrote {ART / 'allocation.json'}")


if __name__ == "__main__":
    main()
