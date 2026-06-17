# Future Roadmap

## Near term (productionizing)
- **Real-time scoring** — serve uplift + next-best-channel as a low-latency API the
  campaign tools call per customer, per moment.
- **Geo / ghost-ad holdouts** — measure incrementality in production the way it should
  be measured: randomized holdouts feeding the Qini curve continuously.
- **Identity resolution** — plug into a CORE-ID-style graph so the unified customer
  profile is real cross-device, cross-channel identity, not a single dataset.

## Mid term (closing the loop)
- **Generative creative** — Claude writes and A/B-tests the message per segment ×
  channel, so "what to say" is optimized alongside "who and where".
- **Constrained multi-touch sequencing** — optimize a *sequence* of touches over time
  (frequency capping to avoid creating Sleeping Dogs), not a single send.
- **Online bandit in production** — the Thompson sampler updates from live conversions,
  continuously reallocating channel mix.

## Long term (the platform)
- **Causal budget planning** — marginal-ROI curves per campaign roll up to a portfolio
  optimizer that allocates the whole marketing budget across programs.
- **Counterfactual what-if studio** — simulate "what if we cut SMS / added WhatsApp /
  raised the budget 20%?" with calibrated causal estimates.

## Team contributions (template — fill in)
| Member | Owned |
| --- | --- |
| _name_ | Causal ML — data pipeline, EconML uplift, Qini validation |
| _name_ | Optimization — knapsack allocator, marginal-ROI, restraint metrics |
| _name_ | Orchestration — Thompson bandit, channel simulation |
| _name_ | Product — Next.js dashboard, UX, demo |
| _name_ | Agent layer — FastAPI, Claude integration, pitch |
