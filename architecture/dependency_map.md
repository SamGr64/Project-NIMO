# Dependency direction

## Allowed flow

```text
dashboard pages ─────┐
                     ├──► application services ──► domain/subsystems ──► repositories ──► SQLite
CLI commands ────────┘                 │
                                       ├──► workspace files
                                       └──► provider interfaces ──► optional adapters
```

## Layer responsibilities

### Interfaces

`dashboard/` and `src/nimo/cli/` validate immediate UI/argument shape, construct requests, call services and present results.

### Application services

`src/nimo/application/services/` coordinates use cases and transactions. It owns workflow ordering, persistence of results, stale-data decisions and service-level validation.

### Domain/subsystems

`generation`, `ingestion`, `analysis`, `forecasting`, `planning`, `investing` and `reporting` contain calculations that are independent of Streamlit and CLI formatting.

### Storage

`storage/models.py` defines persistence entities; repositories encapsulate reusable queries; migrations provide a schema ledger.

### Providers

LLM and market data adapters implement narrow protocols. The core can operate without network adapters.

## Forbidden imports

```text
analysis/forecasting/planning/investing → dashboard or Streamlit
core domain modules                    → CLI argparse objects
core calculations                       → synthetic/ground_truth.json
repositories                            → dashboard session state
report narrative provider               → raw SQL or calculation modules
dashboard pages                         → raw SQLAlchemy queries
```

## Configuration resolution

```text
global YAML defaults
        ↓
per-user profile model_overrides
        ↓
forecast/scenario or budget/portfolio settings
        ↓
immediate CLI/dashboard request
```

Later layers override earlier values without mutating historical inference.
