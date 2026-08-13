# Changelog

## 1.0.0 — Complete baseline through Phase 11

### Behaviour inference

- Added account, category and merchant behaviour maps.
- Added weekly/monthly/yearly periodicity scoring and amount-stability measures.
- Added normal, lognormal, gamma, exponential and bimodal-normal candidate fits.
- Added robust outlier and contextual surprise scores.
- Added descriptive archetype summaries and synthetic recovery benchmarking.

### Forecasting and planning

- Added automatically inferred forecast profiles with assumption provenance.
- Added editable scenarios, dotted-path overrides and probabilistic future events.
- Added deterministic Monte Carlo balance, income, spend and category paths.
- Added threshold probabilities, scenario comparison and rolling backtests.
- Added inferred/custom budgets, per-line budget probabilities and savings goals.
- Added goal completion ranges and category-reduction intervention simulations.

### Reporting and investing

- Added frozen structured report evidence and validated narrative schemas.
- Added offline synthesis plus an optional OpenAI structured-output provider.
- Added HTML, Markdown, PDF and DOCX report renderers.
- Added a synthetic educational market dataset, asset statistics, portfolio simulation, contribution rules and stress tests.
- Added sequential threshold/goal-aware investing rules to avoid reallocating the same cash repeatedly.

### Dashboard and CLI

- Completed Forecasting, Budgeting & Goals, Investing, Behaviours & Configuration, and Reporting & Advice pages.
- Extended persisted page layout selection to the new pages.
- Added complete CLI commands for behaviour, forecasts, budgets, goals, investing, reports, export, backup and diagnostics.
- Added PowerShell-friendly repeated `--allocation SYMBOL=WEIGHT` portfolio creation.
- Exposed financial-twin questionnaire generation in both the dashboard and CLI, including repeatable `--answer QUESTION=ANSWER` values and JSON/YAML files.

### Hardening

- Added schema migrations 1–11 and audit events.
- Added portable workspace-relative output/cache paths.
- Added consistent ZIP backups, optional encrypted `.nimoenc` backups and safe restore.
- Added database/source/cache health diagnostics.
- Added cross-platform GitHub Actions, build/release workflows and pre-commit hooks.
- Expanded unit, integration, statistical and complete-workflow tests.
- Added calibration, behaviour-recovery and performance benchmark scripts.

## 0.5.0 — Phase 0–5 foundation

- Replaced the restrictive single-policy generator with a seeded latent-profile simulator.
- Added stable child seeds for independent generator components.
- Added periodic, distributional, spontaneous, shock and paired-transfer processes.
- Added multiple seeded statement renderers and a shared real/synthetic import path.
- Added per-user workspaces and SQLite databases.
- Added authoritative account/date overlap supersession while preserving identical rows.
- Added provenance for source files and superseded transactions.
- Added standard and custom categories, manual overrides, user rules and export packages.
- Added internal-transfer matching with confidence and cash-flow payloads.
- Added overview, accounts, transactions, categories and cash-flow analysis services.
- Added a shared CLI and Streamlit dashboard foundation.
- Added light/dark design-token configuration and persisted dashboard layouts.
- Added architecture documentation, roadmap and editable Draw.io schematics.
- Added unit, integration and statistical tests.
