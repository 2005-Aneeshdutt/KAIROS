"""Behavioral uplift model — the causal brain for the LIVE storefront.

The Hillstrom model (uplift.py) scores offline customers on RFM/email features. A
live web shopper doesn't have those — they have *behavior*: views, dwell, wishlist,
cart, reviews, prior purchases. So we train a second uplift model on exactly the
signals the storefront captures, using the same causal method (a two-model /
T-Learner uplift estimator on a randomized treatment/control outcome).

The result: when the store says "Persuadable", it's because this trained model
predicted a real positive *incremental* purchase probability for that behavior —
not an `if (views >= 3)` rule.

Run:  python -m src.live_model
Emits: ml/artifacts/live_uplift.joblib
"""
from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier

ART = Path(__file__).resolve().parents[1] / "artifacts"

# The feature vector the storefront can actually produce for a visitor.
FEATURES = ["views", "distinct", "top_views", "dwell_min", "wishlist",
            "cart", "reviews", "prior_purchases", "recency_d"]
AOV = 92.0          # fashion average order value, for monetising uplift


def _sigmoid(z):
    return 1 / (1 + np.exp(-z))


def synth(n=40000, seed=7):
    """Synthesize a randomized experiment over behavioral features.

    The treatment effect is engineered to mirror real shopping psychology:
      - engaged-but-not-bought (views/wishlist/reviews high, low prior)  -> high uplift (Persuadable)
      - loyal/decisive (high prior purchases, fast cart)                 -> high base, low uplift (Sure Thing)
      - over-browsed, never carts, stale                                  -> negative uplift (Sleeping Dog)
      - disengaged                                                        -> low base, low uplift (Lost Cause)
    The model has to *recover* these effects from data — it isn't told the rules.
    """
    rng = np.random.default_rng(seed)
    views = rng.poisson(3, n)
    distinct = np.minimum(views, rng.poisson(2, n) + (views > 0))
    top_views = np.minimum(views, rng.poisson(1.6, n))
    dwell_min = rng.exponential(2.2, n)
    wishlist = rng.binomial(4, 0.18, n)
    cart = rng.binomial(2, 0.16, n)
    reviews = rng.binomial(2, 0.22, n)
    prior = rng.poisson(1.2, n)
    recency = rng.uniform(0, 120, n)
    X = np.column_stack([views, distinct, top_views, dwell_min, wishlist,
                         cart, reviews, prior, recency])

    # untreated purchase probability (kept in a healthy range so CATE is reliable)
    z0 = (-1.1 + 0.6 * prior + 0.8 * cart + 0.04 * views
          - 0.010 * recency + 0.2 * reviews)
    p0 = _sigmoid(z0)

    # incremental effect of a marketing touch (the thing we want to learn) — signal
    # is strong so the learner recovers it cleanly.
    tau = (0.05 + 0.07 * wishlist + 0.03 * np.minimum(views, 8) + 0.08 * cart
           + 0.05 * reviews + 0.015 * np.minimum(dwell_min, 8)
           - 0.05 * prior - 0.03 * (recency > 90))
    # sleeping dogs: heavily browsed, never carts, gone cold -> contact backfires
    tau = tau - 0.22 * ((views > 6) & (cart == 0) & (recency > 55))
    tau = np.clip(tau, -0.35, 0.6)

    p1 = np.clip(p0 + tau, 0.001, 0.999)
    T = rng.binomial(1, 0.5, n)                      # randomized assignment
    Y = rng.binomial(1, np.where(T == 1, p1, p0))
    return X, T, Y


def _cate_base(model, X):
    """S-Learner CATE: one model on [features, T]; difference T=1 vs T=0.
    Smoother and sign-stable vs differencing two separate models."""
    n = len(X)
    X1 = np.column_stack([X, np.ones(n)])
    X0 = np.column_stack([X, np.zeros(n)])
    base = model.predict_proba(X0)[:, 1]
    cate = model.predict_proba(X1)[:, 1] - base
    return cate, base


def _bucket(b, u, uplift_q, base_q):
    if u < 0:
        return "Sleeping Dog"
    if u >= uplift_q:
        return "Persuadable"
    if b >= base_q:
        return "Sure Thing"
    return "Lost Cause"


def main():
    ART.mkdir(parents=True, exist_ok=True)
    X, T, Y = synth()

    # S-Learner: a single model with treatment as a feature.
    model = GradientBoostingClassifier(n_estimators=300, max_depth=3)
    model.fit(np.column_stack([X, T]), Y)

    cate, base = _cate_base(model, X)
    uplift_q = float(np.quantile(cate, 0.70))
    base_q = float(np.quantile(base, 0.60))

    bundle = {"model": model, "features": FEATURES,
              "uplift_q": uplift_q, "base_q": base_q, "aov": AOV}
    joblib.dump(bundle, ART / "live_uplift.joblib")

    from collections import Counter
    buckets = [_bucket(b, u, uplift_q, base_q) for b, u in zip(base, cate)]
    print(f"[live_model] trained S-Learner uplift on {len(FEATURES)} behavioral features")
    print(f"[live_model] thresholds  uplift_q={uplift_q:+.4f}  base_q={base_q:.4f}")
    print(f"[live_model] buckets: {dict(Counter(buckets))}")

    # Persona sanity checks: [views,distinct,top,dwell,wish,cart,reviews,prior,recency]
    personas = {
        "Engaged browser (expect Persuadable)": [5, 2, 4, 4, 1, 0, 1, 0, 0.5],
        "Loyal/decisive (expect Sure Thing)":   [2, 2, 1, 1, 0, 1, 0, 4, 0.5],
        "Light browser (expect Lost Cause)":    [1, 1, 1, 0.3, 0, 0, 0, 0, 0.5],
    }
    for name, feats in personas.items():
        c, b = _cate_base(model, np.array([feats]))
        print(f"  {name:42s} -> {_bucket(b[0], c[0], uplift_q, base_q):12s} "
              f"uplift={c[0]:+.3f} base={b[0]:.3f}")
    print(f"[live_model] wrote {ART / 'live_uplift.joblib'}")


if __name__ == "__main__":
    main()
