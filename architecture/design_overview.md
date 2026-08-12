# NIMO design overview

NIMO is organised around one canonical financial dataset and two thin interfaces.

```text
CLI ───────┐
           ├── application services ── domain modules ── repositories ── user database
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

NIMO provides usable defaults without forcing them. Categories, dashboard layouts, future forecast assumptions, budgets, goals and investment scenarios are intended to remain editable. Historical inference and user planning must be stored separatel

# NIMO (Nexus Intelligence and Monetary Optimisation.)

Credits: Deposits
Debits: Withdrawals

## Phase 1: Statement Generators

For security reasons it is necessary to first build seeded random statements that protect designer and client confidentiality, whilst still allowing programmers to design frameworks around common user behaviours.

Generated statements can either be monthly, yearly, 5 years, or a custom date range (though this feature will come last as a product).

Statements are expected to have 3 timesscales of commonality (weekly, monthly, yearly) and 3 types of debit/ credit behaviours:

- **Periodic**: actions that repeat over the defined timescales. These are guaranteed, or highly likely, spends.
- **Spontaneous**: Unpredictable, irregular, generally large spends that cannot be forecast but are still fundementally probabilistic on larger timescales. Spontaneous spending probabilities are allowed to vary across the week, month or year but are nonetheless not guaranteed on a given day.
- **Distributional**: Spending patterns that obey a probabilistic (likely normal or bimodal) distributions over the defined timescales.

There are a total of 9 configurable modes of defined behaviours.

Naturally, the same action's value will inflate overtime as rates grow with inflation. For the purposes of this generator it will be assumed that prices grow at some compounding percentage over the course of the year. Over a yearly timescale it is anticipated that prices will have grown by the nominal inflation rate, ignoring fluctuations.

## Phase 2: Surface-level metrics

Balance over time
Historic monthly spending vs latest (+ simple forecast methods)
Yearly spending so far
Account pie chart

## Phase 3: Transaction analysis

1. Identify regular spends
2. Identify outlier/ irregular spends
3. Build expected spending distributions

## Phase 4 and onwards...

- Reports
- Budget tip of the week
- Look once a month?
- Small achievable targets
- Investing for dummies, simple stock marekt metrics, sandbox investing
- Saving goals
- Individual targets to get bills down
