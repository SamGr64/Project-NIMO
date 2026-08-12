from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np

from nimo.generation.latent_profile import LatentProfile
from nimo.generation.seeds import child_seed


@dataclass(frozen=True, slots=True)
class SyntheticAccount:
    key: str
    name: str
    bank_name: str
    account_number: str
    sort_code: str
    account_type: str
    currency: str
    opening_balance: float

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _digits(rng: np.random.Generator, count: int) -> str:
    return "".join(str(int(value)) for value in rng.integers(0, 10, size=count))


def build_accounts(profile: LatentProfile, currency: str = "GBP") -> list[SyntheticAccount]:
    rng = np.random.default_rng(child_seed(profile.seed, "accounts"))
    banks = ["NIMOB", "EarlGrey Bank", "Brie Building Society", "Fetawide"]
    current_bank = str(rng.choice(banks))
    accounts = [
        SyntheticAccount(
            key="current",
            name="Main Current Account",
            bank_name=current_bank,
            account_number=_digits(rng, 8),
            sort_code="-".join(_digits(rng, 6)[index : index + 2] for index in range(0, 6, 2)),
            account_type="current",
            currency=currency,
            opening_balance=round(profile.monthly_income * float(rng.uniform(0.45, 1.35)), 2),
        )
    ]

    if profile.savings_propensity > 0.07 or rng.random() < 0.72:
        savings_bank = str(rng.choice(banks))
        accounts.append(
            SyntheticAccount(
                key="savings",
                name="Easy Access Savings",
                bank_name=savings_bank,
                account_number=_digits(rng, 8),
                sort_code="-".join(
                    _digits(rng, 6)[index : index + 2] for index in range(0, 6, 2)
                ),
                account_type="savings",
                currency=currency,
                opening_balance=round(
                    profile.monthly_income
                    * profile.savings_propensity
                    * float(rng.uniform(2.0, 9.0)),
                    2,
                ),
            )
        )
    return accounts
