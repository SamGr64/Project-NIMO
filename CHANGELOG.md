# Changelog

Changes to Project NIMO and its codebase are recorded in this version-control file.
- Patches (_._.X)  : Minor bug fixes and syntax edits
- Minor (_.X._)    : Incremental features and isolated functionality/ procedural adjustments that are backwards-compatible
- Major (X._._)    : Significant breaking features or codebase updates that are not backwards-compatible 

## [Unreleased]

- Forecasting
- Simplified UX

## [0.5.0] — Phase 0–5 foundation

- Replaced the restrictive single-policy generator with a seeded latent-profile simulator.
- Added stable child seeds for independent generator components.
- Added periodic, distributional, spontaneous, shock and paired-transfer processes.
- Added multiple seeded statement renderers and a shared real/synthetic import path.
- Added per-user workspaces and SQLite databases.
- Added authoritative account/date overlap supersession while preserving identical rows.
- Added provenance for source files and superseded transactions.
- Added standard and custom categories, manual overrides, user rules and export packages.
- Added internal-transfer matching with confidence and cash-flow payloads.
- Added overview, accounts, transactions, categories and cash-flow analysis services.
- Added a shared CLI and Streamlit dashboard foundation.
- Added light/dark design-token configuration and persisted dashboard layouts.
- Added architecture documentation, roadmap and editable Draw.io schematics.
- Added unit, integration and statistical tests.

## [0.1.2] 09-08-2026

- Changed statement generator to have periodic, spontaneous, and distributional behaviours across weekly, monthly and yearly timescales.

## [0.1.1] 07-08-2026

- Minor bug fixes and description field adjustments to the statement generator.

## [0.1.0] 06-08-2026

- First committed version of simple generator, uses seeded random generation to produce artificial statements for secure feature production and testing.
