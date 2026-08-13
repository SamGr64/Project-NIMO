# NIMO design overview

NIMO is organised around one canonical financial dataset and two thin interfaces.

```text
CLI ───────┐
           ├── application services ── domain modules ── repositories ── user SQLite database
Dashboard ─┘
```

Neither the CLI nor dashboard calculates balances, categories, transfer matches or generator events. They validate user input, call shared services and present returned results.

## Product loop

```text
Generate or import
        ↓
Normalise and preserve provenance
        ↓
Describe accounts, balances and spending
        ↓
Categorise and reconcile transfers
        ↓
Infer behaviour                         Phase 6
        ↓
Build a default forecast                Phase 7
        ↓
Let the user edit scenarios
        ↓
Budget, goals and investment sandbox    Phases 8–10
        ↓
Evidence-led report and explanation     Phase 9
```

## Generator philosophy

The normal interface requires only a seed and date range. Archetypes and questionnaire answers alter broad priors rather than defining exact behaviours. The seed samples a continuous latent profile, accounts and stochastic financial processes.

Periodic, spontaneous and distributional are properties that may coexist within one process. Groceries can have a weekly preference, a lognormal amount distribution and occasional spontaneous large shops.

## Analysis philosophy

Generated and real statements pass through the same importer. The analysis engine never reads synthetic ground truth. This creates a future validation loop:

```text
hidden generator truth → rendered statements → inferred behavioural map → comparison benchmark
```

## User-control philosophy

NIMO provides usable defaults without forcing them. Categories, dashboard layouts, future forecast assumptions, budgets, goals and investment scenarios are intended to remain editable. Historical inference and user planning must be stored separately.
