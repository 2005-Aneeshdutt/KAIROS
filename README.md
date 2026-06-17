# Epsilon Conductor

**The AI that orchestrates every customer touchpoint for maximum _proven_ incremental value.**

> Most marketing AI predicts *who will buy*. The problem: most of those people were buying
> anyway. Conductor predicts *which purchases you actually caused* — and tells marketers
> where **not** to spend, proving that restraint is worth more than reach.

Built for the Epsilon hackathon theme:
*"How can we use AI to deliver seamless customer experiences across channels while defining
clear measures of success?"*

---

## The core idea: the four buckets

|                                | **Buys without marketing** | **Won't buy without marketing** |
| ------------------------------ | -------------------------- | ------------------------------- |
| **Buys with marketing**        | 🟢 Sure Things (save ₹)    | 🔵 **Persuadables (spend here)** |
| **Won't buy with marketing**   | 🟡 Sleeping Dogs (danger!) | 🔴 Lost Causes (don't waste)    |

We spend budget **only** where it changes the outcome — the Persuadables — and prove it
with causal metrics (Qini / AUUC), not accuracy.

---

## Architecture — a closed decisioning loop

```
1. IDENTITY      Stitch cross-channel events → one unified customer
2. CAUSAL        EconML uplift: incremental lift per customer, per channel
3. ORCHESTRATION Contextual bandit: next-best channel + time (self-optimizing)
4. OPTIMIZATION  Budget-constrained allocator → marginal-ROI curve
5. GENERATIVE    Claude writes the message per segment + channel
6. MEASUREMENT   Qini/AUUC + simulated holdout = proof.  Agent explains every decision.
        └──────────────── feedback loop ────────────────┘
```

## Repo layout

```
/ml    Python — data pipeline, uplift models, bandit, optimizer  (EconML, PuLP)
/api   FastAPI — real-time scoring + decisioning endpoints
/web   Next.js — the command-center dashboard
/docs  Architecture & data-flow diagrams, pitch deck, demo assets
```

## Quick start

```bash
# ML environment
cd ml
python -m venv .venv && source .venv/Scripts/activate   # Windows Git Bash
pip install -r requirements.txt
python -m src.data           # download + prepare the dataset
python -m src.uplift         # train uplift models, emit scores + Qini

# API (after models trained)
cd ../api && pip install -r requirements.txt && uvicorn main:app --reload

# Web
cd ../web && npm install && npm run dev
```

## Tech stack

| Layer        | Tech                                            |
| ------------ | ----------------------------------------------- |
| Data         | Hillstrom / Criteo Uplift (real RCT)            |
| Causal ML    | EconML (DR-Learner, X-Learner), scikit-learn    |
| Orchestration| Thompson-sampling contextual bandit             |
| Optimization | PuLP constrained allocation                     |
| Agent + Gen  | Claude (claude-opus-4-8 / claude-sonnet-4-6)    |
| Backend      | FastAPI                                         |
| Frontend     | Next.js + Recharts                              |

See [PLAN.md](PLAN.md) for the day-by-day build plan.
