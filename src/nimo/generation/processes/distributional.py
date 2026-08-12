from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class DistributionModel:
    family: str
    parameters: tuple[float, ...]

    def sample(self, rng: np.random.Generator, size: int = 1) -> np.ndarray:
        if self.family == "normal":
            return rng.normal(self.parameters[0], self.parameters[1], size=size)
        if self.family == "lognormal":
            return rng.lognormal(self.parameters[0], self.parameters[1], size=size)
        if self.family == "gamma":
            return rng.gamma(self.parameters[0], self.parameters[1], size=size)
        if self.family == "bimodal_normal":
            mean_a, std_a, mean_b, std_b, probability_a = self.parameters
            choose_a = rng.random(size) < probability_a
            return np.where(
                choose_a,
                rng.normal(mean_a, std_a, size=size),
                rng.normal(mean_b, std_b, size=size),
            )
        raise ValueError(f"Unsupported distribution family: {self.family}")
