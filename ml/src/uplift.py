from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.model_selection import train_test_split

DATA = Path(__file__).resolve().parents[1] / "data" / "processed" / "customers.parquet"
ART = Path(__file__).resolve().parents[1] / "artifacts"

OUTCOME = "visit"
FEATURES = ["recency", "history", "mens", "womens", "newbie"]
CAT_FEATURES = ["zip_code", "channel", "history_segment"]

PERSUADABLE_UPLIFT_Q = 0.70
SURE_THING_BASE_Q = 0.60

def load() -> pd.DataFrame:
    df = pd.read_parquet(DATA)
    cats = pd.get_dummies(df[CAT_FEATURES].astype(str), prefix=CAT_FEATURES)
    X = pd.concat([df[FEATURES].astype(float), cats.astype(float)], axis=1)
    return df, X

def train(df: pd.DataFrame, X: pd.DataFrame):
    T = df["treatment"].values
    Y = df[OUTCOME].values

    Xtr, Xte, Ttr, Tte, Ytr, Yte, idx_tr, idx_te = train_test_split(
        X.values, T, Y, df.index.values, test_size=0.3, random_state=42, stratify=T
    )

    try:
        from econml.metalearners import XLearner
        est = XLearner(
            models=GradientBoostingRegressor(n_estimators=200, max_depth=3),
            cate_models=GradientBoostingRegressor(n_estimators=200, max_depth=3),
            propensity_model=GradientBoostingClassifier(n_estimators=100, max_depth=3),
        )
        est.fit(Ytr, Ttr, X=Xtr)
        cate = est.effect(X.values)
        method = "EconML X-Learner"
    except Exception as e:
        print(f"[uplift] EconML unavailable ({e!r}); using T-Learner fallback")
        m1 = GradientBoostingClassifier(n_estimators=200, max_depth=3)
        m0 = GradientBoostingClassifier(n_estimators=200, max_depth=3)
        m1.fit(Xtr[Ttr == 1], Ytr[Ttr == 1])
        m0.fit(Xtr[Ttr == 0], Ytr[Ttr == 0])
        cate = m1.predict_proba(X.values)[:, 1] - m0.predict_proba(X.values)[:, 1]
        est = {"m1": m1, "m0": m0}
        method = "T-Learner (sklearn)"

    base_model = GradientBoostingClassifier(n_estimators=200, max_depth=3)
    base_model.fit(Xtr[Ttr == 0], Ytr[Ttr == 0])
    base_rate = base_model.predict_proba(X.values)[:, 1]

    print(f"[uplift] trained via {method}")
    return est, method, cate, base_rate, set(idx_te)

def conversion_uplift(df: pd.DataFrame, X: pd.DataFrame):
    T, Yc = df["treatment"].values, df["conversion"].values
    m1 = GradientBoostingClassifier(n_estimators=200, max_depth=3)
    m0 = GradientBoostingClassifier(n_estimators=200, max_depth=3)
    m1.fit(X.values[T == 1], Yc[T == 1])
    m0.fit(X.values[T == 0], Yc[T == 0])
    p1 = m1.predict_proba(X.values)[:, 1]
    p0 = m0.predict_proba(X.values)[:, 1]
    return p1 - p0, p0

def bucketize(base_rate: np.ndarray, uplift: np.ndarray) -> np.ndarray:
    uplift_hi = np.quantile(uplift, PERSUADABLE_UPLIFT_Q)
    base_hi = np.quantile(base_rate, SURE_THING_BASE_Q)
    out = np.empty(len(uplift), dtype=object)
    for i, (b, u) in enumerate(zip(base_rate, uplift)):
        if u < 0:
            out[i] = "Sleeping Dog"
        elif u >= uplift_hi:
            out[i] = "Persuadable"
        elif b >= base_hi:
            out[i] = "Sure Thing"
        else:
            out[i] = "Lost Cause"
    return out

def qini_curve(y: np.ndarray, t: np.ndarray, uplift: np.ndarray, n_bins: int = 100):
    order = np.argsort(-uplift)
    y, t = y[order], t[order]
    n = len(y)
    xs, ys = [0.0], [0.0]
    for k in range(1, n_bins + 1):
        cut = int(n * k / n_bins)
        yk, tk = y[:cut], t[:cut]
        n_t = max((tk == 1).sum(), 1)
        n_c = max((tk == 0).sum(), 1)
        gain = (yk[tk == 1].sum()) - (yk[tk == 0].sum()) * (n_t / n_c)
        xs.append(k / n_bins)
        ys.append(float(gain))
    total = ys[-1] if ys[-1] != 0 else 1.0
    ys_norm = [v / total for v in ys]
    auuc = float(np.trapezoid(ys_norm, xs) - 0.5)
    return {"x": xs, "y": ys_norm, "auuc": auuc}

def main() -> None:
    ART.mkdir(parents=True, exist_ok=True)
    df, X = load()
    est, method, cate, base_rate, test_idx = train(df, X)

    df = df.copy()
    df["base_rate"] = base_rate
    df["uplift"] = cate
    df["bucket"] = bucketize(base_rate, cate)

    aov = float(df.loc[df.conversion == 1, "spend"].mean())
    value_per_visit = float(df.loc[df.visit == 1, "conversion"].mean()) * aov
    df["inc_revenue"] = np.clip(cate, 0, None) * value_per_visit
    _, base_conv = conversion_uplift(df, X)
    df["base_conv"] = base_conv
    print(f"[uplift] AOV=${aov:.2f}  value/visit=${value_per_visit:.2f}  "
          f"total incremental revenue=${df['inc_revenue'].sum():,.0f}")

    mask = df.index.isin(test_idx)
    qini = qini_curve(df.loc[mask, OUTCOME].values,
                      df.loc[mask, "treatment"].values,
                      df.loc[mask, "uplift"].values)

    counts = df["bucket"].value_counts().to_dict()
    print(f"[uplift] buckets: {counts}")
    print(f"[uplift] AUUC (vs random): {qini['auuc']:+.4f}  "
          f"({'model beats random' if qini['auuc'] > 0 else 'check model'})")

    cols = ["customer_id", "base_rate", "uplift", "base_conv",
            "inc_revenue", "bucket", "treatment", OUTCOME, "conversion", "spend",
            "channel", "history_segment", "recency"]
    df[cols].to_parquet(ART / "scores.parquet", index=False)
    with open(ART / "qini.json", "w") as f:
        json.dump({"method": method, "buckets": counts, **qini}, f, indent=2)
    joblib.dump(est, ART / "model.joblib")
    print(f"[uplift] wrote scores.parquet, qini.json, model.joblib -> {ART}")

if __name__ == "__main__":
    main()
