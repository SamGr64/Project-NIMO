# Project NIMO

**NIMO** is a local-first personal-finance modelling application and learning project. It can generate reproducible synthetic bank statements, import real CSV statements into a normalised per-user database, infer financial behaviours, build editable Monte Carlo forecasts, create budgets and goals, produce evidence-controlled reports, and run an educational investing sandbox.

Version **1.0.0** implements the original roadmap through Phase 11. The CLI and Streamlit dashboard call the same application services and use the same SQLite data.

> NIMO is educational software. Its forecasts, budget scenarios, reports and investment simulations are not regulated financial, tax or investment advice.

## What is included

- **Minimal seeded generation** using `seed + start date + end date`, with optional broad archetype or questionnaire priors.
- **Real-statement import** with normalisation, provenance and account/date overlap supersession.
- **Overview, account, transaction, category and cash-flow analysis** shared by CLI and dashboard.
- **Manual, rule-based and review-assisted categorisation**, including custom categories.
- **Internal-transfer matching** with confidence, manual confirmation and durable rejection.
- **Behaviour inference** across periodic, distributional and spontaneous dimensions.
- **Default forecasting** plus editable assumptions, planned events, scenarios, Monte Carlo ranges and backtesting.
- **Budgets and savings goals** with probability-aware evaluation and intervention comparisons.
- **Evidence-controlled reports** in HTML, Markdown, PDF and DOCX, with offline prose by default and optional OpenAI synthesis.
- **Educational investing sandbox** with synthetic market history, basic statistics, contribution rules, portfolio simulation and stress tests.
- **Hardening** with schema migrations, diagnostics, portable backups, optional encrypted backups, CI, benchmark scripts and audit records.

## Architecture at a glance

```text
Synthetic generator ──┐
                      ├──► rendered statements ──► normaliser ──► user SQLite database
Real statements ──────┘                                      │
                                                             ▼
                      descriptive analysis ─► behaviour map ─► default forecast
                                                             │
                                    ┌────────────────────────┼───────────────────────┐
                                    ▼                        ▼                       ▼
                              budgets/goals             scenarios              investing
                                    └────────────────────────┼───────────────────────┘
                                                             ▼
                                                structured report evidence
                                                             ▼
                                      offline or optional LLM narrative synthesis

CLI ◄──────────────────── shared application services ────────────────────► dashboard
```

The generator stores private synthetic ground truth under `data/<user>/synthetic/`. Analysis and forecasting services never read that ground truth. Only explicit benchmark tooling may compare inferred behaviour with known synthetic truth.

## Critical statement-overlap rule

NIMO does **not** delete transactions because visible rows are identical. Two identical bus transactions on the same date may be two genuine journeys.

For the same account, a newly imported statement is authoritative for its complete minimum-to-maximum booking-date coverage:

1. older active rows within that account/date interval are marked inactive;
2. every row from the new statement is inserted, including identical rows;
3. superseded rows remain stored for provenance;
4. different accounts never supersede one another.

See [`architecture/overlap_and_provenance.md`](architecture/overlap_and_provenance.md).

---

# Installation

## Windows PowerShell

Open PowerShell in the repository folder containing `pyproject.toml`.

For an automated complete setup, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\setup_windows.ps1
```

The manual equivalent is shown below.

### 1. Create a virtual environment

```powershell
python -m venv .venv
```

### 2. Activate it

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks local scripts for this session:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Activation is optional. Every command can instead use executables under `.\.venv\Scripts\` directly.

### 3. Install the complete project

```powershell
python -m pip install --upgrade pip
python -m pip install -e ".[all,dev]"
```

The complete install includes the dashboard, all report formats, encrypted backups and development tools. A smaller core-only installation is shown later.

### 4. Verify the installation

```powershell
nimo --version
nimo --help
python -m pytest
```

When `nimo` is not recognised, reactivate the environment or run:

```powershell
.\.venv\Scripts\nimo.exe --help
```

### 5. Build or inspect the sample user

The archive already contains a reproducible `sample_user`. To rebuild it:

```powershell
python .\scripts\rebuild_sample_user.py
```

Then run:

```powershell
nimo analyse sample_user
nimo behaviours sample_user
nimo forecast run sample_user --months 12 --runs 3000
nimo dashboard
```

## macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[all,dev]'
python -m pytest
nimo --version
```

