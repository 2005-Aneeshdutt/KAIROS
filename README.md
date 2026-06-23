# Kairos

**Causal marketing decisioning — spend only where it changes the outcome.**

Most marketing AI predicts *who will buy*. The problem: most of those people were going
to buy anyway. **Kairos** predicts *whose decision marketing actually changed* — and tells
you where **not** to spend. From the Greek *kairos*, "the opportune moment": reach the right
person at the right moment, or stay silent.

---

## The core idea — four buckets

|                              | **Buys without marketing** | **Won't buy without marketing** |
| ---------------------------- | -------------------------- | ------------------------------- |
| **Buys with marketing**      | 🟢 Sure Things — save $    | 🔵 **Persuadables — spend here** |
| **Won't buy with marketing** | 🟡 Sleeping Dogs — danger  | 🔴 Lost Causes — skip            |

Budget goes only where it changes the outcome — the **Persuadables** — and the system
proves it with causal metrics (Qini / AUUC), not accuracy.

## What it does

- **Causal uplift, not propensity** — estimates each customer's incremental treatment
  effect (CATE).
- **Live, per-shopper scoring** — a behavioral model scores web visitors in real time,
  with per-product intent across the consideration set.
- **Channel + timing orchestration** — a Thompson-sampling bandit learns the best channel
  per segment; an in-app / off-site policy picks the right moment.
- **Budget allocation** — a 0/1 knapsack maximizes incremental revenue under budget and
  surfaces the marginal-ROI knee.
- **Minimum Effective Dose** — the smallest discount that still converts, not a blanket 20%.
- **Restraint, measured in dollars** — Revenue Generated / Budget Saved / Revenue Protected.
- **AI Strategist agent** — a tool-using agent that plans a campaign by calling the system's
  own tools (segments, allocation, benchmark, strategy) and grounding its answer in the real
  numbers. Runs a deterministic planner with no key; upgrades to a hosted LLM via **OpenRouter**
  (any tool-capable model) automatically when `OPENROUTER_API_KEY` is set.
- **Live, multi-user analytics** — every shopper on the site is scored and segmented in real
  time; the dashboard shows who's online now and the global funnel updates live.
- **Persistent by default** — carts, orders and the funnel survive restarts (SQLite locally,
  Postgres in production via `DATABASE_URL`), with an in-memory fallback.
- **Explainable** — every decision (including *not* to spend) explained in plain English.

## Proof — measured, not modelled

Validated on a real randomized controlled trial (the Hillstrom email experiment, 64,000
customers). Treated vs. held-out control:

| Bucket        | Contacted | Control | Effect                        |
| ------------- | --------- | ------- | ----------------------------- |
| Persuadable   | 1.47%     | 0.58%   | marketing lifts ~2.5×         |
| Sure Thing    | 1.14%     | 0.95%   | barely moves                  |
| Sleeping Dog  | 0.69%     | 2.52%   | **contact lowers it 1.83pp**  |
| Lost Cause    | 0.75%     | 0.26%   | negligible absolute value     |

## Repo layout

```
/ml    Python — data pipeline, uplift models, bandit, optimizer (EconML, PuLP)
/api   FastAPI — real-time scoring + decisioning endpoints
/web   Next.js — dashboard, live storefront, console, strategy view
/docs  Architecture + pitch assets
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the system and data flow.

---

## Run locally

**Prerequisites:** Python 3.11+, Node 18+. The trained model artifacts are already in
`ml/artifacts/`, so no training is needed to run the app.

**1. API** (terminal 1)
```bash
cd api
pip install -r requirements.txt
uvicorn main:app --reload          # http://127.0.0.1:8000
```
On Windows PowerShell, run `$env:PYTHONIOENCODING="utf-8"` first.

*Optional — live LLM strategist:* create `api/.env` with `OPENROUTER_API_KEY=sk-or-...`
(and optionally `OPENROUTER_MODEL`, e.g. `qwen/qwen3-235b-a22b-2507`). Without it the agent
runs a deterministic planner and `/explain` uses templates — both work offline. The store's
state persists to `api/kairos.db` (SQLite); set `DATABASE_URL` to use Postgres instead.

**2. Dashboard** (terminal 2)
```bash
cd web
npm install
npm run dev                        # http://localhost:3000
```
The dashboard proxies `/api/*` to the FastAPI backend (override with the `API_URL` env var).
If the API is down it falls back to empty states rather than crashing.

**Pages**

| URL | What it is |
| --- | --- |
| `/`          | Analytics dashboard — AI Strategist, live shoppers online now, buckets, Qini, marginal-ROI, restraint metrics, live revenue |
| `/strategy`  | Marketing strategy — funnel, segment playbook, channels, real-RCT validation, benchmark |
| `/store`     | Storefront — shop as a customer (browse, bundle, checkout, cross-device) |
| `/console`   | Marketer console — real-time view of the live shopper |

Open `/store` and `/console` side by side and click around to watch decisions update live.

**Optional — retrain the models from scratch (~2 min):**
```bash
cd ml
pip install -r requirements.txt
python -m src.data        # download Hillstrom RCT
python -m src.uplift      # uplift model -> scores, qini
python -m src.live_model  # live behavioral model
python -m src.allocate    # budget allocation
python -m src.bandit      # channel bandit
```

**Run everything as one container (mirrors production):**
```bash
docker build -t kairos .
docker run -p 3000:3000 -e PORT=3000 kairos    # http://localhost:3000
```

## Deploy (one URL)

The repo ships a `Dockerfile` + `render.yaml` that run the API and dashboard in a single
container behind one domain (Next serves the UI and proxies `/api/*` to FastAPI internally).

On [Render](https://render.com): **New → Blueprint → select this repo → Deploy Blueprint**.
You get a single URL serving the whole app. For the live AI Strategist + explanations, set
`OPENROUTER_API_KEY` (and optionally `OPENROUTER_MODEL`) on the service — `ANTHROPIC_API_KEY`
also works. Set `DATABASE_URL` to a Postgres URL for persistence that survives redeploys;
otherwise an ephemeral SQLite file is used.

## Tech stack

| Layer         | Tech                                             |
| ------------- | ------------------------------------------------ |
| Data          | Hillstrom email RCT (real randomized experiment) |
| Causal ML     | EconML X-Learner, S-Learner, scikit-learn        |
| Orchestration | Thompson-sampling contextual bandit              |
| Optimization  | PuLP 0/1 knapsack, marginal-ROI knee             |
| Backend       | FastAPI (real-time SSE)                          |
| Frontend      | Next.js, Recharts                                |
| LLM agent     | OpenRouter (tool-using strategist + explanations); Anthropic optional |
| Persistence   | SQLite (local) / Postgres via `DATABASE_URL`     |
