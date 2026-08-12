# NIMO sample user

This workspace is fully synthetic and reproducible. It is safe to use for dashboard, CLI and analysis development.

- Seed: `42`
- Date range: `2024-01-01` to `2026-07-31`
- Seed-selected archetype: `variable_income`
- Imported transactions: `1606`
- Accounts: `2`

Rebuild from the repository root with:

```bash
python scripts/rebuild_sample_user.py
```

The analysis code receives only the rendered statement files and normalized database. Hidden generator truth remains under `synthetic/` for future validation and must not be read by analysis services.
