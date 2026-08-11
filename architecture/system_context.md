# System context

## Boundaries

NIMO is a local application with these principal boundaries:

```text
Users
  ├── CLI
  └── Streamlit dashboard
          │
          ▼
Application service layer
  ├── user workspaces
  ├── generation/import
  ├── analysis
  ├── categorisation
  └── layout persistence
          │
          ▼
Domain and data modules
          │
          ▼
One database per user
```

External LLM, market-data and report-rendering providers are future optional adapters. They must sit behind interfaces and may not become dependencies of the domain layer.

## Main packages

- `src/nimo/config` loads versioned YAML configuration.
- `src/nimo/users` manages workspace folders and profile metadata.
- `src/nimo/storage` owns the database schema and repositories.
- `src/nimo/ingestion` inspects, maps and normalises statement rows.
- `src/nimo/generation` creates latent profiles, transactions and rendered statements.
- `src/nimo/categorisation` manages taxonomies, rules and manual assignments.
- `src/nimo/analysis` computes descriptive, category, transfer and cash-flow results.
- `src/nimo/application` composes those modules into interface-safe services.
- `src/nimo/cli` and `dashboard/` are presentation layers.

## Configuration resolution

```text
project defaults
      ↓
user profile preferences
      ↓
page/scenario-specific settings
      ↓
immediate CLI or dashboard input
```

More specific values override broader defaults. The Phase 5 build implements project defaults, user profile preferences and dashboard layout overrides.
