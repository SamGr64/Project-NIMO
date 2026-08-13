# Phase 6–11 implementation

## Phase 6 — behaviour inference

Implemented modules:

```text
analysis/periodicity.py
analysis/distributions.py
analysis/outliers.py
analysis/behaviours.py
analysis/archetypes.py
application/services/behaviour_service.py
```

The engine groups transactions by category, merchant and account. It records weekly/monthly/yearly timing, amount stability, candidate distribution fits, outlier evidence and independent periodic/distributional/spontaneous scores. The resulting archetype is a descriptive summary, not a risk class.

## Phase 7 — forecasting

Implemented modules:

```text
forecasting/profile_builder.py
forecasting/scenarios.py
forecasting/monte_carlo.py
forecasting/backtesting.py
application/services/forecast_service.py
```

A default profile is inferred automatically. User scenario overrides use dotted paths and retain provenance. Planned events support amount uncertainty, probability and repeating intervals. Stored simulations use deterministic seeds and compressed path arrays.

## Phase 8 — budgets and goals

Implemented modules:

```text
planning/budgets.py
planning/goals.py
application/services/planning_service.py
```

The default category budget is inferred from recent history. User budgets are separate objects. Budget evaluation estimates the probability that simulated next-month category spend remains within each limit. Goals support fixed and surplus-linked contributions plus intervention comparisons.

## Phase 9 — reporting

Implemented modules:

```text
reporting/context_builder.py
reporting/schemas.py
reporting/llm/{offline,openai_provider}.py
reporting/renderers/{html,markdown,pdf,document}.py
application/services/report_service.py
```

NIMO owns evidence, calculations and layout. Offline synthesis works without an API. The optional OpenAI adapter requests a schema-validated `ReportNarrative` and cannot alter stored metrics.

## Phase 10 — investing sandbox

Implemented modules:

```text
investing/providers/
investing/statistics.py
investing/simulator.py
investing/data/educational_market.csv
application/services/investment_service.py
```

The local provider exposes a clearly marked synthetic dataset. The simulator uses joint historical monthly return bootstrapping, portfolio weights, fees, user contribution rules and forecast cash-flow paths. Stress presets affect returns, income or cash flow.

## Phase 11 — hardening

Implemented modules and operations:

```text
storage/migrations/
storage/audit.py
storage/versioning.py
hardening/backups.py
hardening/doctor.py
scripts/benchmark_behaviour_recovery.py
scripts/calibrate_forecasts.py
scripts/benchmark_performance.py
.github/workflows/
```

Backups include a hash manifest, consistent SQLite snapshot, safe extraction checks and optional password encryption. Paths persisted by new runs are workspace-relative. CI targets Windows and Ubuntu and tests packaging as well as the application workflow.
