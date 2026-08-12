# Project NIMO

**NIMO** is a local-first personal-finance modelling project for learning and experimenting with synthetic data generation, transaction normalisation, dashboard design, behavioural analysis and, in later phases, Monte Carlo forecasting, budgeting, goals, reporting and an educational investing sandbox.

This repository is currently implemented through **Phase 5**:

- project/configuration and user-workspace foundation;
- normalised SQLite transaction storage;
- authoritative date-overlap statement importing;
- seeded behavioural statement generation;
- descriptive analysis and a bare-bones CLI;
- a configurable Streamlit dashboard foundation;
- manual, rule-based and export-assisted categorisation;
- internal-transfer confidence matching and cash-flow schematics.

Behaviour inference, forecasting, budgets/goals, reports and investing have dashboard and package scaffolds but are intentionally not presented as complete functionality yet.

## Core design

```text
Synthetic generator ──┐
                      ├──► rendered statements ──► normaliser ──► user database
Real statements ──────┘                                      │
                                                             ▼
                                        metrics, categories, transfers, cash flow
                                                             │
                                  CLI ◄── application services ──► dashboard
```

The synthetic generator knows a hidden latent profile. The analysis side receives only rendered bank statements, exactly as it would for a real user. Hidden ground truth is written under `data/<user>/synthetic/` for future validation and is never read by the analysis services.

## Important ingestion invariant

NIMO does **not** remove transaction rows because their visible values are identical. Two identical bus transactions on the same date may be two real journeys.

Instead, when a newer statement overlaps an older statement for the same account:

1. the newer statement is treated as authoritative for its entire minimum-to-maximum date coverage;
2. older active rows in that account/date interval are marked inactive;
3. every row from the newer statement is inserted, including visually identical rows;
4. superseded rows remain stored for provenance and rollback.

See `architecture/overlap_and_provenance.md`.

## Installation

Create a virtual environment, then install the core package:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Install the dashboard extras:

```bash
pip install -e '.[dashboard]'
```

For development and tests:

```bash
pip install -e '.[dev]'
```

## Quick start

Build the included demonstration user:

```bash
nimo init --sample --sample-seed 42
```

List profiles:

```bash
nimo user list
```

Generate another synthetic user:

```bash
nimo generate demo_user \
  --seed 901 \
  --start 2024-01-01 \
  --end 2026-07-31
```

Choose a broad archetype prior explicitly:

```bash
nimo generate saver_demo \
  --seed 1304 \
  --start 2024-01-01 \
  --end 2026-07-31 \
  --archetype stable_saver
```

Import a real CSV statement:

```bash
nimo import my_profile path/to/statement.csv --account-name 'Main Current Account'
```

Run the default analysis:

```bash
nimo analyse sample_user
nimo analyse sample_user --json
nimo accounts sample_user
nimo transactions sample_user --limit 20
nimo cashflow sample_user
```

Manage categories:

```bash
nimo categories list sample_user
nimo categories custom sample_user cycling 'Cycling'
nimo categories assign sample_user cycling 123 124
nimo categories rule-add sample_user 'Coffee rule' cafe dining
nimo categories auto sample_user
nimo categories export sample_user
nimo categories import sample_user path/to/reviewed_suggestions.csv
```

The export command creates a transaction CSV and a master prompt in the user’s `exports/` directory. No data is sent to an external model automatically. A reviewed CSV can be imported as LLM suggestions; manual assignments and user rules retain precedence.

Launch the dashboard:

```bash
nimo dashboard
```

## CLI commands

```text
nimo init
nimo user create|list
nimo generate
nimo import
nimo analyse
nimo accounts
nimo transactions
nimo categories list|auto|assign|custom|rule-add|export|import
nimo cashflow [--confirm DEBIT_ID CREDIT_ID] [--unmatch TRANSFER_GROUP_ID]
nimo dashboard
```

Use `nimo <command> --help` for command-specific options.

## User workspace

```text
data/<user_name>/
├── profile.yaml
├── raw/                  # immutable copies of imported/generated statements
├── database/
│   └── nimo.sqlite3      # normalised active and superseded records
├── synthetic/            # manifests and hidden truth for generated users
├── exports/              # user-controlled CSV/prompt exports
├── reports/              # reserved for report outputs
└── cache/                # rebuildable temporary artifacts
```

`data/sample_user/` is a reproducible generated profile. Run `python scripts/rebuild_sample_user.py` to rebuild it.

## Dashboard pages

Implemented through Phase 5:

- **Data & Setup** — create profiles, generate statements and upload CSV files;
- **Overview** — configurable headline metrics, balance history, monthly spend and recent transactions;
- **Accounts** — balances, activity and account summaries;
- **Transactions** — normalised transaction table and manual category assignment;
- **Categories** — summaries, custom categories, automatic categorisation, ChatGPT export packages and reviewed-suggestion import;
- **Cash Flow** — Sankey-style external flows, confidence-matched internal transfers, durable manual confirmation and rejection.

Scaffolded for later phases:

- Forecasting & Scenarios;
- Budgeting & Goals;
- Investing;
- User Behaviours & Configuration;
- Reporting & Advice.

Dashboard pages live in `dashboard/pages/`; shared presentation features live in `dashboard/lib/`. Core calculations remain in `src/nimo/` and are shared with the CLI.

## Themes and page customisation

Edit:

```text
config/themes/light.yaml
config/themes/dark.yaml
```

These files define surface, text, brand, status and chart design tokens. The Overview page already supports persisted show/hide and ordering choices through the widget/layout service. The same registry pattern is ready to expand to other pages.

## Configuration philosophy

Global YAML files contain defaults, priors, taxonomies and presentation tokens. They do not define a particular generated person.

The normal generator interface is deliberately small:

```text
seed + start date + end date
```

An archetype or questionnaire may adjust prior ranges, but the seed still creates the particular synthetic individual.

## Tests

Run:

```bash
pytest
```

The current suite covers:

- configuration loading;
- hierarchical seed stability;
- latent-profile reproducibility;
- end-to-end generated statement reproducibility;
- preservation of identical transactions;
- newest-date-coverage supersession;
- exact source-file protection;
- category precedence and reviewed LLM suggestion import;
- automatic/manual transfer matching, durable rejection and external-spend exclusion;
- dashboard layout persistence;
- CLI generation and analysis;
- broad population variation across seeds.

## Architecture

Start with `architecture/README.md`. Editable diagrams.net files are included for the system context, process flow, data model, generator loop, dashboard structure and roadmap.

## Privacy and scope

NIMO is currently a local educational project. Real financial data is ignored by Git by default. External LLM and market-data integrations are not enabled in the Phase 5 build. This project does not provide regulated financial or investment advice.
