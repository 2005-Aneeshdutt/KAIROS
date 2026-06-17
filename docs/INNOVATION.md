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

## Decisioning, not just measurement — why this is Epsilon's natural next product
Epsilon's moat is **identity (CORE ID) + transaction data + measurement**. Almost every
martech tool — including most attribution — measures incrementality *after* the spend, as
a retrospective report. Conductor's move is to push causal uplift **upstream into the
decision**: who to target, on which channel, at what moment, and *how much* to spend, are
all chosen by incrementality *before* the budget is committed. The pitch to Epsilon:
*"uplift is the right answer, and you are one of the only companies that owns the identity
graph and the randomized-holdout capability to actually run it at scale."* Conductor is the
decisioning layer that sits on top of assets Epsilon already has — not an outside gadget.

What we'd evolve for a real Epsilon deployment: swap the behavioral simulator for
**always-on randomized holdouts ("ghost ads" / PSA controls)** — a small group that is
never marketed to, so measured lift = treated − control updates *continuously*. That is
Epsilon's measurement DNA turned into a live decision input.

## The differentiator: **Minimum Effective Dose** (incrementality-aware discount depth)
The decision nobody personalises: **how big the discount should be.** Indian e-commerce
runs on blanket "FLAT 50% OFF / BOGO" blasts — the *depth* of the promotion is the same for
everyone, so margin is given away far beyond what was needed to flip the customer.

Conductor adds a third causal question after "who?" and "which channel?": **"what is the
smallest incentive that still changes the outcome?"** For each Persuadable we model
conversion as a function of discount depth and pick the **minimum effective dose** — often
a reminder at 0–10%, not a reflexive 20%. The new metric is **Margin Right-Sized**: profit
kept by not over-discounting people who'd have converted on a smaller nudge (or none).

- **Researched:** heterogeneous promotion-depth elasticity and personalized-incentive /
  willingness-to-pay optimization are well studied in marketing science; uplift-for-pricing
  is academically mature.
- **Under-implemented (esp. India):** depth personalization is rare here — the market is
  dominated by flat, blanket discounting.
- **Why it lands with Epsilon:** it turns their data into *per-rupee margin efficiency*, and
  it's the offer-level completion of the incrementality story — restraint, made financial.
