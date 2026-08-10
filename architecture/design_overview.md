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
