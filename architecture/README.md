# Project NIMO architecture

This directory contains the executable architecture contracts for Project NIMO 1.0.0. The Markdown documents define module ownership, data boundaries, persistence and process rules. The `.drawio` files are editable diagrams.net schematics of the same system.

## Reading order

1. [`system_context.md`](system_context.md) — system purpose, interfaces and trust boundaries.
2. [`repository_structure.md`](repository_structure.md) — directory and file responsibilities.
3. [`dependency_map.md`](dependency_map.md) — allowed dependency direction.
4. [`data_model.md`](data_model.md) — SQLite entities, versions and invalidation.
5. [`process_flow.md`](process_flow.md) — startup, import, inference, planning, reporting and backup flows.
6. [`generator_contract.md`](generator_contract.md) — minimal generator inputs and hidden-truth separation.
7. [`dashboard_contract.md`](dashboard_contract.md) and [`cli_contract.md`](cli_contract.md) — thin interface rules.
8. [`security_privacy.md`](security_privacy.md) and [`overlap_and_provenance.md`](overlap_and_provenance.md) — sensitive-data and statement-overlap invariants.
9. [`phase_6_to_11_implementation.md`](phase_6_to_11_implementation.md) — completed analytical/planning phases.
10. [`roadmap.md`](roadmap.md) and [`build_validation.md`](build_validation.md) — release state and validation.

## Editable schematics

- `system_context.drawio`
- `process_flow.drawio`
- `data_model.drawio`
- `generator_analysis_loop.drawio`
- `dashboard_architecture.drawio`
- `phase_roadmap.drawio`
- `behaviour_forecasting_loop.drawio`
- `planning_investing_flow.drawio`
- `reporting_security_flow.drawio`

The Markdown contracts are authoritative when a diagram and document disagree.
