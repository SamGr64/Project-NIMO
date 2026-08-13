from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from nimo.analysis.distributions import fit_amount_distributions, sample_distribution
from nimo.analysis.outliers import score_outliers
from nimo.analysis.periodicity import detect_periodicity


def test_monthly_periodicity_and_amount_stability_are_detected() -> None:
    dates = pd.date_range("2024-01-28", periods=18, freq="ME")
    frame = pd.DataFrame(
        {
            "booking_date": dates,
            "amount": [-1250.0] * len(dates),
        }
    )
    result = detect_periodicity(frame)
    assert result["cadence"] == "monthly"
    assert result["cadence_scores"]["monthly"] > 0.8
    assert result["amount_stability"] == 1.0


def test_bimodal_distribution_can_be_selected_and_sampled() -> None:
    rng = np.random.default_rng(77)
    values = np.concatenate([rng.normal(18.0, 2.0, 200), rng.normal(62.0, 5.0, 160)])
    result = fit_amount_distributions(values, minimum_observations=12)
    assert result["status"] == "fit"
    assert result["best_fit"] is not None
    assert result["best_fit"]["family"] == "bimodal_normal"
    sample = sample_distribution(result["best_fit"], np.random.default_rng(12), 100)
    assert sample.shape == (100,)
    assert np.all(sample >= 0)


def test_normal_distribution_ks_test_uses_custom_loc_scale() -> None:
    rng = np.random.default_rng(42)
    values = rng.normal(12.0, 3.0, 1000)
    result = fit_amount_distributions(values, minimum_observations=12)
    assert result["status"] == "fit"
    assert result["best_fit"] is not None
    assert result["best_fit"]["family"] == "normal"
    assert float(result["best_fit"]["parameters"]["loc"]) == pytest.approx(12.0, abs=0.5)
    assert float(result["best_fit"]["parameters"]["scale"]) == pytest.approx(3.0, abs=0.5)


def test_outlier_scoring_flags_large_category_spend() -> None:
    frame = pd.DataFrame(
        {
            "id": list(range(1, 14)),
            "amount": [-20.0, -21.0, -19.0, -22.0, -20.0, -18.0, -23.0, -21.5, -20.5, -19.5, -22.5, -21.0, -250.0],
            "category_slug": ["restaurants"] * 13,
        }
    )
    scored = score_outliers(frame)
    flagged = scored.loc[scored["is_outlier"]]
    assert list(flagged["transaction_id"]) == [13]
    assert float(flagged.iloc[0]["surprise_score"]) > 0
