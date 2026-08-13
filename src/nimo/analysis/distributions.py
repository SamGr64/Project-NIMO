from __future__ import annotations

import math
from typing import Any, Callable

import numpy as np
from scipy import stats
from scipy.special import logsumexp


def fit_amount_distributions(
    values: np.ndarray | list[float],
    *,
    candidates: list[str] | None = None,
    minimum_observations: int = 12,
) -> dict[str, Any]:
    data = np.asarray(values, dtype=float)
    data = np.abs(data[np.isfinite(data)])
    data = data[data >= 0]
    if len(data) == 0:
        return {"status": "no_data", "sample_count": 0, "best_fit": None, "candidates": []}
    if np.allclose(data, data[0]):
        return {
            "status": "fixed",
            "sample_count": int(len(data)),
            "best_fit": {"family": "fixed", "parameters": {"value": float(data[0])}, "aic": 0.0, "ks_statistic": 0.0, "ks_pvalue": 1.0},
            "candidates": [],
            "distributional_score": 0.0,
        }
    if len(data) < minimum_observations:
        return {
            "status": "insufficient_data",
            "sample_count": int(len(data)),
            "best_fit": None,
            "candidates": [],
            "empirical": _empirical(data),
            "distributional_score": round(float(min(0.35, len(data) / max(1, minimum_observations) * 0.35)), 6),
        }

    candidates = candidates or ["normal", "lognormal", "gamma", "exponential", "bimodal_normal"]
    fits: list[dict[str, Any]] = []
    for family in candidates:
        try:
            fitted = _fit_one(family, data)
        except (ValueError, FloatingPointError, OverflowError, ZeroDivisionError):
            continue
        if fitted is not None and math.isfinite(float(fitted["aic"])):
            fits.append(fitted)
    fits.sort(key=lambda item: float(item["aic"]))
    best = fits[0] if fits else None
    cv = float(np.std(data, ddof=1) / np.mean(data)) if np.mean(data) > 0 else 0.0
    fit_quality = 0.0 if best is None else max(0.0, 1.0 - min(1.0, float(best["ks_statistic"]) * 2.0))
    distributional_score = min(1.0, (cv / 0.6) * fit_quality)
    return {
        "status": "fit" if best else "failed",
        "sample_count": int(len(data)),
        "best_fit": best,
        "candidates": fits,
        "empirical": _empirical(data),
        "distributional_score": round(float(distributional_score), 6),
    }


def sample_distribution(fit: dict[str, Any] | None, rng: np.random.Generator, size: int) -> np.ndarray:
    if not fit:
        return np.zeros(size, dtype=float)
    family = fit.get("family")
    params = fit.get("parameters", {})
    if family == "fixed":
        return np.full(size, float(params.get("value", 0.0)))
    if family == "normal":
        return np.maximum(0.0, rng.normal(float(params["loc"]), float(params["scale"]), size))
    if family == "lognormal":
        return rng.lognormal(float(params["log_mean"]), float(params["log_sigma"]), size)
    if family == "gamma":
        return rng.gamma(float(params["shape"]), float(params["scale"]), size)
    if family == "exponential":
        return rng.exponential(float(params["scale"]), size)
    if family == "bimodal_normal":
        weights = np.asarray(params["weights"], dtype=float)
        component = rng.choice(2, p=weights / weights.sum(), size=size)
        means = np.asarray(params["means"], dtype=float)
        scales = np.asarray(params["scales"], dtype=float)
        return np.maximum(0.0, rng.normal(means[component], scales[component]))
    return np.zeros(size, dtype=float)


def _fit_one(family: str, data: np.ndarray) -> dict[str, Any] | None:
    if family == "normal":
        loc, scale = stats.norm.fit(data)
        scale = max(float(scale), 1e-9)
        log_likelihood = float(np.sum(stats.norm.logpdf(data, loc=loc, scale=scale)))
        # Use a closure-based CDF so ks.test only sees a callable that already
        # applies the fitted loc/scale parameters. This avoids SciPy's internal
        # special-case mapping of "norm" to special.ndtr.
        normal_cdf = lambda x, loc=loc, scale=scale: stats.norm.cdf(x, loc=loc, scale=scale)
        ks = stats.kstest(data, normal_cdf)
        return _fit_payload(family, {"loc": float(loc), "scale": scale}, log_likelihood, 2, ks)
    if family == "lognormal":
        positive = data[data > 0]
        if len(positive) != len(data):
            return None
        shape, loc, scale = stats.lognorm.fit(positive, floc=0)
        log_likelihood = float(np.sum(stats.lognorm.logpdf(positive, shape, loc=loc, scale=scale)))
        lognormal_cdf = lambda x, shape=shape, loc=loc, scale=scale: stats.lognorm.cdf(x, shape, loc=loc, scale=scale)
        ks = stats.kstest(positive, lognormal_cdf)
        return _fit_payload(family, {"shape": float(shape), "loc": float(loc), "scale": float(scale), "log_mean": float(math.log(scale)), "log_sigma": float(shape)}, log_likelihood, 2, ks)
    if family == "gamma":
        positive = data[data > 0]
        if len(positive) != len(data):
            return None
        shape, loc, scale = stats.gamma.fit(positive, floc=0)
        log_likelihood = float(np.sum(stats.gamma.logpdf(positive, shape, loc=loc, scale=scale)))
        gamma_cdf = lambda x, shape=shape, loc=loc, scale=scale: stats.gamma.cdf(x, shape, loc=loc, scale=scale)
        ks = stats.kstest(positive, gamma_cdf)
        return _fit_payload(family, {"shape": float(shape), "loc": float(loc), "scale": float(scale)}, log_likelihood, 2, ks)
    if family == "exponential":
        positive = data[data >= 0]
        loc, scale = stats.expon.fit(positive, floc=0)
        log_likelihood = float(np.sum(stats.expon.logpdf(positive, loc=loc, scale=scale)))
        expon_cdf = lambda x, loc=loc, scale=scale: stats.expon.cdf(x, loc=loc, scale=scale)
        ks = stats.kstest(positive, expon_cdf)
        return _fit_payload(family, {"loc": float(loc), "scale": float(scale)}, log_likelihood, 1, ks)
    if family == "bimodal_normal":
        return _fit_bimodal(data)
    return None


