from __future__ import annotations


def apply_layout(fig, layout: dict):
    fig.update_layout(**layout)
    return fig
