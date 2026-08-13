import pytest

from nimo.config.loader import ConfigManager
from nimo.generation.latent_profile import sample_latent_profile


def test_latent_profile_is_seeded_and_bounded(project_root, data_root) -> None:
    config = ConfigManager.discover(project_root=project_root, data_root=data_root)
    kwargs = {
        "seed": 123,
        "generator_config": config.mapping("generator"),
        "archetypes_config": config.mapping("archetypes"),
        "questionnaire_config": config.mapping("questionnaire"),
    }
    first = sample_latent_profile(**kwargs)
    second = sample_latent_profile(**kwargs)
    assert first == second
    assert 0 <= first.savings_propensity <= 1
    assert first.monthly_income > 0


def test_financial_twin_answers_constrain_population_without_fixed_archetype(project_root, data_root) -> None:
    config = ConfigManager.discover(project_root=project_root, data_root=data_root)
    answers = {
        "income_pattern": "predictable",
        "saving_style": "save_first",
        "social_spend": "low",
        "unexpected_costs": "rarely",
    }
    kwargs = {
        "seed": 90210,
        "generator_config": config.mapping("generator"),
        "archetypes_config": config.mapping("archetypes"),
        "questionnaire_config": config.mapping("questionnaire"),
        "questionnaire": answers,
    }
    first = sample_latent_profile(**kwargs)
    second = sample_latent_profile(**kwargs)
    assert first == second
    assert 0.75 <= first.income_stability <= 1.0
    assert 0.42 <= first.savings_propensity <= 0.78
    assert 0.08 <= first.discretionary_intensity <= 0.35
    assert 0.15 <= first.weekend_bias <= 0.50
    assert 0.0 <= first.shock_exposure <= 0.18
    assert first.archetype in config.mapping("archetypes")["archetypes"]


def test_questionnaire_rejects_unknown_answer(project_root, data_root) -> None:
    config = ConfigManager.discover(project_root=project_root, data_root=data_root)
    with pytest.raises(ValueError, match="Unknown answer"):
        sample_latent_profile(
            seed=1,
            generator_config=config.mapping("generator"),
            archetypes_config=config.mapping("archetypes"),
            questionnaire_config=config.mapping("questionnaire"),
            questionnaire={"saving_style": "definitely_not_real"},
        )
