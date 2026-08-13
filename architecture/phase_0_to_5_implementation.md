# Phase 0–5 implementation

## Phase 0 — foundation

Implemented:

- source-layout package;
- typed app/theme configuration;
- per-user workspaces;
- SQLite initialization;
- application container and service boundary;
- CLI skeleton;
- privacy-aware Git defaults.

Exit criterion met: CLI and dashboard bootstrap can create/select a user and open the same database.

## Phase 1 — canonical database and import

Implemented:

- CSV delimiter handling;
- alias-based column detection;
- signed or split credit/debit amounts;
- dates, descriptions, merchants, currencies and balances;
- source manifests and hashes;
- account resolution;
- authoritative date-overlap supersession;
- exact source-file protection;
- preservation of identical rows.

Exit criterion met: overlapping layouts can populate one canonical active dataset without row-value deduplication.

## Phase 2 — generator version 2

Implemented:

- minimal seed/date interface;
- seeded random archetype when unspecified;
- optional archetype/questionnaire priors;
- hierarchical child seeds;
- hidden continuous profile;
- current/savings accounts;
- income, housing, bills, subscriptions, groceries, dining, transport, shopping, health, shocks and paired transfers;
- inflation;
- multiple statement formats;
- private ground truth;
- real/synthetic shared importer.

Exit criterion met: same inputs produce identical statement content and different seeds produce different financial lives.

## Phase 3 — descriptive analysis and CLI

Implemented:

- total balance;
- income, external spend and net cash flow;
- savings rate;
- current-month and yearly spend;
- weighted monthly spend;
- month-end projection;
- account summaries and histories;
- transaction table;
- text and JSON CLI outputs.

Exit criterion met: imported and generated users expose the same result contracts.

## Phase 4 — dashboard foundation

Implemented:

- central Streamlit navigation;
- profile selection;
- Data & Setup, Overview, Accounts and Transactions;
- light/dark design tokens;
- chart builders;
- shared application services;
- widget registry scaffold;
- persisted Overview layouts.

Exit criterion met at code level. Streamlit remains an optional dependency and must be installed with the dashboard extra.

## Phase 5 — categories and cash flow

Implemented:

- standard taxonomy;
- custom categories;
- manual precedence;
- user text/regex rules;
- built-in keyword categorisation;
- explicit ChatGPT export package and reviewed-suggestion import;
- exact-amount/date/description transfer confidence;
- paired transfer groups with durable manual confirmation/rejection;
- external metric exclusion;
- category charts and cash-flow Sankey payloads/pages.

Exit criterion met: transfer movements no longer inflate external income/spend, and the user retains category control.
