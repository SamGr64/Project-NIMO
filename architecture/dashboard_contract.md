# Dashboard contract

## Folder boundary

```text
dashboard/pages/    page composition and user interactions
dashboard/lib/      reusable charts, widgets, themes, filters and layout controls
src/nimo/           all financial calculations, persistence and generation
```

A page may not open the SQLite database or reproduce core calculations.

## Navigation

Implemented pages:

- Data & Setup;
- Overview;
- Accounts;
- Transactions;
- Categories;
- Cash Flow, including manual transfer confirmation/rejection.

Scaffolded pages:

- Forecasting & Scenarios;
- Budgeting & Goals;
- Investing;
- User Behaviours & Configuration;
- Reporting & Advice.

## Widget contract

Each reusable widget should ultimately declare:

- stable widget id;
- title;
- supported pages;
- required service data;
- supported sizes/options;
- render callable.

Page layouts store widget ids and headline metric ids, never financial values.

## Layout customisation

The Phase 5 Overview supports:

- selecting headline metrics;
- selecting visible widgets;
- defining widget order;
- saving/restoring defaults.

The `LayoutService` and registry are reusable for all other pages.

## Themes

`config/themes/light.yaml` and `dark.yaml` are authoritative design-token sources. They control:

- application surfaces;
- primary and secondary text;
- brand colours;
- status colours;
- chart categorical palette;
- borders.

Streamlit’s static config is limited to server/browser settings.
