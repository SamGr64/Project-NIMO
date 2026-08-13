# Project roadmap

## Version 1.0.0 baseline — complete

| Phase | Capability | Status |
|---|---|---|
| 0 | configuration, workspaces, service boundaries | Complete |
| 1 | canonical database and overlap-safe import | Complete |
| 2 | latent-profile seeded generator and statement renderer | Complete |
| 3 | descriptive metrics and CLI | Complete |
| 4 | multipage dashboard, themes and persisted layouts | Complete baseline |
| 5 | categories, transfers and cash-flow network | Complete |
| 6 | behaviour inference, distributions, outliers and archetype | Complete baseline |
| 7 | default forecasts, scenarios, Monte Carlo and backtests | Complete baseline |
| 8 | inferred/custom budgets, goals and interventions | Complete baseline |
| 9 | structured evidence, offline/optional LLM reports and four formats | Complete baseline |
| 10 | educational investing sandbox and stress testing | Complete baseline |
| 11 | migrations, portable/encrypted backups, diagnostics, CI and benchmarks | Complete baseline |

“Complete baseline” means the end-to-end use case and extension contract are implemented. It does not imply the models are scientifically final or suitable for regulated use.

## Post-1.0 development themes

### Model quality

- benchmark recovery over larger synthetic populations;
- calibrate forecast interval coverage by archetype/history length;
- improve seasonality and change-point detection;
- add hierarchical/empirical distribution models;
- add explicit model selection diagnostics and uncertainty.

### Data ingestion

- Excel, OFX/QIF and Open Banking adapters;
- guided mapping presets per bank;
- currency conversion and multi-currency accounts;
- stronger pending/settled transaction reconciliation.

### Planning

- multiple-goal allocation optimisation;
- debt and credit interest models;
- tax/pension-specific modules kept behind jurisdiction-specific adapters;
- richer recurring future events.

### Investing education

- pluggable licensed market-data providers;
- rebalancing rules and asset-class factors;
- sequence-of-returns and withdrawal experiments;
- clearer learning content and accessibility testing.

### Product hardening

- authenticated multi-user deployment mode;
- stronger database migrations for destructive schema changes;
- secret-manager adapters;
- automated visual dashboard tests;
- formal threat modelling and independent security review.
