# System context

## Purpose

Project NIMO is a local-first personal-finance modelling application. It supports two data entry paths:

```text
seeded synthetic statements ──┐
                              ├──► normalised per-user transaction database
real user CSV statements ─────┘
```

The normalised database supports descriptive analysis, categorisation, cash-flow reconciliation, behaviour inference, forecasting, budgeting, savings goals, reporting and an educational investing sandbox.

## Interfaces

- **CLI:** complete bare-bones access to all application services.
- **Streamlit dashboard:** interactive page and widget composition.
- **Scripts:** benchmarks, calibration, sample rebuilding and migrations.

All interfaces call the same `ApplicationContainer` services. No interface owns business calculations.

## Core subsystems

```text
Generation / ingestion
        ↓
Normalised storage and provenance
        ↓
Descriptive analysis + categorisation + transfers
        ↓
Behavioural map
        ↓
Forecast profile + user scenarios
        ↓
Budgets, goals and investing simulations
        ↓
Structured report evidence
        ↓
Offline or optional OpenAI narrative
```

## External boundaries

- **OpenAI:** optional report narrative provider; disabled by default.
- **Market data:** provider interface; version 1.0 ships a synthetic local dataset.
- **File formats:** CSV import, CSV/JSON export, HTML/Markdown/PDF/DOCX reports, ZIP/encrypted backup archives.

## Trust boundaries

1. Real statements and user databases are sensitive local data.
2. Synthetic hidden truth is private to generation/benchmarking and is never consumed by analysis.
3. LLM prose cannot modify calculations; it receives a frozen structured evidence package.
4. Investment simulations are educational and cannot place trades.
5. Dashboard/CLI inputs are validated at service boundaries before persistence.
