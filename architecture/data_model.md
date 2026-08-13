# Data model

Each user has a separate SQLite database. The database is the canonical normalised state; raw files and generated outputs remain in the user workspace.

## Foundation

- `users` — workspace identity and currency.
- `accounts` — bank/account identity, opening balance and active state.
- `source_files` — original name, stored path, SHA-256, account/date coverage and import metadata.
- `transactions` — canonical signed amounts, dates, descriptions, category/transfer links, source provenance and active/superseded state.
- `categories` and `category_rules` — standard/custom taxonomy and deterministic user rules.
- `transfer_matches` — paired internal-transfer transactions, evidence, confidence and review state.
- `dashboard_layouts` — per-page headline/widget ordering.

## Behaviour inference

- `behaviour_runs` — data/config/model version and diagnostics.
- `behaviour_patterns` — account/category/merchant periodic, distributional and spontaneous scores.
- `behavioural_maps` — current versioned map and archetype summary.
- `transaction_outliers` — robust Z score, surprise score and evidence.

## Forecasting and planning

- `forecast_profiles` — inferred baseline assumptions tied to a behaviour/data version.
- `forecast_scenarios` — user overrides and planned events; historical inference remains unchanged.
- `forecast_runs` — simulation metadata, summary and optional cache path.
- `budgets` / `budget_lines` — inferred and user-defined monthly plans.
- `goals` — target, date, current amount, priority and contribution rules.

## Investing and reports

- `portfolios` — allocations, contribution rule and assumptions.
- `investment_runs` — summary, stress scenario and optional cache path.
- `report_runs` — frozen evidence, validated narrative and portable output paths.

## Hardening

- `schema_migrations` — applied schema versions 1–11.
- `audit_events` — important user/service actions such as backup creation.

## Provenance fields

Derived outputs retain some or all of:

```text
source_data_version
model_version
config_hash
run seed
as-of date
created timestamp
scenario/profile reference
```

`source_data_version` is a stable fingerprint of active source/transaction state. A changed import, category or transfer state can therefore be detected as stale.

## Cache policy

Monte Carlo path arrays are compressed `.npz` files under `cache/`. SQLite stores portable workspace-relative references and complete summaries. Cache arrays can be deleted or omitted from a backup without losing transaction history or headline results.

## Invalidation

```text
transaction/source change
  → behaviour map stale
  → default forecast profile stale
  → planning/investment/report results should be refreshed

category/transfer change
  → category/cash-flow/behaviour outputs stale

scenario change
  → only that scenario's future results stale

layout/theme change
  → no analytical invalidation
```
