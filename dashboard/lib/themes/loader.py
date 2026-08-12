from __future__ import annotations

from typing import Any

from nimo.config.models import ThemeConfig


def apply_theme(st, theme: ThemeConfig) -> None:
    css = f"""
    <style>
    :root {{
      --nimo-bg: {theme.surface.background};
      --nimo-surface: {theme.surface.primary};
      --nimo-surface-alt: {theme.surface.secondary};
      --nimo-text: {theme.text.primary};
      --nimo-text-muted: {theme.text.secondary};
      --nimo-primary: {theme.brand.primary};
      --nimo-accent: {theme.brand.accent};
      --nimo-border: {theme.border};
    }}
    .stApp {{ background: var(--nimo-bg); color: var(--nimo-text); }}
    [data-testid="stMetric"], .nimo-card {{
      background: var(--nimo-surface);
      border: 1px solid var(--nimo-border);
      border-radius: 0.75rem;
      padding: 0.75rem;
    }}
    [data-testid="stSidebar"] {{ background: var(--nimo-surface); }}
    .nimo-muted {{ color: var(--nimo-text-muted); }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


def plotly_layout(theme: ThemeConfig) -> dict[str, Any]:
    return {
        "paper_bgcolor": theme.surface.background,
        "plot_bgcolor": theme.surface.background,
        "font": {"color": theme.text.primary},
        "colorway": theme.charts.categorical,
        "margin": {"l": 24, "r": 24, "t": 48, "b": 32},
        "legend": {"orientation": "h"},
    }
