# CLI contract

The CLI is a first-class, bare-bones interface over the same application services as the dashboard.

## Command responsibilities

A command may:

1. validate arguments;
2. resolve a user/application container;
3. create a request object;
4. call a service;
5. format text or JSON output.

A command may not:

- write SQL directly;
- fit or calculate financial models;
- parse statement columns itself;
- implement a second generator;
- bypass category or transfer provenance.

## Current commands

```text
init                         initialise the data root and optional sample user
user create|list             manage workspaces
generate                     seeded statements, archetypes and questionnaire answers
import                       normalise a CSV statement
analyse                      headline metrics
accounts                     account summaries
transactions                 canonical transaction view
categories                   taxonomy, manual categories, rules and review packages
cashflow                     external/internal links plus manual confirm/reject
behaviours                    maps, patterns, outliers and diagnostics
forecast                     profiles, scenarios, overrides, events and backtests
budget                       inferred/custom budgets and probability evaluation
goal                         savings goals, simulations and interventions
invest                       educational assets, portfolios and stress simulations
report                       evidence-controlled HTML/Markdown/PDF/DOCX reports
export                       active normalised transaction exports
backup                       portable/encrypted create, verify and restore
doctor                       database, provenance and cache checks
dashboard                    launch Streamlit when installed
```

Commands support `--project-root` and `--data-root`, enabling isolated tests and alternate data locations. Important global options appear before the subcommand:

```powershell
nimo --data-root "D:\NIMO-Data" analyse my_profile
```

Questionnaire generation accepts repeatable PowerShell-friendly answers:

```powershell
nimo generate twin_demo --seed 42 --start 2024-01-01 --end 2026-01-01 `
  --answer income_pattern=predictable `
  --answer saving_style=balanced
```

Most data-heavy commands support `--json` so the CLI can be used in scripts without reproducing business logic.
