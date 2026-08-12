from nimo.generation.seeds import child_seed


def test_child_seeds_are_stable_and_namespaced() -> None:
    assert child_seed(42, "income") == child_seed(42, "income")
    assert child_seed(42, "income") != child_seed(42, "dining")
    assert child_seed(42, "income") != child_seed(43, "income")
