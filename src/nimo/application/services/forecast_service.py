from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from sqlalchemy import select, update

from nimo.analysis.overview import compute_overview_metrics
from nimo.application.services.behaviour_service import BehaviourService
from nimo.forecasting import (
    build_default_forecast_profile,
    resolve_profile,
    rolling_backtest,
    simulate_forecast,
    summarise_forecast,
    validate_override,
)
from nimo.storage.database import Database
from nimo.storage.models import Account, ForecastProfileRecord, ForecastRunRecord, ForecastScenarioRecord
from nimo.storage.repositories import TransactionRepository
from nimo.storage.versioning import source_data_version
from nimo.users.workspace import UserWorkspace


class ForecastService:
    def __init__(
        self,
        *,
        database: Database,
        workspace: UserWorkspace,
        config: dict[str, Any],
        behaviours: BehaviourService,
    ) -> None:
        self.database = database
        self.workspace = workspace
        self.config = config
        self.behaviours = behaviours
        self.transactions = TransactionRepository()

    def ensure_default_profile(self, *, force: bool = False) -> dict[str, Any]:
        behaviour_map = self.behaviours.current()
        behaviour_map_id = self.behaviours.current_record_id()
        with self.database.session() as session:
            data_version = source_data_version(session)
            existing = session.scalar(
                select(ForecastProfileRecord)
                .where(
                    ForecastProfileRecord.is_current.is_(True),
                    ForecastProfileRecord.source_data_version == data_version,
                )
                .order_by(ForecastProfileRecord.id.desc())
            )
            if existing is not None and not force:
                self._ensure_baseline(session, existing)
                return self._profile_payload(existing)
            frame = self.transactions.active_frame(session)
            opening = {
                account.id: float(account.opening_balance)
                for account in session.scalars(select(Account).where(Account.is_active.is_(True)))
            }
            overview = compute_overview_metrics(frame, account_opening=opening)
            profile = build_default_forecast_profile(
                frame,
                behaviour_map,
                opening_balance=float(overview.total_balance),
                config=self.config,
            )
            session.execute(update(ForecastProfileRecord).values(is_current=False))
            record = ForecastProfileRecord(
                name="Default",
                source_behaviour_map_id=behaviour_map_id,
                source_data_version=data_version,
                profile_json=json.dumps(profile, sort_keys=True),
                is_current=True,
            )
            session.add(record)
            session.flush()
            self._ensure_baseline(session, record, reset=True)
            return self._profile_payload(record)

    def profile(self) -> dict[str, Any]:
        return self.ensure_default_profile()

    def scenarios(self) -> list[dict[str, Any]]:
        self.ensure_default_profile()
        with self.database.session() as session:
            records = list(session.scalars(select(ForecastScenarioRecord).order_by(ForecastScenarioRecord.is_baseline.desc(), ForecastScenarioRecord.name)))
            return [self._scenario_payload(record) for record in records]

    def create_scenario(self, name: str, *, description: str = "", copy_from: str = "Baseline") -> dict[str, Any]:
        name = name.strip()
        if not name:
            raise ValueError("Scenario name cannot be empty")
        profile = self.ensure_default_profile()
        with self.database.session() as session:
            if session.scalar(select(ForecastScenarioRecord).where(ForecastScenarioRecord.name == name)) is not None:
                raise ValueError(f"Forecast scenario already exists: {name}")
            source = session.scalar(select(ForecastScenarioRecord).where(ForecastScenarioRecord.name == copy_from))
            record = ForecastScenarioRecord(
                name=name,
                description=description,
                profile_id=int(profile["id"]),
                overrides_json=source.overrides_json if source else "{}",
                events_json=source.events_json if source else "[]",
                is_baseline=False,
            )
            session.add(record)
            session.flush()
            return self._scenario_payload(record)

    def set_override(self, scenario: str, path: str, value: Any) -> dict[str, Any]:
        profile = self.ensure_default_profile()
        with self.database.session() as session:
            record = self._scenario_record(session, scenario)
            profile_record = session.get(ForecastProfileRecord, record.profile_id)
            if profile_record is None:
                raise KeyError(f"Forecast profile not found for scenario {scenario}")
            base = json.loads(profile_record.profile_json)
            validate_override(base, path, value)
            overrides = json.loads(record.overrides_json)
            overrides[path] = value
            record.overrides_json = json.dumps(overrides, sort_keys=True)
            return self._scenario_payload(record)

    def remove_override(self, scenario: str, path: str) -> dict[str, Any]:
        with self.database.session() as session:
            record = self._scenario_record(session, scenario)
            overrides = json.loads(record.overrides_json)
            overrides.pop(path, None)
            record.overrides_json = json.dumps(overrides, sort_keys=True)
            return self._scenario_payload(record)

    def add_event(
        self,
        scenario: str,
        *,
        name: str,
        event_date: date,
        amount: float,
        uncertainty: float = 0.0,
        probability: float = 1.0,
        repeat_months: int = 0,
    ) -> dict[str, Any]:
        if not 0 <= probability <= 1:
            raise ValueError("Event probability must be between 0 and 1")
        with self.database.session() as session:
            record = self._scenario_record(session, scenario)
            events = json.loads(record.events_json)
            events.append(
                {
                    "name": name,
                    "date": event_date.isoformat(),
                    "amount": float(amount),
                    "uncertainty": max(0.0, float(uncertainty)),
                    "probability": float(probability),
                    "repeat_months": max(0, int(repeat_months)),
                    "source": "user",
                }
            )
            record.events_json = json.dumps(events, sort_keys=True)
            return self._scenario_payload(record)

    def clear_events(self, scenario: str) -> dict[str, Any]:
        with self.database.session() as session:
            record = self._scenario_record(session, scenario)
            record.events_json = "[]"
            return self._scenario_payload(record)

    def resolved_scenario(self, scenario: str = "Baseline") -> dict[str, Any]:
        self.ensure_default_profile()
        with self.database.session() as session:
            scenario_record = self._scenario_record(session, scenario)
            profile_record = session.get(ForecastProfileRecord, scenario_record.profile_id)
            if profile_record is None:
                raise KeyError(f"Forecast profile not found for scenario {scenario}")
            base = json.loads(profile_record.profile_json)
            overrides = json.loads(scenario_record.overrides_json)
            return {
                "scenario": self._scenario_payload(scenario_record),
                "profile": resolve_profile(base, overrides),
                "base_profile": base,
                "events": json.loads(scenario_record.events_json),
                "source_data_version": profile_record.source_data_version,
            }

    def run(
        self,
        *,
        scenario: str = "Baseline",
        horizon_months: int | None = None,
        runs: int | None = None,
        seed: int = 202601,
        threshold: float | None = None,
        store: bool = True,
    ) -> dict[str, Any]:
        self.ensure_default_profile()
        monte = self.config.get("monte_carlo", {})
        horizon = int(horizon_months or monte.get("default_horizon_months", 12))
        run_count = int(runs or monte.get("default_runs", 3000))
        if horizon > int(monte.get("maximum_horizon_months", 120)):
            raise ValueError("Forecast horizon exceeds configured maximum")
        if run_count > int(monte.get("maximum_runs", 50000)):
            raise ValueError("Simulation count exceeds configured maximum")
        with self.database.session() as session:
            scenario_record = self._scenario_record(session, scenario)
            profile_record = session.get(ForecastProfileRecord, scenario_record.profile_id)
            if profile_record is None:
                raise KeyError(f"Forecast profile not found for scenario {scenario}")
            base = json.loads(profile_record.profile_json)
            overrides = json.loads(scenario_record.overrides_json)
            events = json.loads(scenario_record.events_json)
            resolved = resolve_profile(base, overrides)
            simulation = simulate_forecast(
                resolved,
                events=events,
                horizon_months=horizon,
                runs=run_count,
                seed=seed,
            )
            summary = summarise_forecast(simulation, threshold=threshold)
            summary.update(
                {
                    "scenario": scenario_record.name,
                    "scenario_id": scenario_record.id,
                    "seed": seed,
                    "as_of_date": resolved.get("as_of_date"),
                    "overrides": overrides,
                    "events": events,
                }
            )
            if not store:
                return {"summary": summary, "simulation": simulation}
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            path = self.workspace.cache_dir / f"forecast_{scenario_record.id}_{timestamp}.npz"
            self.workspace.cache_dir.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(
                path,
                months=np.asarray(simulation.months),
                balances=simulation.balances,
                income=simulation.income,
                spending=simulation.spending,
                net_cashflow=simulation.net_cashflow,
            )
            record = ForecastRunRecord(
                scenario_id=scenario_record.id,
                seed=seed,
                horizon_months=horizon,
                simulation_runs=run_count,
                as_of_date=date.fromisoformat(str(resolved.get("as_of_date"))),
                source_data_version=profile_record.source_data_version,
                assumptions_json=json.dumps(resolved, sort_keys=True),
                summary_json=json.dumps(summary, sort_keys=True),
                paths_file=self.workspace.path_for_storage(path),
            )
            session.add(record)
            session.flush()
            summary["run_id"] = record.id
            summary["paths_file"] = self.workspace.path_for_storage(path)
            record.summary_json = json.dumps(summary, sort_keys=True)
            return summary

    def latest_run(self, *, scenario: str | None = None) -> dict[str, Any] | None:
        with self.database.session() as session:
            statement = select(ForecastRunRecord).order_by(ForecastRunRecord.id.desc())
            if scenario is not None:
                scenario_record = self._scenario_record(session, scenario)
                statement = statement.where(ForecastRunRecord.scenario_id == scenario_record.id)
            record = session.scalar(statement)
            return None if record is None else json.loads(record.summary_json)

    def load_paths(self, run_id: int) -> dict[str, Any]:
        with self.database.session() as session:
            record = session.get(ForecastRunRecord, run_id)
            if record is None or not record.paths_file:
                raise KeyError(f"Forecast run not found: {run_id}")
            path = self.workspace.resolve_stored_path(record.paths_file)
        if not path.exists():
            raise FileNotFoundError(f"Forecast path cache is missing: {path}")
        with np.load(path, allow_pickle=False) as data:
            return {key: data[key] for key in data.files}

    def compare(self, scenarios: list[str], *, horizon_months: int | None = None, runs: int | None = None, seed: int = 202601) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for index, name in enumerate(scenarios):
            result = self.run(scenario=name, horizon_months=horizon_months, runs=runs, seed=seed + index, store=False)
            summary = result["summary"]
            final = summary["final_balance"]
            rows.append(
                {
                    "scenario": name,
                    "median_final_balance": final["median"],
                    "p10": final["p10"],
                    "p90": final["p90"],
                    "expected_net_cashflow": summary["expected_net_cashflow"],
                    "probability_negative_balance": summary["probability_negative_balance"],
                }
            )
        return rows

    def backtest(self, *, holdout_months: int | None = None, runs: int | None = None) -> dict[str, Any]:
        with self.database.session() as session:
            frame = self.transactions.active_frame(session)
            opening = float(sum(account.opening_balance for account in session.scalars(select(Account).where(Account.is_active.is_(True)))))
        backtest_cfg = self.config.get("backtesting", {})
        return rolling_backtest(
            frame,
            opening_balance=opening,
            config=self.config,
            holdout_months=int(holdout_months or backtest_cfg.get("default_holdout_months", 3)),
            runs=int(runs or backtest_cfg.get("runs", 1000)),
        )

    def _ensure_baseline(self, session, profile: ForecastProfileRecord, *, reset: bool = False) -> ForecastScenarioRecord:
        baseline = session.scalar(select(ForecastScenarioRecord).where(ForecastScenarioRecord.name == "Baseline"))
        if baseline is None:
            baseline = ForecastScenarioRecord(
                name="Baseline",
                description="Inferred behaviour continues with default assumptions.",
                profile_id=profile.id,
                overrides_json="{}",
                events_json="[]",
                is_baseline=True,
            )
            session.add(baseline)
            session.flush()
        elif baseline.profile_id != profile.id:
            baseline.profile_id = profile.id
            if reset:
                baseline.overrides_json = "{}"
                baseline.events_json = "[]"
        return baseline

    @staticmethod
    def _profile_payload(record: ForecastProfileRecord) -> dict[str, Any]:
        return {
            "id": record.id,
            "name": record.name,
            "source_data_version": record.source_data_version,
            "source_behaviour_map_id": record.source_behaviour_map_id,
            "profile": json.loads(record.profile_json),
            "is_current": record.is_current,
        }

    @staticmethod
    def _scenario_payload(record: ForecastScenarioRecord) -> dict[str, Any]:
        return {
            "id": record.id,
            "name": record.name,
            "description": record.description,
            "profile_id": record.profile_id,
            "overrides": json.loads(record.overrides_json),
            "events": json.loads(record.events_json),
            "is_baseline": record.is_baseline,
        }

    @staticmethod
    def _scenario_record(session, scenario: str | int) -> ForecastScenarioRecord:
        if isinstance(scenario, int) or str(scenario).isdigit():
            record = session.get(ForecastScenarioRecord, int(scenario))
        else:
            record = session.scalar(select(ForecastScenarioRecord).where(ForecastScenarioRecord.name == str(scenario)))
        if record is None:
            raise KeyError(f"Forecast scenario not found: {scenario}")
        return record
