from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

from nimo.generation.seeds import child_seed


TRAITS = (
    "income_stability",
    "savings_propensity",
    "discretionary_intensity",
    "spending_volatility",
    "weekend_bias",
    "shock_exposure",
)


@dataclass(frozen=True, slots=True)
class LatentProfile:
    seed: int
    archetype: str
    monthly_income: float
    income_stability: float
    savings_propensity: float
    discretionary_intensity: float
    spending_volatility: float
    weekend_bias: float
    shock_exposure: float
    payday: int
    housing_ratio: float
    annual_inflation: float
    subscription_tendency: float
    price_sensitivity: float

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _uniform(rng: np.random.Generator, bounds: list[float] | tuple[float, float]) -> float:
    return float(rng.uniform(float(bounds[0]), float(bounds[1])))


def sample_latent_profile(
    *,
    seed: int,
    generator_config: dict[str, Any],
    archetypes_config: dict[str, Any],
    questionnaire_config: dict[str, Any] | None = None,
    archetype: str | None = None,
    questionnaire: dict[str, str] | None = None,
) -> LatentProfile:
    rng = np.random.default_rng(child_seed(seed, "latent-profile"))
    archetypes = archetypes_config.get("archetypes", {})
    if not archetypes:
        raise ValueError("No generator archetypes are configured")

    chosen = archetype or str(rng.choice(sorted(archetypes)))
    if chosen not in archetypes:
        raise ValueError(f"Unknown archetype {chosen!r}; choose from {', '.join(sorted(archetypes))}")

    population = generator_config.get("population_priors", {})
    trait_ranges: dict[str, list[float]] = {}
    archetype_traits = archetypes[chosen].get("traits", {})
    for trait in TRAITS:
        general = population.get(trait, {"lower": 0.0, "upper": 1.0})
        trait_ranges[trait] = list(
            archetype_traits.get(trait, [general.get("lower", 0.0), general.get("upper", 1.0)])
        )

    if questionnaire and questionnaire_config:
        questions = {
            item["id"]: item for item in questionnaire_config.get("questions", [])
        }
        for question_id, answer_id in questionnaire.items():
            question = questions.get(question_id)
            if not question:
                continue
            answer = question.get("answers", {}).get(answer_id)
            if not answer:
                continue
            for trait, bounds in answer.get("trait_ranges", {}).items():
                if trait in trait_ranges:
                    current = trait_ranges[trait]
                    lower = max(float(current[0]), float(bounds[0]))
                    upper = min(float(current[1]), float(bounds[1]))
                    trait_ranges[trait] = [lower, upper] if lower <= upper else list(bounds)

    values = {trait: _uniform(rng, trait_ranges[trait]) for trait in TRAITS}
    income_cfg = population.get("monthly_income", {"minimum": 1400, "maximum": 6500})
    income_min = float(income_cfg.get("minimum", 1400))
    income_max = float(income_cfg.get("maximum", 6500))
    # A triangular draw avoids placing too many users at either extreme.
    monthly_income = float(rng.triangular(income_min, 3000.0, income_max))
    if chosen == "stable_saver":
        monthly_income *= float(rng.uniform(1.02, 1.25))
    elif chosen == "variable_income":
        monthly_income *= float(rng.uniform(0.85, 1.12))

    generation = generator_config.get("generation", {})
    inflation_mean = float(generation.get("annual_inflation_mean", 0.03))
    inflation_spread = float(generation.get("annual_inflation_spread", 0.012))
    annual_inflation = max(-0.01, float(rng.normal(inflation_mean, inflation_spread)))

    housing_ratio = float(
        np.clip(
            rng.normal(0.31 + 0.05 * values["discretionary_intensity"], 0.045),
            0.18,
            0.48,
        )
    )

    return LatentProfile(
        seed=seed,
        archetype=chosen,
        monthly_income=round(monthly_income, 2),
        income_stability=values["income_stability"],
        savings_propensity=values["savings_propensity"],
        discretionary_intensity=values["discretionary_intensity"],
        spending_volatility=values["spending_volatility"],
        weekend_bias=values["weekend_bias"],
        shock_exposure=values["shock_exposure"],
        payday=int(rng.integers(25, 29)),
        housing_ratio=housing_ratio,
        annual_inflation=annual_inflation,
        subscription_tendency=float(rng.beta(2 + 4 * values["discretionary_intensity"], 3)),
        price_sensitivity=float(rng.beta(2 + 4 * values["savings_propensity"], 3)),
    )
