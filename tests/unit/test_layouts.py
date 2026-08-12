def test_layout_customisation_persists(container) -> None:
    layout = {"headline_metrics": ["total_balance"], "widgets": ["balance_history"]}
    container.layouts.save("overview", layout)
    assert container.layouts.get("overview") == layout
