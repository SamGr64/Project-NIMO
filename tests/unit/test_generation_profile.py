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
