# Kairos — Golden-Path Demo Card

**Total: ~3 minutes.** Goal: hit the three wow moments and *reach the strategist/benchmark*
(the thing the last rehearsal ran out of time for). Do **not** tour the dashboards.

---

## Pre-flight (do before you present)
1. **API up:** `cd api && source .venv/bin/activate && uvicorn main:app --port 8000`
   (needs Python 3.12 venv — `python3.12 -m venv .venv`). Check: `curl localhost:8000/health` → `live_model: true`.
2. **Web up:** `cd web && npm run dev` → http://localhost:3000
3. **Seed the demo:** `cd api && python seed_demo.py --reset`  → 8 people, $487 revenue, a cross-device merge.
4. **Open 3 tabs:** Store (`/store`), Company → Audiences (`/people`), Console (`/console`). Browser zoom ~110%.
5. Optional: set `OPENROUTER_API_KEY` for live LLM phrasing — **not required** (offline planner gives crisp grounded answers and can't stall).

---

## The opening line (memorize — judges weight this)
> "Most marketing AI tells you *who will buy*. The problem: most of them were buying anyway.
> **Kairos tells you whose decision you actually changed — and where *not* to spend.**"

---

## The 90-second prototype run

**① The problem, made concrete — Dashboard `/dashboard` (15s)**
- "Of 64,000 real customers, only ~30% are **Persuadable**. Everyone else is wasted spend."
- Point at **Revenue Generated + Budget Saved + Revenue Protected**. "Restraint, in dollars."

**② Don't target your best customer — `/strategy` (20s)**
- Show the **segment playbook**: Persuadable = spend, Sure Thing = *reward, don't discount*, Sleeping Dog = *contact backfires, stay silent*.
- Scroll to the **head-to-head benchmark** → hit **"Random seed"** live: "+63% net revenue, ~4.7× ROI — reproducible, not cherry-picked."

**③ CORE ID identity resolution — the Epsilon wow (35s)** ← *the new, signature moment*
- Store tab: click **"Continue on phone"** or just browse a couple items as the signed-in shopper… then the real beat:
- **Open a fresh incognito window → `/store` → "Browse as a guest."** Click 2–3 products, hit **"Leave site"**, then **"Sign in"** with an email.
- The **"Welcome back — we unified N events across desktop + mobile and 2 sessions into your CORE ID"** modal pops. *"That's identity resolution — anonymous to known, one person."*
- Flip to **Audiences (`/people`)** → click **Rohan Gupta** → the **Identity Resolution graph**: "1 person, resolved from 6 signals." Point at the top strip: *"8/8 resolved, 2 cross-device, 28 signals unified."*

**④ The live brain — Console `/console` (20s)**
- With the store shopper active: **per-product intent**, **detected patterns**, and the **two-world economics** gap growing live. "Same shopper, two worlds — the gap is what restraint is worth."
- Click **"Ask the AI Strategist about this customer"** (on `/people`) → it grounds a SPEND/HOLD/SUPPRESS call in *this* person's real data.

---

## Close (30s)
> "Predictive AI finds who *might* buy. **Kairos proves which purchases you caused** — and stays
> silent when spending would only waste money or do harm. It's built on Epsilon's own playbook:
> **CORE ID + PeopleCloud — Audiences, Activation, Measurement** — with a causal layer that makes
> every touch provably worth it. The right person, the right moment… or nothing at all."

---

## Three lines to land (say them with conviction)
1. **"Don't target your best customer."**
2. **"Don't email someone who's on your site."**
3. **"Restraint is a revenue line."**

## If something breaks
- LLM/strategist slow → it auto-falls back to the **offline planner** (still correct). Don't wait on it.
- Images slow (venue wifi) → emoji fallbacks render instantly; ignore.
- State looks messy → `python seed_demo.py --reset` resets to the clean 8-person demo in ~5s.
- Merge modal didn't show → you must browse as **guest first**, *then* sign in (not the other way).

## Do NOT
- Show architecture diagrams or say "X-Learner / Thompson sampling" — say *"causal AI, proven on a real randomized experiment."*
- Tour every chart. Land the three moments and stop.
