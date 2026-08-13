# NIMO sample user

This workspace is fully synthetic and reproducible. It is safe to use for dashboard, CLI, forecasting, planning, reporting and investing-sandbox development.

- Seed: `42`
- Date range: `2024-01-01` to `2026-07-31`
- Seed-selected archetype: `variable_income`
- Imported transactions: `1606`
- Accounts: `2`

- Inferred archetype: `variable-income, high saver, evenly timed spender`
- Forecast horizon/runs: `12 months / 1000`
- Default budget lines: `10`
- Demo goal probability: `59.1%`
- Investment horizon/runs: `10 years / 1000`
- Included sample reports: `html, md, pdf`

Rebuild from PowerShell at the repository root with:

```powershell
python .\scripts\rebuild_sample_user.py
```

Add `--include-pdf` when the reports extra is installed. The analysis code receives only rendered statement files and the normalised database. Hidden generator truth remains under `synthetic/` for explicit validation tools and is never read by normal analysis services.
