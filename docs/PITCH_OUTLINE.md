# Pitch Deck Outline (10 slides) + 5-min Demo Script

## Deck
1. **Title** — Epsilon Conductor: causal marketing decisioning. One line: "Spend only
   where it changes the outcome."
2. **The problem** — 60% of targeted customers were buying anyway. Predictive AI burns
   budget on the already-convinced. (Show the wasted-spend stat.)
3. **The insight** — Don't find who will buy; find whose behavior you can *change*.
   The 2×2: Sure Things / Persuadables / Sleeping Dogs / Lost Causes.
4. **The data** — Hillstrom RCT, 64k customers, real treatment/control. Why randomized
   data makes our causal claims real.
5. **The model** — EconML X-Learner → per-customer incremental lift. Qini curve +
   AUUC: we beat random targeting (show the curve).
6. **The decision** — Budget knapsack → marginal-ROI curve and the "stop-spending"
   knee. Think like a CFO, not a data scientist.
7. **The orchestration** — Thompson-sampling bandit learns best channel per segment,
   live convergence vs random.
8. **The restraint dashboard** — Generated + Saved + Protected. The number nobody else
   shows: Revenue Protected.
9. **The agent** — Claude explains every call, including "don't target your best
   customer." Human-in-the-loop trust.
10. **Why Epsilon** — Omnichannel experience + incrementality = the brief, answered.
    Roadmap: real-time scoring, geo-holdout measurement, generative creative.

## 5-minute demo script
- **0:00 Problem** — "Every marketing AI predicts who will buy. But most of them buy
  anyway. We're paying to reach the already-convinced."
- **1:00 Four buckets** — Show the scatter live. "Of 64,000 customers, only 30% are
  Persuadable. Predictive AI would have you pay for all of them."
- **2:00 The counterintuitive call** — Click a Sure Thing. "82% likely to buy — but
  marketing moves it almost nothing. Conductor says *don't*. Here's Claude's reasoning."
  Then click a Persuadable: low baseline, big lift. "Here's where the rupee goes."
- **3:00 Budget magic** — Drag the slider. The marginal-ROI curve flattens at the
  green knee. "Mathematically, this is where you stop spending."
- **4:00 Impact** — The three metrics. "Generated, Saved, Protected. Same budget,
  better outcome — and we can prove the lift with the Qini curve."
- **4:40 Close** — "As cookies die, the question isn't 'can we reach more?' It's 'can
  we prove we changed anything?' That's incrementality. That's Conductor."
