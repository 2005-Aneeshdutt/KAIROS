# How to run Epsilon Conductor

Three processes: train the models once, run the API, run the dashboard.

## Prerequisites
- Python 3.10+ and Node 18+
- (Optional) An Anthropic API key for Claude-generated explanations

> Inside a venv, install with `python -m pip …` rather than bare `pip` — on some setups
> the venv's `pip` shim resolves to the wrong Python interpreter.

## 1. Train the models (one time, ~2 min)
```bash
cd ml
python -m venv .venv
source .venv/bin/activate             # Windows Git Bash: source .venv/Scripts/activate
python -m pip install -r requirements.txt

python -m src.data        # downloads Hillstrom RCT → data/processed/customers.parquet
python -m src.uplift      # EconML uplift → artifacts/scores.parquet, qini.json, model.joblib
python -m src.allocate    # PuLP knapsack → artifacts/allocation.json
python -m src.bandit      # Thompson bandit → artifacts/bandit.json
python -m src.live_model  # behavioral uplift model → artifacts/live_uplift.joblib
```

## 2. Run the API (terminal 2)
```bash
cd api
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env       # optional: add ANTHROPIC_API_KEY for live Claude explanations
uvicorn main:app --reload  # serves http://127.0.0.1:8000
```
Check: `curl http://localhost:8000/health` lists 6 artifacts.

## 3. Run the dashboard (terminal 3)
```bash
cd web
npm install
npm run dev                # open http://localhost:3000
```
The dashboard proxies `/api/*` to the FastAPI backend (override with `API_URL`). If the
API is down it falls back to empty states rather than crashing.

## Pages
| URL | What it is |
| --- | --- |
| `/`         | Analytics dashboard — buckets, Qini, marginal-ROI, restraint metrics, live revenue |
| `/strategy` | Marketing strategy — funnel, segment playbook, channel strategy, benchmark |
| `/store`    | Storefront — shop as a customer |
| `/console`  | Conductor console — the marketer's real-time view |

## Guided demo flow (~6 min)
Open `/store` and `/console` in two tabs (use an incognito window for a fresh shopper;
`localStorage.clear()` resets identity).

1. **Dashboard (`/`)** — only ~30% are Persuadable. Click a *Sure Thing* → Claude says
   "don't spend here." Drag the budget slider to the diminishing-returns knee.
2. **Shop (`/store`)** — fixate on one item, open it, click **"View all reviews"** (an
   intent signal), browse 2–3 products → a **dynamic bundle** appears. Add to cart, don't buy.
3. **Console (`/console`)** — watch the **consideration set** (per-product intent), the
   **detected patterns**, and the **two-world economics** gap grow live. Channel = In-App.
4. **Cross-device** — click **"Continue on phone"**, browse in the phone, add to cart →
   console shows `desktop → mobile` identity resolution.
5. **Leave (`/store` → "Leave site")** — the targeted email lands in the 📧 inbox on an
   off-site channel, with a deep-link straight back to the product. (We never email while
   you're on-site — only once you've left.)
6. **Check out** — pay; **`/`** dashboard revenue and **`/strategy`** funnel update in real time.
7. **Strategy (`/strategy`)** — the **head-to-head benchmark**: hit "Random seed" to prove
   Conductor beats Traditional on reproducible numbers (≈ +67% net revenue, 4–5× ROI).

The three lines to land: *"don't target your best customer"*, *"don't email someone who's
on your site"*, and *"restraint is a revenue line."*

## Troubleshooting
- **EconML install fails** — the pipeline auto-falls back to a scikit-learn T-Learner;
  results still produce. EconML needs a C++ build toolchain on some OSes.
- **`No module named pulp` / `econml`** despite installing — you hit the venv `pip` shim;
  reinstall with `python -m pip install -r requirements.txt`.
- **Windows console UnicodeEncodeError** — set `PYTHONIOENCODING=utf-8` before running.
- **Blank charts** — make sure step 1 produced `ml/artifacts/*` and the API is running.
- **`/` or `/console` briefly 404 in dev** — a Next.js hot-reload hiccup; restart `npm run dev`.
