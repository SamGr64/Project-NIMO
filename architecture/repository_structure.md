# Repository structure

```text
Project-NIMO/
├── pyproject.toml                 package, dependencies, CLI and tool config
├── README.md                      PowerShell-first user/developer guide
├── SECURITY.md                    sensitive-data and secret-handling guidance
├── architecture/                  contracts and editable Draw.io schematics
├── config/                        global defaults, priors, models and themes
├── prompts/                       categorisation/report prompt templates
├── data/<user>/                   isolated workspaces
├── dashboard/
│   ├── app.py                     Streamlit bootstrap and navigation
│   ├── pages/                     page composition
│   └── lib/                       charts, layouts, themes and UI helpers
├── src/nimo/
│   ├── cli/                       thin command interface
│   ├── application/               service orchestration
│   ├── config/                    typed YAML loading
│   ├── domain/                    request/result models
│   ├── users/                     workspace lifecycle and portable paths
│   ├── storage/                   ORM, repositories, versions and migrations
│   ├── ingestion/                 CSV inspection and canonical import
│   ├── generation/                latent user, processes and statement rendering
│   ├── categorisation/            taxonomy, rules and review exchange
│   ├── analysis/                  metrics, transfers and behaviour inference
│   ├── forecasting/               profile, scenarios, Monte Carlo and backtests
│   ├── planning/                  budgets, goals and interventions
│   ├── investing/                 providers, statistics and simulations
│   ├── reporting/                 evidence, narrative providers and renderers
│   └── hardening/                 backups and diagnostics
├── tests/                         unit, integration and statistical validation
├── scripts/                       rebuild, migrate, benchmark and calibrate
└── .github/workflows/             cross-platform CI and release build
```

## Configuration ownership

- `generator.yaml`: population-level generator priors, never one fixed user.
- `statement_formats.yaml`: renderer/import layout variability.
- `analysis.yaml`: inference thresholds and candidate model families.
- `forecasting.yaml`: Monte Carlo/backtest defaults and limits.
- `budgeting.yaml`: inferred-budget and goal defaults.
- `investing.yaml`: sandbox, fees, run limits and stress presets.
- `reporting.yaml`: report sections, privacy and provider defaults.
- `dashboard/default_layouts.yaml`: page defaults.
- `themes/`: appearance tokens.

## Runtime outputs

Only `data/sample_user` is intended for source control. Real user data, caches, reports and exports are excluded by default. Cache files are rebuildable; SQLite and raw source files are durable.
