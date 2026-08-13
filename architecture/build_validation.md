# Project NIMO 1.0.0 build validation

Validation date: **2026-08-10**

This document records the release checks performed for the completed Phase 0-11 baseline. The tests demonstrate that the implemented workflows execute coherently; they are not evidence that the statistical models are scientifically final or suitable for regulated financial use.

## Automated checks

- `python -m pytest -q`: **26 tests passed**.
- `python -m compileall -q src dashboard scripts`: completed without syntax errors.
- `python -m pip wheel . --no-deps --no-build-isolation`: built `project_nimo-1.0.0-py3-none-any.whl` successfully.
- All **15 YAML configuration/profile files** used by the release parsed successfully.
- All **9 editable `.drawio` files** parsed as valid diagrams.net XML.
- The bundled sample database passed `PRAGMA integrity_check` and `PRAGMA foreign_key_check`.
- The bundled sample database is at schema migration **11 of 11**.
- `nimo doctor sample_user` passed database, foreign-key, migration, raw-source hash, cache-reference and workspace-directory checks.
- Plotly smoke tests constructed and serialised **8 figures**: balance area, monthly income/spend, category bar, account composition, cash-flow Sankey, forecast fan, investment fan and budget-probability charts.
- A clean wheel installation completed an end-to-end CLI workflow covering generation, analysis, categories, behaviours, scenarios, forecasts, budgets, goals, investing, all four report formats, export, backup, restore and diagnostics.

The optional Ruff executable was not available in the offline validation image. Ruff is configured in `pyproject.toml`, pre-commit and GitHub Actions so it runs in a normal development/CI installation.

## Reproducible sample user

`data/sample_user` was rebuilt from:

- seed: `42`;
- date range: `2024-01-01` through `2026-07-31`;
- seed-selected archetype: `variable_income`;
- accounts: `2`;
- active transactions: `1,606`;
- behaviour maps: `1` current run;
- forecast: `12` months, `1,000` Monte Carlo paths;
- inferred budget: `10` lines;
- demonstration goal: `Emergency buffer`;
- investment sandbox: `10` years, `1,000` paths;
- report outputs: HTML, Markdown and PDF.

The demonstration goal has a target of `£18,000` by `2028-12-31`, starts at `£6,000`, and had a simulated completion probability of approximately **59.1%** under the bundled baseline. That value is a sample-model result, not a promise.

## End-to-end workflow coverage

The integration suite also verifies financial-twin questionnaire constraints and exercises:

```text
seeded profile
    -> rendered statements
    -> overlap-safe normalisation
    -> categories and transfers
    -> behaviour inference
    -> editable forecast scenario
    -> deterministic Monte Carlo paths
    -> budget and goal simulation
    -> investing sandbox
    -> HTML / Markdown / PDF / DOCX reports
    -> portable and encrypted backup
    -> restore and doctor checks
```

It also verifies that analysis output does not expose or read synthetic ground truth.

## Model diagnostic smoke results

The behaviour-recovery benchmark compares inferred category labels with private synthetic truth at a `0.35` score threshold. Across the bundled sample's 12 categories, F1 scores were:

| Dimension | F1 |
|---|---:|
| Periodic | 0.666667 |
| Distributional | 0.666667 |
| Spontaneous | 0.500000 |

These numbers are a small-sample diagnostic, not final acceptance thresholds.

A six-period rolling forecast diagnostic using 200 paths produced:

- 50% interval coverage: **16.7%**;
- 90% interval coverage: **83.3%**.

The result confirms the backtesting pipeline works and also shows why post-1.0 calibration remains an explicit roadmap item. The current uncertainty model should not be described as fully calibrated.

## Local performance smoke

A fresh 31-month synthetic profile was generated and imported, then analysed on the release container using 500 forecast and 500 investment paths:

| Operation | Elapsed seconds |
|---|---:|
| Generation and import | 0.664 |
| Behaviour inference | 1.600 |
| 24-month forecast | 0.205 |
| 10-year investment simulation | 0.231 |

These are environment-specific smoke timings, not performance guarantees.

## Report rendering QA

The sample PDF and DOCX renderers were exercised with the completed evidence package. Each file was rendered to page images and visually inspected after iteration.

Verified items included:

- no clipped or overlapping text;
- clean repeated headers for continued budget tables;
- readable metric cards and callouts;
- forecast uncertainty bands and labels;
- goals, investing, risks and action sections;
- consistent three-page output in both PDF and DOCX QA runs.

The release sample includes HTML, Markdown and PDF. DOCX remains available from `nimo report build ... --format docx`.

## Dashboard validation boundary

The offline execution image did not include the optional `streamlit` package, so a live Streamlit server was not launched during release validation. The dashboard modules were syntax-compiled, all shared chart builders were exercised against `sample_user`, page/service imports were covered by tests, and the CLI provides a clear installation error when Streamlit is absent.

On Windows PowerShell:

```powershell
python -m pip install -e ".[all,dev]"
nimo dashboard
```