## Optional dependency groups

```powershell
# Core CLI only
python -m pip install -e "."

# Streamlit and Plotly
python -m pip install -e ".[dashboard]"

# HTML/PDF reporting and optional OpenAI provider
python -m pip install -e ".[reports]"

# DOCX output
python -m pip install -e ".[documents]"

# Encrypted backups
python -m pip install -e ".[security]"

# Tests, build tools, Ruff and typing tools
python -m pip install -e ".[dev]"
```

---

# First workflows

## Generate a synthetic user

PowerShell uses a backtick for line continuation:

```powershell
nimo generate demo_user `
  --seed 901 `
  --start 2024-01-01 `
  --end 2026-07-31
```

One-line form:

```powershell
nimo generate demo_user --seed 901 --start 2024-01-01 --end 2026-07-31
```

Optional broad archetype prior:

```powershell
nimo generate saver_demo --seed 1304 --start 2024-01-01 --end 2026-07-31 --archetype stable_saver
```

Financial-twin questionnaire mode uses repeated `QUESTION=ANSWER` values. The answers constrain continuous trait ranges; the seed still creates an individual rather than a fixed template:

```powershell
nimo generate twin_demo `
  --seed 2026 `
  --start 2024-01-01 `
  --end 2026-07-31 `
  --answer income_pattern=predictable `
  --answer saving_style=balanced `
  --answer social_spend=medium `
  --answer unexpected_costs=sometimes
```

Answers may instead be stored in a JSON or YAML mapping and passed with `--questionnaire-file`. Available question and answer IDs are defined in `config/questionnaire.yaml`.

Use `demo_user`, not `demo\_user`. Backslashes are not used to escape underscores in commands.

## Import a real CSV statement

Create a profile, then import one or more statements:

```powershell
nimo user create my_profile
nimo import my_profile "C:\path\to\current-account.csv" --account-name "Main Current Account"
nimo import my_profile "C:\path\to\savings.csv" --account-name "Savings"
```

Inspect the result:

```powershell
nimo analyse my_profile
nimo accounts my_profile
nimo transactions my_profile --limit 50
nimo cashflow my_profile
nimo doctor my_profile
```

To keep data somewhere other than the repository, place the global option **before** the command:

```powershell
nimo --data-root "D:\NIMO-Data" user create my_profile
nimo --data-root "D:\NIMO-Data" import my_profile "C:\path\to\statement.csv"
```

---

# CLI guide

Run `nimo <command> --help` or `nimo <command> <action> --help` for every option.

## Users, generation and import

```powershell
nimo init --sample --sample-seed 42
nimo user list
nimo user create another_user
nimo generate another_user --seed 55 --start 2024-01-01 --end 2026-07-31
nimo import another_user "C:\path\to\statement.csv" --account-name "Current Account"
```

## Descriptive analysis

```powershell
nimo analyse sample_user
nimo analyse sample_user --json
nimo accounts sample_user
nimo transactions sample_user --limit 25
nimo cashflow sample_user
```

## Categories

```powershell
nimo categories list sample_user
nimo categories custom sample_user cycling "Cycling"
nimo categories assign sample_user cycling 123 124
nimo categories rule-add sample_user "Coffee rule" cafe dining
nimo categories auto sample_user
nimo categories export sample_user
nimo categories import sample_user "C:\path\to\reviewed_suggestions.csv"
```

Manual assignments override user rules; user rules override built-in classification; built-in classification overrides reviewed LLM suggestions.

## Behaviour inference

```powershell
nimo behaviours sample_user
nimo behaviours sample_user --scope category
nimo behaviours sample_user --scope merchant
nimo behaviours sample_user --outliers
nimo behaviours sample_user --refresh --json
```

