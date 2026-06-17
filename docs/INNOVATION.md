# Innovation & Differentiation Summary

## The one sentence
> Conductor tells marketers where **not** to spend money — and proves that restraint
> is worth more than reach.

## The core shift: predictive → causal
Every other team predicts *who will buy*. The problem: most of those people buy
anyway, so the budget is wasted on the already-convinced. Conductor predicts *which
purchases marketing actually causes* (incremental lift) and spends only there.

| Everyone else | Conductor |
| --- | --- |
| Predicts purchase probability | Predicts the *purchases you caused* (CATE) |
| Shows revenue generated | Shows generated **+ saved + protected** |
| Recommends actions | Recommends actions **and inaction** |
| Optimizes conversion rate | Optimizes *incremental* conversion under budget |
| Measures with accuracy / F1 | Measures with **Qini / AUUC** (the right metric) |

## Three things almost no team will have
1. **Budget-constrained optimization with a marginal-ROI curve.** A knapsack turns
   uplift scores into a CFO decision, and the diminishing-returns "knee" tells the
   marketer exactly where to stop spending. Nobody else thinks like a CFO.
2. **A self-optimizing channel bandit.** Thompson sampling learns the best channel
   per segment online — you watch it converge live, beating random by a measurable
   margin and approaching the oracle ceiling.
3. **The restraint dashboard + an agentic explanation layer.** "Revenue Protected"
   (money saved by *not* over-marketing) is something no team shows, and Claude
   explains every counterintuitive call — including "don't target your best customer."

## Why it fits the Epsilon theme
The brief asks for *seamless experiences across channels* **and** *clear measures of
success*. Conductor's channel orchestration is the first; **incrementality is the
honest measure of success** — the second — as third-party cookies die and the real
question becomes "can we prove we changed anything?"

## Grounded, not hand-waved
Built on the **Hillstrom** email RCT — real randomized treatment/control — so every
uplift number is validated against a true holdout, not a synthetic guess. At-scale
revenue figures are clearly labeled "projected", never passed off as measured.
