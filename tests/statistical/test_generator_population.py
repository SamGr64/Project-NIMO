from nimo.config.loader import ConfigManager
from nimo.generation.latent_profile import sample_latent_profile


def test_unconstrained_seeds_span_multiple_archetypes(project_root, data_root) -> None:
    config = ConfigManager.discover(project_root=project_root, data_root=data_root)
    profiles = [
        sample_latent_profile(
            seed=seed,
            generator_config=config.mapping("generator"),
            archetypes_config=config.mapping("archetypes"),
            questionnaire_config=config.mapping("questionnaire"),
        )
        for seed in range(20)
    ]
    assert len({profile.archetype for profile in profiles}) >= 3
    assert len({round(profile.savings_propensity, 2) for profile in profiles}) > 10
