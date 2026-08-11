# Generator contract

## Public input

Required:

- `seed`;
- `start_date`;
- `end_date`.

Optional:

- broad archetype prior;
- questionnaire answers that constrain trait ranges;
- statement rendering format.

No individual salary, rent, merchant, occurrence rate or transaction amount must be configured for normal generation.

## Hidden output

The latent profile includes continuous traits such as:

- income stability;
- savings propensity;
- discretionary intensity;
- spending volatility;
- weekend preference;
- shock exposure;
- subscription tendency;
- price sensitivity.

The generator creates a particular person by sampling within broad prior ranges using the seed.

## Seed isolation

```text
master seed
├── latent-profile
├── accounts
├── income
├── housing
├── bills
├── subscriptions
├── groceries
├── dining
├── transport
├── shopping
├── health
├── shocks
├── transfers
└── renderer:<account>
```

Child seeds use a stable hash of the master seed and namespace. Adding a random draw to dining should not alter the salary or account numbers.

## Behaviour composition

A process may expose several properties at once:

```text
Groceries
  occurrence: weekly distributional with weekday weights
  amount: lognormal
  periodic property: weekend tendency
  spontaneous property: rare large shop
  annual property: inflation and future seasonality
```

The generator records hidden process truth but the statement renderer removes those labels.

## Reproducibility

Given the same generator version, seed, date range, archetype/questionnaire and statement format, rendered statement content must be reproducible. Timestamps and user-workspace paths are provenance rather than generator output.
