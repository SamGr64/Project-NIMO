# Program process flow

## 1. Startup

```text
start CLI/dashboard
  → discover project root
  → load typed YAML configuration
  → select/create user workspace
  → open SQLite
  → apply idempotent migrations 1–11
  → create repositories/provider adapters/application services
  → ensure category taxonomy
  → ready
```

## 2. Synthetic generation

```text
seed + date range + optional archetype/questionnaire
  → sample continuous latent behavioural profile
  → derive stable child seeds by namespace
  → create accounts and financial processes
  → simulate periodic/distributional/spontaneous/shock/transfer events
  → apply inflation and running balances
  → store private hidden truth
  → render varied bank-style CSV statements
  → import through the normal statement pipeline
  → automatic categories and transfer matching
  → active canonical transactions
```

A renderer or behaviour algorithm can change without changing unrelated child-seed streams.

## 3. Real statement import

```text
CSV selected
  → compute SHA-256 and store immutable raw copy
  → detect columns/amount shape
  → normalise signed amounts, dates, descriptions and balances
  → resolve account
  → determine new statement min/max booking-date coverage
  → retire older active rows for the same account/date interval
  → insert every new row (never equality-deduplicate)
  → categorise and refresh transfer candidates
```

## 4. Analysis and behaviour

```text
active canonical transactions
  → exclude confirmed/matched internal transfers from external cash flow
  → descriptive metrics/accounts/categories/cash-flow network
  → account/category/merchant grouping
  → weekly/monthly/yearly periodicity
  → candidate amount-distribution fitting
  → robust outlier and contextual surprise scoring
  → behavioural map
  → descriptive archetype label
```

Periodic, distributional and spontaneous are independent dimensions; one category may exhibit all three.

## 5. Forecasting

```text
behavioural map + historical monthly aggregates
  → inferred default ForecastProfile with provenance
  → Baseline scenario
  → optional user overrides and planned events
  → resolved scenario
  → deterministic-seed Monte Carlo paths
  → balance/income/spend/category intervals and threshold probabilities
  → compressed path cache + SQLite summary
  → rolling historical backtest when requested
```

The user edits the forecast profile or scenario; the behavioural map remains historical evidence.

## 6. Budgets and goals

```text
recent categorised history
  → inferred baseline budget
  → user copies/edits/adds lines
  → one-month forecast samples
  → probability within each budget line

forecast scenario + goal definition
  → monthly fixed/surplus-linked contributions
  → goal value paths
  → probability achieved + completion-month range
  → optional category-reduction intervention comparison
```

## 7. Investing sandbox

```text
forecast cash-flow paths
  + user portfolio
  + contribution rule
  + synthetic educational return history
  + optional stress preset
  → joint monthly return bootstrap
  → investment value paths
  → cash balances after contributions
  → range, drawdown, contribution and liquidity statistics
```

Threshold and goal-aware contribution rules are sequential so the same surplus cash is not invested repeatedly.

## 8. Reporting

```text
selected period
  → freeze historical facts + behaviour + assumptions + simulations
  → build structured evidence package
  → offline narrative OR optional OpenAI structured narrative
  → validate ReportNarrative schema
  → NIMO renders charts/tables/prose to HTML/Markdown/PDF/DOCX
  → store evidence, narrative, output paths and data version
```

## 9. Backup, restore and diagnostics

```text
workspace
  → consistent SQLite snapshot
  → portable relative source/report/cache references
  → optional omission of rebuildable caches
  → hash manifest
  → ZIP or encrypted .nimoenc

restore
  → verify CRC and file hashes
  → block unsafe archive paths
  → copy files and recreate required directories
  → initialise/migrate database
  → run doctor checks
```

`nimo doctor` checks SQLite integrity, foreign keys, schema version, raw-source hashes, cache references and workspace directories.