The behaviour map retains separate periodic, distributional and spontaneous scores. A category can contain all three.

## Forecast profiles and scenarios

Inspect the default profile and scenarios:

```powershell
nimo forecast profile sample_user --json
nimo forecast scenarios sample_user
```

Create and modify a scenario:

```powershell
nimo forecast create sample_user "My Plan" --description "Lower discretionary spending and a planned course"
nimo forecast set sample_user "My Plan" global_assumptions.annual_inflation_rate 0.04
nimo forecast set sample_user "My Plan" categories.dining.monthly_mean 150
nimo forecast event-add sample_user "My Plan" "Training course" 2027-03-01 -1200 --uncertainty 150
```

Run and compare forecasts:

```powershell
nimo forecast run sample_user --scenario Baseline --months 12 --runs 5000 --threshold 2000
nimo forecast run sample_user --scenario "My Plan" --months 12 --runs 5000
nimo forecast compare sample_user Baseline "My Plan" --months 12 --runs 3000
nimo forecast backtest sample_user --holdout-months 6 --runs 1000
```

A negative event amount is an outgoing; a positive event amount is an incoming.

## Budgets

```powershell
nimo budget show sample_user
nimo budget evaluate sample_user --runs 3000
nimo budget create sample_user "My Budget"
nimo budget set sample_user "My Budget" groceries 320
nimo budget evaluate sample_user --budget "My Budget" --scenario "My Plan" --runs 3000
```

The inferred default budget is preserved separately from user-defined budgets.

## Goals

```powershell
nimo goal add sample_user "Emergency Fund" 6000 2028-12-31 --current 1500 --monthly 200 --surplus-fraction 0.20
nimo goal list sample_user
nimo goal simulate sample_user "Emergency Fund" --runs 5000
nimo goal intervention sample_user "Emergency Fund" dining 20 --runs 3000
```

Goal results are probabilities and completion ranges, not guaranteed dates.

## Investing sandbox

```powershell
nimo invest assets sample_user
nimo invest stats sample_user GLOBAL_EQ BOND CASH
nimo invest portfolios sample_user
nimo invest simulate sample_user --years 10 --runs 5000
nimo invest simulate sample_user --years 10 --runs 5000 --stress market_drop
```

Create a portfolio using repeated `SYMBOL=WEIGHT` values:

```powershell
nimo invest create sample_user "Learning Mix" `
  --allocation GLOBAL_EQ=0.60 `
  --allocation BOND=0.30 `
  --allocation CASH=0.10 `
  --rule percent_surplus `
  --fraction 0.40
