# Dashboard contract

## Pages

```text
Start
  Data & Setup

My Finances
  Overview
  Accounts
  Transactions
  Categories
  Cash Flow

Plan
  Forecasting & Scenarios
  Budgeting & Goals
  Investing

Insights
  Behaviours & Configuration
  Reporting & Advice
```

## Page rule

A page may:

- read global context and session state;
- collect user input;
- call application services;
- render shared components/charts;
- save layout preferences.

A page may not implement financial calculations, query SQL directly or read synthetic ground truth.

## Shared library

`dashboard/lib/` contains bootstrap/context, service facade, themes, filters, forms, charts, components, widget registry and layout persistence. `dashboard/pages/` only composes these features.

## Layout autonomy

Every implemented page has a default layout in `config/dashboard/default_layouts.yaml`. The layout service persists:

- selected headline metrics;
- selected widgets;
- widget ordering;
- page-specific configuration where supported.

A reset operation restores the project default. Layout changes never invalidate analysis.

## Themes

`config/themes/light.yaml` and `dark.yaml` define design tokens. The dashboard applies tokens to CSS and Plotly templates. User theme selection is stored in session/profile preferences; project designers retain control of the token files.

## Error boundary

Service exceptions are displayed as actionable errors without exposing statement content or secrets. Missing optional dependencies produce install guidance rather than import failures during core CLI use.
