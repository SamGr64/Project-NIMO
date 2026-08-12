# Repository structure and file responsibilities

## Root

```text
Project-NIMO/
├── pyproject.toml          package metadata, dependencies, CLI entry point and test/lint settings
├── README.md               setup, user guide and current phase status
├── CHANGELOG.md            release-level changes
├── .env.example            documented optional environment variables
├── .streamlit/config.toml  static Streamlit server/browser settings only
├── architecture/           contracts, roadmap and editable Draw.io schematics
├── config/                 global defaults, priors, taxonomy, layouts and design tokens
├── prompts/                versioned optional LLM instructions; never core calculations
├── data/                   local per-user workspaces
├── dashboard/              Streamlit presentation layer
├── src/nimo/               installable application package
├── tests/                  unit, integration and statistical verification
└── scripts/                reproducible maintenance and benchmark commands
```

## Configuration

```text
config/
├── app.yaml                    application, path, storage and privacy defaults
├── generator.yaml              population-level ranges and generator defaults
├── archetypes.yaml             broad trait ranges, not fixed people
├── questionnaire.yaml          intuitive answers mapped to trait-range constraints
├── statement_formats.yaml      aliases and renderer layouts
├── categories.yaml             built-in category hierarchy and keywords
├── analysis.yaml               transfer thresholds and metric defaults
├── forecasting.yaml            future Phase 7 defaults
├── budgeting.yaml              future Phase 8 defaults
├── reporting.yaml              future Phase 9 defaults
├── investing.yaml              future Phase 10 defaults
├── dashboard/default_layouts.yaml
└── themes/light.yaml, dark.yaml
```

All files are loaded by `nimo.config.ConfigManager`. Core services receive parsed mappings from the application container rather than reading YAML independently.

## Core source package

### `src/nimo/application/`

- `container.py` constructs one user-scoped service graph.
- `services/user_service.py` creates workspaces/databases.
- `services/ingestion_service.py` wraps import plus optional categorisation/transfer refresh.
- `services/generation_service.py` coordinates profile → simulation → render → import.
- `services/analysis_service.py` exposes interface-safe DataFrames and metric objects.
- `services/layout_service.py` persists page widget choices.

Dependencies: config, workspaces, storage, generation, ingestion, analysis and categorisation. Interface layers depend on this package.

### `src/nimo/config/`

- `models.py` contains typed app/theme schemas.
- `loader.py` discovers the project and loads YAML mappings.

Dependencies: Pydantic and PyYAML only.

### `src/nimo/users/`

- `workspace.py` validates user slugs and owns folder/profile creation.

Dependencies: standard library and PyYAML. It does not open the database.

### `src/nimo/storage/`

- `models.py` defines SQLAlchemy tables.
- `database.py` owns SQLite engines and transaction-scoped sessions.
- `repositories/accounts.py`, `transactions.py`, `categories.py`, `layouts.py` contain reusable data access.
- `migrations/` is reserved for explicit versioned migrations before schema-breaking releases.

Dependencies: SQLAlchemy and pandas in the transaction-frame repository.

### `src/nimo/ingestion/`

- `csv_reader.py` reads common delimiters.
- `mappings.py` resolves aliases and amount shapes.
- `normalise.py` creates canonical rows and account metadata.
- `pipeline.py` applies file hashing, raw-file copying, account/date supersession and inserts.

Dependencies: pandas, storage repositories, user workspace and `statement_formats.yaml` supplied by the container.

### `src/nimo/generation/`

- `seeds.py` derives stable component seeds.
- `latent_profile.py` samples a continuous hidden profile.
- `accounts.py` creates the seeded account ecosystem.
- `processes/` contains reusable process primitives.
- `simulator.py` composes financial processes and running balances.
- `renderers/csv_renderer.py` creates varied observable statements.
- `truth.py` writes private validation truth.

Dependencies: NumPy/pandas and generator/archetype/questionnaire/statement configuration supplied by the service. It does not write to SQLite directly.

### `src/nimo/categorisation/`

- `taxonomy.py` flattens standard and child category definitions.
- `service.py` creates categories, applies precedence, manages rules/manual assignments and builds explicit LLM export packages.

Dependencies: storage and prompt files. No external model is called in Phase 5.

### `src/nimo/analysis/`

- `overview.py` calculates headline and monthly metrics.
- `accounts.py` builds account summaries and balances.
- `categories.py` builds category tables/timelines.
- `transfers.py` matches opposite account movements with confidence.
- `cashflow.py` constructs external and internal Sankey links.

Dependencies: canonical active transactions and storage for transfer pairs. It never reads `synthetic/ground_truth.json`.

### `src/nimo/cli/`

- `main.py` registers commands and shared root options.
- `common.py` resolves containers and formats text/JSON.
- `commands/` contains one argument/handler module per capability.

Dependencies: application services only; no direct SQL or calculations.

### Future namespaces

- `forecasting/` — Phase 7;
- `planning/` — Phase 8;
- `reporting/` — Phase 9;
- `investing/` — Phase 10.

They are explicit scaffolds and do not claim implemented behaviour.

## Dashboard

```text
dashboard/
├── app.py                   page configuration, user/theme bootstrap and navigation
├── pages/                   one page-composition module per navigation destination
└── lib/
    ├── bootstrap.py         selected profile and application container
    ├── context.py           shared page context
    ├── services.py          dashboard-facing service facade
    ├── charts/              Plotly builders
    ├── filters/             reusable filtering controls
    ├── layout/              layout editor and persistence calls
    ├── themes/              YAML tokens → CSS/Plotly layout
    ├── widgets/             stable widget registry
    ├── components/          future reusable cards/tables/alerts
    └── forms/               future shared forms
```

Pages can call services and chart builders. They cannot query SQLAlchemy or calculate financial metrics.

## Tests

```text
tests/
├── conftest.py                         isolated temporary workspaces
├── unit/                               focused deterministic behaviour
├── integration/                        multi-module pipelines and CLI
├── statistical/                        population-level seeded variation
├── contract/                           future provider contracts
├── regression/                         future saved output/schema checks
└── e2e/                                future dashboard/browser smoke tests
```

Current tests cover config, seeds, generator reproducibility, overlap safety, identical rows, categories, transfers, layouts, CLI and population variation.
