# Architecture — Epsilon Conductor

## System diagram

```
┌──────────────┐     ┌─────────────────────────────────────────────┐
│  Hillstrom   │     │                  ML PIPELINE  (/ml)          │
│  RCT data    │────▶│                                              │
│  64k, T/C    │     │  data.py     clean + feature engineer        │
└──────────────┘     │  uplift.py   EconML X-Learner → CATE,        │
                     │              4 buckets, Qini/AUUC            │
                     │  allocate.py PuLP knapsack → marginal ROI,   │
                     │              restraint metrics              │
                     │  bandit.py   Thompson sampling → best channel│
                     │                    │                         │
                     │              artifacts/*.parquet,*.json      │
                     └────────────────────┼─────────────────────────┘
                                          │
                     ┌────────────────────▼─────────────────────────┐
                     │              API  (/api, FastAPI)            │
                     │  /segments /customers /qini /allocation      │
                     │  /allocate /bandit /explain ──► Claude       │
                     └────────────────────┼─────────────────────────┘
                                          │  (Next.js /api proxy)
                     ┌────────────────────▼─────────────────────────┐
                     │           DASHBOARD  (/web, Next.js)         │
                     │  restraint metrics · segment scatter ·       │
                     │  decision inspector (Claude) · marginal-ROI  │
                     │  slider · Qini curve · bandit convergence    │
                     └──────────────────────────────────────────────┘
```

## Data flow

1. **Ingest** — Hillstrom RCT (random treatment/control) → causal ground truth.
2. **Estimate** — X-Learner predicts each customer's incremental response (CATE).
3. **Segment** — (baseline, uplift) → Persuadable / Sure Thing / Lost Cause / Sleeping Dog.
4. **Validate** — Qini curve + AUUC on a holdout prove targeting beats random.
5. **Allocate** — knapsack picks the action portfolio maximising incremental revenue
   under budget; the marginal-ROI curve exposes the diminishing-returns knee.
6. **Orchestrate** — a Thompson-sampling bandit learns the best channel per segment.
7. **Explain** — Claude turns each decision into plain-English rationale + override.

## Why each choice

| Decision | Reason |
| --- | --- |
| Hillstrom RCT | Real randomized data — causal claims survive expert scrutiny |
| X-Learner (EconML) | Strong CATE estimator for imbalanced treatment groups |
| Qini / AUUC | The correct metric for uplift — not accuracy/F1 |
| Knapsack allocator | Turns scores into a budget decision a CFO understands |
| Thompson bandit | Online channel learning that visibly self-optimizes |
| Claude explain layer | Trust + human-in-the-loop, the demo's memorable moment |
