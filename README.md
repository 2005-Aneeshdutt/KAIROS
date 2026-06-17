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

**Prerequisites:** Python 3.10+ and Node 18+. Three processes run together: the ML
pipeline (once, to produce artifacts), the FastAPI backend, and the Next.js frontend.

> Tip: inside a venv, always install with `python -m pip …` (not bare `pip`) — on some
> setups the venv's `pip` shim resolves to the wrong interpreter.

### 1. ML pipeline — produces the model artifacts (run first, once)

```bash
cd ml
python -m venv .venv
source .venv/bin/activate            # Windows Git Bash: source .venv/Scripts/activate
python -m pip install -r requirements.txt

python -m src.data                   # download + prepare the Hillstrom RCT
python -m src.uplift                 # uplift model → scores.parquet, qini.json, model.joblib
python -m src.allocate               # PuLP knapsack → allocation.json (marginal ROI, restraint)
python -m src.bandit                 # Thompson bandit → bandit.json
python -m src.live_model             # behavioral uplift model → live_uplift.joblib
```

This writes everything to `ml/artifacts/`. The API reads from there.

### 2. API — FastAPI backend (new terminal)

```bash
cd api
python -m venv .venv
source .venv/bin/activate            # Windows: source .venv/Scripts/activate
python -m pip install -r requirements.txt

# optional: enables Claude-written explanations (falls back to templates without it)
cp .env.example .env                 # then add ANTHROPIC_API_KEY=...

uvicorn main:app --reload            # serves http://localhost:8000
```

Sanity check: `curl http://localhost:8000/health` should list 6 artifacts.

### 3. Web — Next.js dashboard + storefront (new terminal)

```bash
cd web
npm install
npm run dev                          # serves http://localhost:3000
```

The web app proxies `/api/*` to `http://127.0.0.1:8000` (override with `API_URL`).

### 4. Open the product

| URL | What it is |
| --- | --- |
| `http://localhost:3000`           | **Analytics dashboard** — buckets, Qini, marginal-ROI, restraint metrics, live store revenue |
| `http://localhost:3000/strategy`  | **Marketing strategy** — funnel, segment playbook, channel strategy, head-to-head benchmark |
| `http://localhost:3000/store`     | **Storefront** — shop as a customer (browse, bundle, checkout, "Leave site") |
| `http://localhost:3000/console`   | **Conductor console** — the marketer's real-time view of the shopper |

Open `/store` and `/console` side by side, click around, then **"Leave site"** to see the
targeted email land in the 📧 inbox. See [docs/RUN_INSTRUCTIONS.md](docs/RUN_INSTRUCTIONS.md)
for a full guided demo flow.

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