def _fit_payload(family: str, parameters: dict[str, Any], log_likelihood: float, parameter_count: int, ks: Any) -> dict[str, Any]:
    return {
        "family": family,
        "parameters": parameters,
        "log_likelihood": round(log_likelihood, 6),
        "aic": round(float(2 * parameter_count - 2 * log_likelihood), 6),
        "ks_statistic": round(float(ks.statistic), 6),
        "ks_pvalue": round(float(ks.pvalue), 6),
    }


def _fit_bimodal(data: np.ndarray) -> dict[str, Any] | None:
    if len(data) < 16:
        return None
    means = np.array([np.quantile(data, 0.30), np.quantile(data, 0.75)], dtype=float)
    scales = np.array([max(np.std(data) * 0.55, 1e-3), max(np.std(data) * 0.55, 1e-3)], dtype=float)
    weights = np.array([0.5, 0.5], dtype=float)
    responsibilities = np.zeros((len(data), 2), dtype=float)
    for _ in range(100):
        previous = means.copy()
        log_components = np.column_stack([
            math.log(max(weights[index], 1e-9)) + stats.norm.logpdf(data, means[index], scales[index])
            for index in range(2)
        ])
        normaliser = logsumexp(log_components, axis=1)
        responsibilities = np.exp(log_components - normaliser[:, None])
        totals = responsibilities.sum(axis=0)
        weights = totals / len(data)
        means = (responsibilities * data[:, None]).sum(axis=0) / np.maximum(totals, 1e-9)
        variances = (responsibilities * (data[:, None] - means) ** 2).sum(axis=0) / np.maximum(totals, 1e-9)
        scales = np.sqrt(np.maximum(variances, 1e-6))
        if np.max(np.abs(means - previous)) < 1e-7:
            break
    order = np.argsort(means)
    means, scales, weights = means[order], scales[order], weights[order]
    if abs(means[1] - means[0]) < 0.35 * np.std(data):
        return None
    log_components = np.column_stack([
        math.log(max(weights[index], 1e-9)) + stats.norm.logpdf(data, means[index], scales[index])
        for index in range(2)
    ])
    log_likelihood = float(np.sum(logsumexp(log_components, axis=1)))

    def cdf(value: np.ndarray) -> np.ndarray:
        return weights[0] * stats.norm.cdf(value, means[0], scales[0]) + weights[1] * stats.norm.cdf(value, means[1], scales[1])

    ordered = np.sort(data)
    empirical = np.arange(1, len(ordered) + 1) / len(ordered)
    ks_statistic = float(np.max(np.abs(empirical - cdf(ordered))))
    return {
        "family": "bimodal_normal",
        "parameters": {
            "weights": [round(float(value), 8) for value in weights],
            "means": [round(float(value), 8) for value in means],
            "scales": [round(float(value), 8) for value in scales],
        },
        "log_likelihood": round(log_likelihood, 6),
        "aic": round(float(2 * 5 - 2 * log_likelihood), 6),
        "ks_statistic": round(ks_statistic, 6),
        "ks_pvalue": None,
    }


def _empirical(data: np.ndarray) -> dict[str, float]:
    return {
        "mean": round(float(np.mean(data)), 6),
        "median": round(float(np.median(data)), 6),
        "std": round(float(np.std(data, ddof=1)) if len(data) > 1 else 0.0, 6),
        "q05": round(float(np.quantile(data, 0.05)), 6),
        "q25": round(float(np.quantile(data, 0.25)), 6),
        "q75": round(float(np.quantile(data, 0.75)), 6),
        "q95": round(float(np.quantile(data, 0.95)), 6),
        "minimum": round(float(np.min(data)), 6),
        "maximum": round(float(np.max(data)), 6),
    }
