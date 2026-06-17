# How to run Epsilon Conductor

Three processes: train the models once, run the API, run the dashboard.

## Prerequisites
- Python 3.11+ and Node 18+
- (Optional) An Anthropic API key for Claude-generated explanations

## 1. Train the models (one time, ~2 min)
```bash
cd ml
python -m venv .venv
source .venv/Scripts/activate        # Windows Git Bash;  .venv\Scripts\activate on PowerShell
pip install -r requirements.txt
python -m src.data        # downloads Hillstrom RCT, writes data/processed/customers.parquet
python -m src.uplift      # EconML uplift → artifacts/scores.parquet, qini.json
python -m src.allocate    # PuLP knapsack → artifacts/allocation.json
python -m src.bandit      # Thompson bandit → artifacts/bandit.json
```

## 2. Run the API (terminal 2)
```bash
cd api
pip install -r requirements.txt
cp .env.example .env       # optional: add ANTHROPIC_API_KEY for live Claude explanations
uvicorn main:app --reload  # serves http://127.0.0.1:8000
```

## 3. Run the dashboard (terminal 3)
```bash
cd web
npm install
npm run dev                # open http://localhost:3000
```

The dashboard proxies `/api/*` to the FastAPI backend. If the API is down it falls
back to empty states rather than crashing.

## Troubleshooting
- **EconML install fails** — the pipeline auto-falls back to a scikit-learn
  T-Learner; results still produce. EconML needs a C++ build toolchain on some OSes.
- **Windows console UnicodeEncodeError** — set `PYTHONIOENCODING=utf-8` before running.
- **Blank charts** — make sure step 1 produced `ml/artifacts/*.json` and the API is running.
