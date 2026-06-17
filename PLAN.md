# Build Plan — Epsilon Conductor

7-day battle plan. Cut scope top-down: a flawless closed loop beats six wobbling features.

## Day 1 — Foundation ✅ (in progress)
- [x] Repo scaffold (`/ml`, `/api`, `/web`, `/docs`)
- [ ] Load dataset (Hillstrom first — small, real RCT), EDA, confirm treatment/control
- [ ] Data pipeline emits a clean modeling table

## Day 2 — Causal core
- [ ] EconML uplift (DR-Learner + X-Learner), per-channel score vectors
- [ ] 4-bucket segmentation (Sure Things / Persuadables / Sleeping Dogs / Lost Causes)
- [ ] **Qini curve + AUUC** — credibility anchor, build early

## Day 3 — Optimization
- [ ] PuLP budget allocator: maximize incremental revenue s.t. budget
- [ ] **Marginal-ROI / diminishing-returns curve** — the CFO slide

## Day 4 — Backend + bandit
- [ ] FastAPI scoring + decisioning endpoints
- [ ] Thompson-sampling contextual bandit (next-best channel), visible convergence

## Day 5 — Frontend (big push)
- [ ] Customer scatter map (base prob vs. incremental lift)
- [ ] Individual journey timeline
- [ ] Three-metric restraint panel (Generated / Saved / Protected)
- [ ] Budget slider → live re-allocation; Qini + marginal-ROI charts

## Day 6 — Agent layer (the winning moment)
- [ ] Claude explainability: "why this decision?" + override
- [ ] Claude-generated message content per segment/channel

## Day 7 — Win the room
- [ ] Demo video (built around 3 counterintuitive moments)
- [ ] Pitch deck + architecture & data-flow diagrams
- [ ] README run instructions, innovation summary, roadmap
- [ ] Rehearse 5-min script

## The demo script (5 min)
1. **Problem** — "60% of targeted customers were buying anyway. We burn budget on the convinced."
2. **Four buckets** — live segmentation of the base, real numbers.
3. **Counterintuitive call** — one customer: traditional AI says target (82%), agent says *don't*, explains why.
4. **Budget magic** — drag slider, marginal-ROI curve flattens: "spend stops here."
5. **Impact + Epsilon** — Generated + Saved + Protected. "Incrementality is the measure of success."

## Submission checklist
Title · Description · Screenshots · Demo video · Pitch deck · Live demo link ·
Repo URL · Source zip · Run instructions · **Extras:** architecture diagram ·
data-flow diagram · differentiation summary · team contributions · roadmap