```

The bundled market series are synthetic. The sandbox is deliberately separated from brokerage execution and product recommendations.

## Reports

Offline prose is the default:

```powershell
nimo report build sample_user --format html --format pdf --format docx
nimo report list sample_user
```

Optional OpenAI narrative synthesis:

```powershell
$env:OPENAI_API_KEY = "your-key"
nimo report build sample_user --format html --llm
```

NIMO performs the calculations, freezes structured evidence, validates the narrative schema and controls report layout. The language model does not calculate balances or simulation outputs.

## Export, backups and diagnostics

```powershell
nimo export sample_user --output ".\sample_user_transactions.csv"
nimo doctor sample_user
nimo backup create sample_user
nimo backup verify ".\path\to\sample_user_backup.zip"
```

Encrypted backup using an environment variable rather than a command-line password:

```powershell
$env:NIMO_BACKUP_PASSPHRASE = "use-a-long-unique-passphrase"
nimo backup create sample_user --encrypt
nimo backup verify ".\path\to\sample_user_backup.nimoenc" --encrypted
nimo backup restore ".\path\to\sample_user_backup.nimoenc" --encrypted --user restored_user
```

By default, rebuildable simulation caches are excluded from backups. Their summaries remain in SQLite, while missing path arrays are safely cleared in the portable backup snapshot.

---

# Dashboard

Launch with:

```powershell
nimo dashboard
```

Pages:

1. **Data & Setup** — select/create users, generate synthetic statements and upload CSV statements.
2. **Overview** — configurable headline metrics, balance history, monthly activity and recent transactions.
3. **Accounts** — balances, activity and account summaries.
4. **Transactions** — searchable normalised records and manual category editing.
5. **Categories** — summaries, distributions, rules, custom categories and review-assisted categorisation.
6. **Cash Flow** — external flows and confidence-matched internal transfers.
7. **Forecasting & Scenarios** — assumptions, overrides, planned events, fan charts and backtesting.
8. **Budgeting & Goals** — inferred/custom budgets, budget probabilities, goals and intervention experiments.
9. **Investing** — assets, portfolio construction, contribution rules, simulations and stress tests.
10. **Behaviours & Configuration** — inferred map, diagnostics, outliers and per-user model overrides.
11. **Reporting & Advice** — report builder, narrative preview, report history and downloads.

Every page has a sensible default. Page layouts can select/reorder headline metrics and widgets, and the preferences are stored per user. Shared visual components live under `dashboard/lib/`; page composition lives under `dashboard/pages/`. Business calculations remain under `src/nimo/`.

## Appearance

Edit the design tokens:

```text
config/themes/light.yaml
config/themes/dark.yaml
```

The same tokens feed Streamlit CSS and Plotly chart templates. Per-user display/model choices live in `data/<user>/profile.yaml` or are edited through the configuration page.

---

# User workspace

```text
data/<user_name>/
├── profile.yaml
├── raw/                  # immutable imported/generated statement copies
├── database/
│   └── nimo.sqlite3      # active and superseded rows plus analysis/planning state
├── synthetic/            # generator manifests and hidden truth for synthetic users
├── exports/              # user-controlled exports and backup archives
├── reports/              # HTML, Markdown, PDF and DOCX reports
└── cache/                # rebuildable forecast/investment path arrays
```

Stored report/cache paths are workspace-relative so a profile can be moved or restored on another operating system.

---

# Configuration

Global YAML files define defaults, priors, taxonomies, statistical thresholds and presentation tokens. They do not define an individual generated person.

```text
config/
├── app.yaml
├── generator.yaml
├── archetypes.yaml
├── questionnaire.yaml
├── statement_formats.yaml
├── categories.yaml
├── analysis.yaml
├── forecasting.yaml
├── budgeting.yaml
├── investing.yaml
├── reporting.yaml
├── dashboard/default_layouts.yaml
└── themes/{light,dark}.yaml
```

A user can override selected model defaults under `model_overrides` in their profile without modifying global configuration.

---

# Development and validation

Run the complete suite:

```powershell
python -m pytest
python -m compileall -q src dashboard scripts
python -m ruff check src dashboard scripts tests
python -m build
```

Useful diagnostics:

```powershell
python .\scripts\benchmark_behaviour_recovery.py sample_user
python .\scripts\calibrate_forecasts.py sample_user --holdout-months 6 --runs 1000
python .\scripts\benchmark_performance.py --forecast-runs 2000 --investment-runs 2000
python .\scripts\migrate_all_users.py
```

The test suite covers seed stability, statement format round-trips, overlap replacement, preservation of identical transactions, categories/transfers, behaviour fitting, deterministic Monte Carlo paths, budgets/goals, investing contribution rules, all report formats, encrypted/portable backups, database health and the expanded CLI.

GitHub Actions runs tests and builds on Windows and Ubuntu. See `.github/workflows/`.

---

# Architecture documentation

Start with [`architecture/README.md`](architecture/README.md). The folder includes contracts, data model, dependency direction, process flows, security boundaries, implementation notes, validation evidence and editable `.drawio` diagrams.

# Privacy

Review [`SECURITY.md`](SECURITY.md) before using real data. Real user workspaces, `.env` and Streamlit secrets are ignored by Git. Offline reporting and bundled synthetic market data require no external data transfer.
