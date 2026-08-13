from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from sqlalchemy import select

from nimo.application.services.forecast_service import ForecastService
from nimo.forecasting import simulate_forecast
from nimo.investing import LocalMarketDataProvider, asset_statistics, correlation_matrix, simulate_portfolio, summarise_investment
from nimo.storage.database import Database
from nimo.storage.models import InvestmentRunRecord, PortfolioRecord
from nimo.users.workspace import UserWorkspace


class InvestmentService:
    def __init__(
        self,
        *,
        database: Database,
        workspace: UserWorkspace,
        config: dict[str, Any],
        forecasting: ForecastService,
    ) -> None:
        self.database = database
        self.workspace = workspace
        self.config = config
        self.forecasting = forecasting
        self.provider = LocalMarketDataProvider()

    def assets(self) -> list[dict[str, Any]]:
        return self.provider.list_assets().to_dict(orient="records")

    def statistics(self, symbols: list[str] | None = None) -> list[dict[str, Any]]:
        return asset_statistics(self.provider.history(symbols))

    def correlations(self, symbols: list[str] | None = None) -> dict[str, Any]:
        matrix = correlation_matrix(self.provider.history(symbols), symbols)
        return {"symbols": list(matrix.columns), "matrix": matrix.to_dict()}

    def ensure_default_portfolio(self) -> dict[str, Any]:
        with self.database.session() as session:
            record = session.scalar(select(PortfolioRecord).where(PortfolioRecord.is_default.is_(True)).order_by(PortfolioRecord.id.desc()))
            if record is None:
                defaults = self.config.get("defaults", {})
                record = PortfolioRecord(
                    name="Balanced Learning Portfolio",
                    description="Educational default: global equities, bonds and cash. Not a recommendation.",
                    allocations_json=json.dumps({"GLOBAL_EQ": 0.60, "BOND": 0.30, "CASH": 0.10}, sort_keys=True),
                    contribution_rule_json=json.dumps(
                        {
                            "type": str(defaults.get("contribution_rule", "fixed")),
                            "amount": float(defaults.get("monthly_contribution", 100.0)),
                            "initial_amount": 0.0,
                        },
                        sort_keys=True,
                    ),
                    assumptions_json=json.dumps(
                        {
                            "annual_fee_rate": float(defaults.get("annual_fee_rate", 0.0025)),
                            "provider": "local_educational",
                        },
                        sort_keys=True,
                    ),
                    is_default=True,
                )
                session.add(record)
                session.flush()
            return self._portfolio_payload(record)

    def portfolios(self) -> list[dict[str, Any]]:
        self.ensure_default_portfolio()
        with self.database.session() as session:
            return [self._portfolio_payload(record) for record in session.scalars(select(PortfolioRecord).order_by(PortfolioRecord.is_default.desc(), PortfolioRecord.name))]

    def create_portfolio(
        self,
        name: str,
        *,
        allocations: dict[str, float],
        contribution_rule: dict[str, Any] | None = None,
        description: str = "",
    ) -> dict[str, Any]:
        self._validate_allocations(allocations)
        with self.database.session() as session:
            if session.scalar(select(PortfolioRecord).where(PortfolioRecord.name == name)) is not None:
                raise ValueError(f"Portfolio already exists: {name}")
            record = PortfolioRecord(
                name=name,
                description=description,
                allocations_json=json.dumps(allocations, sort_keys=True),
                contribution_rule_json=json.dumps(contribution_rule or {"type": "fixed", "amount": 100.0}, sort_keys=True),
                assumptions_json=json.dumps({"annual_fee_rate": float(self.config.get("defaults", {}).get("annual_fee_rate", 0.0025)), "provider": "local_educational"}, sort_keys=True),
                is_default=False,
            )
            session.add(record)
            session.flush()
            return self._portfolio_payload(record)

    def update_portfolio(
        self,
        portfolio: str | int,
        *,
        allocations: dict[str, float] | None = None,
        contribution_rule: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with self.database.session() as session:
            record = self._portfolio_record(session, portfolio)
            if allocations is not None:
                self._validate_allocations(allocations)
                record.allocations_json = json.dumps(allocations, sort_keys=True)
            if contribution_rule is not None:
                record.contribution_rule_json = json.dumps(contribution_rule, sort_keys=True)
            return self._portfolio_payload(record)

    def simulate(
        self,
        portfolio: str | int = "Balanced Learning Portfolio",
        *,
        scenario: str = "Baseline",
        horizon_years: int | None = None,
        runs: int | None = None,
        seed: int = 44021,
        stress_name: str | None = None,
        store: bool = True,
    ) -> dict[str, Any]:
        self.ensure_default_portfolio()
        defaults = self.config.get("defaults", {})
        simulation_cfg = self.config.get("simulation", {})
        years = int(horizon_years or defaults.get("horizon_years", 10))
        run_count = int(runs or defaults.get("simulation_runs", 3000))
        if years > int(simulation_cfg.get("maximum_horizon_years", 50)):
            raise ValueError("Investment horizon exceeds configured maximum")
        if run_count > int(simulation_cfg.get("maximum_runs", 50000)):
            raise ValueError("Simulation count exceeds configured maximum")
        with self.database.session() as session:
            portfolio_record = self._portfolio_record(session, portfolio)
            portfolio_payload = self._portfolio_payload(portfolio_record)
        resolved = self.forecasting.resolved_scenario(scenario)
        profile = json.loads(json.dumps(resolved["profile"]))
        stress = self._stress(stress_name)
        if stress and "income_multiplier" in stress:
            profile["income"]["monthly_mean"] = float(profile["income"]["monthly_mean"]) * float(stress["income_multiplier"])
            profile["income"]["monthly_std"] = float(profile["income"]["monthly_std"]) * float(stress["income_multiplier"])
        horizon_months = years * 12
        cashflow = simulate_forecast(
            profile,
            events=resolved["events"],
            horizon_months=horizon_months,
            runs=run_count,
            seed=seed,
        )
        assumptions = portfolio_payload["assumptions"]
        investment = simulate_portfolio(
            history=self.provider.history(list(portfolio_payload["allocations"])),
            allocations=portfolio_payload["allocations"],
            cashflow=cashflow,
            contribution_rule=portfolio_payload["contribution_rule"],
            annual_fee_rate=float(assumptions.get("annual_fee_rate", defaults.get("annual_fee_rate", 0.0025))),
            seed=seed + 1,
            stress=stress,
        )
        summary = summarise_investment(investment)
        summary.update(
            {
                "portfolio": portfolio_payload,
                "scenario": scenario,
                "horizon_years": years,
                "simulation_runs": run_count,
                "seed": seed,
                "stress_name": stress_name,
                "provider": self.provider.name,
                "educational_notice": "All bundled market history is synthetic and for learning only. Results are simulations, not predictions or recommendations.",
            }
        )
        if not store:
            return {"summary": summary, "simulation": investment, "cashflow": cashflow}
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        path = self.workspace.cache_dir / f"investment_{portfolio_record.id}_{timestamp}.npz"
        self.workspace.cache_dir.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            path,
            months=np.asarray(investment.months),
            portfolio_values=investment.portfolio_values,
            contributions=investment.contributions,
            adjusted_cash_balances=investment.adjusted_cash_balances,
        )
        with self.database.session() as session:
            record = InvestmentRunRecord(
                portfolio_id=portfolio_record.id,
                forecast_run_id=None,
                seed=seed,
                horizon_months=horizon_months,
                simulation_runs=run_count,
                stress_name=stress_name,
                summary_json=json.dumps(summary, sort_keys=True),
                paths_file=self.workspace.path_for_storage(path),
            )
            session.add(record)
            session.flush()
            summary["run_id"] = record.id
            summary["paths_file"] = self.workspace.path_for_storage(path)
            record.summary_json = json.dumps(summary, sort_keys=True)
        return summary

    def latest_run(self) -> dict[str, Any] | None:
        with self.database.session() as session:
            record = session.scalar(select(InvestmentRunRecord).order_by(InvestmentRunRecord.id.desc()))
            return None if record is None else json.loads(record.summary_json)

    def _stress(self, name: str | None) -> dict[str, Any] | None:
        if name is None:
            return None
        preset = self.config.get("stress_presets", {}).get(name)
        if preset is None:
            raise KeyError(f"Unknown stress preset: {name}")
        return {key: value for key, value in preset.items() if key != "label"}

    def _validate_allocations(self, allocations: dict[str, float]) -> None:
        available = set(self.provider.list_assets()["symbol"])
        unknown = set(allocations) - available
        if unknown:
            raise KeyError(f"Unknown educational assets: {sorted(unknown)}")
        if sum(max(0.0, float(value)) for value in allocations.values()) <= 0:
            raise ValueError("Portfolio allocations must contain a positive weight")

    @staticmethod
    def _portfolio_record(session, portfolio: str | int) -> PortfolioRecord:
        if isinstance(portfolio, int) or str(portfolio).isdigit():
            record = session.get(PortfolioRecord, int(portfolio))
        else:
            record = session.scalar(select(PortfolioRecord).where(PortfolioRecord.name == str(portfolio)))
        if record is None:
            raise KeyError(f"Portfolio not found: {portfolio}")
        return record

    @staticmethod
    def _portfolio_payload(record: PortfolioRecord) -> dict[str, Any]:
        return {
            "id": record.id,
            "name": record.name,
            "description": record.description,
            "allocations": json.loads(record.allocations_json),
            "contribution_rule": json.loads(record.contribution_rule_json),
            "assumptions": json.loads(record.assumptions_json),
            "is_default": record.is_default,
        }
