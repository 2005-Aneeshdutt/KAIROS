"""Data pipeline — Hillstrom MineThatData E-Mail Analytics dataset.

A real randomized experiment (RCT): customers were randomly assigned to receive a
Men's email, a Women's email, or no email. Because assignment is random, the
difference in outcomes between treated and control groups is a *causal* effect —
exactly what uplift modeling needs. This is why our incrementality claims survive
scrutiny: they rest on randomized treatment, not observational correlation.

Run:  python -m src.data
Emits: ml/data/processed/customers.parquet
"""
from __future__ import annotations

import io
from pathlib import Path

import pandas as pd
import requests

HILLSTROM_URL = (
    "http://www.minethatdata.com/"
    "Kevin_Hillstrom_MineThatData_E-MailAnalytics_DataMiningChallenge_2008.03.20.csv"
)

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"
PROCESSED_DIR = Path(__file__).resolve().parents[1] / "data" / "processed"
RAW_CSV = RAW_DIR / "hillstrom.csv"
OUT_PARQUET = PROCESSED_DIR / "customers.parquet"


def download() -> pd.DataFrame:
    """Fetch the raw CSV (cached locally after first run)."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if RAW_CSV.exists():
        print(f"[data] using cached {RAW_CSV}")
        return pd.read_csv(RAW_CSV)

    print(f"[data] downloading Hillstrom dataset ...")
    resp = requests.get(HILLSTROM_URL, timeout=60)
    resp.raise_for_status()
    df = pd.read_csv(io.StringIO(resp.text))
    df.to_csv(RAW_CSV, index=False)
    print(f"[data] cached {len(df):,} rows -> {RAW_CSV}")
    return df


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    """Clean + feature-engineer into a modeling table.

    Treatment = received any email (Men's or Women's). Control = No E-Mail.
    Primary outcome = `visit` (site visit within 2 weeks) — denser signal than
    conversion, standard choice for Hillstrom uplift work. `conversion` and
    `spend` are kept for revenue-impact accounting downstream.
    """
    df = df.copy()
    df.columns = [c.strip().lower() for c in df.columns]

    # Treatment indicator: 1 if an email was sent, 0 for the holdout/control arm.
    df["treatment"] = (df["segment"] != "No E-Mail").astype(int)
    # Keep which creative was sent — lets us tell a per-channel story later.
    df["email_type"] = df["segment"].map(
        {"Mens E-Mail": "mens", "Womens E-Mail": "womens", "No E-Mail": "none"}
    )

    # Categorical encodings
    df["zip_code"] = df["zip_code"].astype("category")
    df["channel"] = df["channel"].astype("category")
    seg_order = ["1) $0 - $100", "2) $100 - $200", "3) $200 - $350",
                 "4) $350 - $500", "5) $500 - $750", "6) $750 - $1,000",
                 "7) $1,000 +"]
    df["history_segment"] = pd.Categorical(
        df["history_segment"], categories=seg_order, ordered=True
    )

    # Synthetic, stable customer id for joins in the API / dashboard.
    df.insert(0, "customer_id", [f"C{i:06d}" for i in range(len(df))])

    keep = [
        "customer_id", "recency", "history", "history_segment", "mens", "womens",
        "zip_code", "newbie", "channel", "treatment", "email_type",
        "visit", "conversion", "spend",
    ]
    out = df[keep]

    # Sanity: treatment/control balance + naive ATE (the headline causal number).
    t = out[out.treatment == 1]
    c = out[out.treatment == 0]
    ate_visit = t.visit.mean() - c.visit.mean()
    ate_conv = t.conversion.mean() - c.conversion.mean()
    print(f"[data] rows={len(out):,}  treated={len(t):,}  control={len(c):,}")
    print(f"[data] naive ATE  visit: {ate_visit:+.4f}   conversion: {ate_conv:+.4f}")
    print("[data] ^ this positive lift is the population-level effect we'll "
          "decompose per-customer with uplift modeling.")
    return out


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df = prepare(download())
    df.to_parquet(OUT_PARQUET, index=False)
    print(f"[data] wrote {OUT_PARQUET}")


if __name__ == "__main__":
    main()
