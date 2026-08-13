from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import streamlit as st

from dashboard.lib.bootstrap import bootstrap_dashboard
from dashboard.lib.themes import apply_theme
from dashboard.pages import (
    accounts,
    behaviours_config,
    budgeting_goals,
    cash_flow,
    categories,
    data_setup,
    forecasting,
    investing,
    overview,
    reporting_advice,
    transactions,
)

st.set_page_config(page_title="Project NIMO", page_icon="£", layout="wide")
ctx = bootstrap_dashboard(st, PROJECT_ROOT)
apply_theme(st, ctx.config.theme(ctx.theme_name))

navigation = st.navigation(
    {
        "Start": [
            st.Page(
                lambda: data_setup.render(ctx),
                title="Data & Setup",
                icon=":material/upload_file:",
                url_path="data_setup",
            )
        ],
        "My Finances": [
            st.Page(
                lambda: overview.render(ctx),
                title="Overview",
                icon=":material/dashboard:",
                url_path="overview",
            ),
            st.Page(
                lambda: accounts.render(ctx),
                title="Accounts",
                icon=":material/account_balance:",
                url_path="accounts",
            ),
            st.Page(
                lambda: transactions.render(ctx),
                title="Transactions",
                icon=":material/receipt_long:",
                url_path="transactions",
            ),
            st.Page(
                lambda: categories.render(ctx),
                title="Categories",
                icon=":material/category:",
                url_path="categories",
            ),
            st.Page(
                lambda: cash_flow.render(ctx),
                title="Cash Flow",
                icon=":material/account_tree:",
                url_path="cash_flow",
            ),
        ],
        "Plan": [
            st.Page(
                lambda: forecasting.render(ctx),
                title="Forecasting & Scenarios",
                icon=":material/trending_up:",
                url_path="forecasting",
            ),
            st.Page(
                lambda: budgeting_goals.render(ctx),
                title="Budgeting & Goals",
                icon=":material/savings:",
                url_path="budgeting_goals",
            ),
            st.Page(
                lambda: investing.render(ctx),
                title="Investing",
                icon=":material/candlestick_chart:",
                url_path="investing",
            ),
        ],
        "Insights": [
            st.Page(
                lambda: behaviours_config.render(ctx),
                title="Behaviours & Configuration",
                icon=":material/psychology:",
                url_path="behaviours_config",
            ),
            st.Page(
                lambda: reporting_advice.render(ctx),
                title="Reporting & Advice",
                icon=":material/description:",
                url_path="reporting_advice",
            ),
        ],
    }
)
navigation.run()
