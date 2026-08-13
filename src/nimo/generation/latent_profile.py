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


def _population_ranges(generator_config: dict[str, Any]) -> dict[str, list[float]]:
    population = generator_config.get("population_priors", {})
    return {
        trait: [
            float(population.get(trait, {}).get("lower", 0.0)),
            float(population.get(trait, {}).get("upper", 1.0)),
        ]
        for trait in TRAITS
    }


def _archetype_ranges(
    *,
    chosen: str,
    population_ranges: dict[str, list[float]],
    archetypes: dict[str, Any],
) -> dict[str, list[float]]:
    archetype_traits = archetypes[chosen].get("traits", {})
    return {
        trait: list(archetype_traits.get(trait, population_ranges[trait]))
        for trait in TRAITS
    }


def _apply_questionnaire(
    trait_ranges: dict[str, list[float]],
    *,
    questionnaire: dict[str, str],
    questionnaire_config: dict[str, Any],
) -> None:
    questions = {
        str(item["id"]): item
        for item in questionnaire_config.get("questions", [])
        if isinstance(item, dict) and "id" in item
    }
    for question_id, answer_id in questionnaire.items():
        question = questions.get(question_id)
        if question is None:
            raise ValueError(f"Unknown questionnaire question {question_id!r}")
        answer = question.get("answers", {}).get(answer_id)
        if answer is None:
            available = ", ".join(sorted(question.get("answers", {})))
            raise ValueError(
                f"Unknown answer {answer_id!r} for question {question_id!r}; choose from {available}"
            )
        for trait, bounds in answer.get("trait_ranges", {}).items():
            if trait not in trait_ranges:
                continue
            current = trait_ranges[trait]
            lower = max(float(current[0]), float(bounds[0]))
            upper = min(float(current[1]), float(bounds[1]))
            # A questionnaire should still be usable when a separately selected
            # archetype has no overlap with an answer. In that case the direct
            # user answer is more authoritative than the broad archetype prior.
            trait_ranges[trait] = [lower, upper] if lower <= upper else [float(bounds[0]), float(bounds[1])]


def _nearest_archetype(values: dict[str, float], archetypes: dict[str, Any]) -> str:
    """Return a descriptive archetype nearest to a questionnaire-derived profile.

    Questionnaire mode begins from population priors rather than secretly choosing
    a hard archetype first. The resulting continuous traits are labelled only after
    sampling, which keeps the label descriptive rather than generative.
    """

    scores: list[tuple[float, str]] = []
    for name, payload in archetypes.items():
        traits = payload.get("traits", {})
        distance = 0.0
        compared = 0
        for trait in TRAITS:
            bounds = traits.get(trait)
            if not bounds:
                continue
            lower, upper = float(bounds[0]), float(bounds[1])
            midpoint = (lower + upper) / 2.0
            scale = max(upper - lower, 0.1)
            distance += ((values[trait] - midpoint) / scale) ** 2
            compared += 1
        if compared:
            scores.append((distance / compared, str(name)))
    if not scores:
        raise ValueError("No archetype trait ranges are configured")
    return min(scores)[1]


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
    if archetype is not None and archetype not in archetypes:
        raise ValueError(f"Unknown archetype {archetype!r}; choose from {', '.join(sorted(archetypes))}")
    if questionnaire and not questionnaire_config:
        raise ValueError("Questionnaire answers were supplied but no questionnaire configuration is available")

    population = generator_config.get("population_priors", {})
    population_ranges = _population_ranges(generator_config)

    # In ordinary random mode the seed selects a broad archetype prior. In twin
    # mode, answers constrain the full population first and the archetype label is
    # inferred afterwards. An explicitly selected archetype may also be refined by
    # questionnaire answers.
    chosen: str | None
    if archetype is not None:
        chosen = archetype
        trait_ranges = _archetype_ranges(
            chosen=chosen,
            population_ranges=population_ranges,
            archetypes=archetypes,
        )
    elif questionnaire:
        chosen = None
        trait_ranges = {key: list(value) for key, value in population_ranges.items()}
    else:
        chosen = str(rng.choice(sorted(archetypes)))
        trait_ranges = _archetype_ranges(
            chosen=chosen,
            population_ranges=population_ranges,
            archetypes=archetypes,
        )

    if questionnaire:
        _apply_questionnaire(
            trait_ranges,
            questionnaire=questionnaire,
            questionnaire_config=questionnaire_config or {},
        )

    values = {trait: _uniform(rng, trait_ranges[trait]) for trait in TRAITS}
    if chosen is None:
        chosen = _nearest_archetype(values, archetypes)

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
