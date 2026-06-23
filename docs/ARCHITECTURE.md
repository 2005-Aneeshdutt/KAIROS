# Architecture — Kairos

## System diagram

```
┌──────────────┐     ┌─────────────────────────────────────────────┐
│  Hillstrom   │     │                 ML PIPELINE  (/ml)           │
│  RCT data    │────▶│                                              │
│  64k, T/C    │     │  data.py        clean + feature engineer     │
└──────────────┘     │  uplift.py      EconML X-Learner -> CATE,    │
                     │                 4 buckets, Qini/AUUC         │
                     │  live_model.py  S-Learner on behavior        │
                     │  allocate.py    PuLP knapsack -> marginal ROI│
                     │  bandit.py      Thompson sampling -> channel │
                     │                     │                        │
                     │                 artifacts/*.parquet,*.json   │
                     └─────────────────────┼────────────────────────┘
                                           │
                     ┌─────────────────────▼────────────────────────┐
                     │              API  (/api, FastAPI)            │
                     │  batch:  /segments /customers /qini          │
                     │          /allocation /bandit /benchmark      │
                     │  live:   /track /visitor /store/* /strategy  │
                     │          /live-customers (who's online now)  │
                     │  /agent, /explain ─► OpenRouter LLM          │
                     │          (planner / template fallback)       │
                     │  store state ─► SQLite / Postgres (DB layer) │
                     └─────────────────────┼────────────────────────┘
                                           │  (Next.js /api proxy)
                     ┌─────────────────────▼────────────────────────┐
                     │            WEB  (/web, Next.js)              │
                     │  / dashboard · /strategy · /store · /console │
                     │  restraint metrics · Qini · marginal-ROI ·   │
                     │  bandit · live storefront · per-product cards│
                     └──────────────────────────────────────────────┘
```

In production the whole stack runs in one container (`Dockerfile` + `render.yaml`): Next
serves the UI and proxies `/api/*` to FastAPI on an internal port, so it is one URL.

## Data flow

1. **Ingest** — Hillstrom RCT (random treatment/control) gives causal ground truth.
2. **Estimate** — an X-Learner predicts each customer's incremental response (CATE); a
   second S-Learner scores live web behavior in real time.
3. **Segment** — (baseline, uplift) maps to Persuadable / Sure Thing / Lost Cause /
   Sleeping Dog via data-driven quantile cuts; negative uplift is always a Sleeping Dog.
4. **Validate** — Qini curve + AUUC on a holdout, plus observed treated-vs-control rates
   straight from the RCT (measured, not modelled).
5. **Allocate** — a 0/1 knapsack picks the action portfolio that maximizes incremental
   revenue under budget; the marginal-ROI curve exposes the diminishing-returns knee.
6. **Orchestrate** — a Thompson-sampling bandit learns the best channel per segment; a
   timing policy decides in-app vs off-site and when to stay silent.
7. **Dose** — Minimum Effective Dose picks the smallest discount that still converts.
8. **Explain** — a hosted LLM (OpenRouter, Anthropic optional) turns each decision into a
   plain-English rationale (deterministic template fallback when no key is set).
9. **Act (agent)** — the AI Strategist agent perceives a goal, selects and calls the tools
   above (segments / allocation / benchmark / strategy), and composes a grounded plan; it is
   LLM-driven via OpenRouter when a key is set, and a deterministic planner otherwise.
10. **Persist** — every visitor (cart, orders, events) is written through to a DB (SQLite
    locally, Postgres via `DATABASE_URL`) and reloaded on startup; global revenue is rebuilt
    from stored orders, so analytics survive restarts. In-memory fallback if the DB is down.

## Why each choice

| Decision            | Reason                                                           |
| ------------------- | --------------------------------------------------------------- |
| Hillstrom RCT       | Real randomized data — causal claims survive expert scrutiny    |
| X-Learner (EconML)  | Strong CATE estimator for imbalanced treatment groups           |
| S-Learner (live)    | Sign-stable uplift from sparse, real-time behavioral signals    |
| Qini / AUUC + RCT   | The correct proof for uplift — not accuracy / F1                |
| Knapsack allocator  | Turns scores into a budget decision a CFO understands           |
| Thompson bandit     | Online channel learning that visibly self-optimizes            |
| LLM agent (OpenRouter)| Tool-using strategist + explanations; planner fallback, no lock-in |
| Write-through DB     | Persistence + global analytics that survive restarts            |
