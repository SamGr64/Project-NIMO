from __future__ import annotations

import json
from datetime import date
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy import delete, select

from nimo.application.services.forecast_service import ForecastService
from nimo.forecasting import simulate_forecast
from nimo.planning import infer_budget_lines, months_until, simulate_goal
from nimo.storage.database import Database
from nimo.storage.models import BudgetLineRecord, BudgetRecord, GoalRecord
from nimo.storage.repositories import TransactionRepository
from nimo.storage.versioning import source_data_version


class PlanningService:
    def __init__(
        self,
        *,
        database: Database,
        config: dict[str, Any],
        forecasting: ForecastService,
    ) -> None:
        self.database = database
        self.config = config
        self.forecasting = forecasting
        self.transactions = TransactionRepository()

    def ensure_default_budget(self, *, force: bool = False) -> dict[str, Any]:
        with self.database.session() as session:
            data_version = source_data_version(session)
            budget = session.scalar(select(BudgetRecord).where(BudgetRecord.is_default.is_(True)).order_by(BudgetRecord.id.desc()))
            settings = json.loads(budget.settings_json) if budget else {}
            if budget is not None and settings.get("source_data_version") == data_version and not force:
                return self._budget_payload(session, budget)
            frame = self.transactions.active_frame(session)
            lines = infer_budget_lines(frame, config=self.config)
            if budget is None:
                budget = BudgetRecord(
                    name="NIMO Baseline",
                    mode="category",
                    period="monthly",
                    is_default=True,
                    settings_json="{}",
                )
                session.add(budget)
                session.flush()
            else:
                session.execute(delete(BudgetLineRecord).where(BudgetLineRecord.budget_id == budget.id))
            budget.settings_json = json.dumps(
                {
                    "source_data_version": data_version,
                    "description": "Default budget inferred from recent category spending.",
                },
                sort_keys=True,
            )
            for line in lines:
                session.add(
                    BudgetLineRecord(
                        budget_id=budget.id,
                        category_slug=line["category_slug"],
                        label=line["label"],
                        amount=float(line["amount"]),
                        source=line["source"],
                        is_essential=bool(line["is_essential"]),
                        settings_json=json.dumps(line["settings"], sort_keys=True),
                    )
                )
            session.flush()
            return self._budget_payload(session, budget)

    def budgets(self) -> list[dict[str, Any]]:
        self.ensure_default_budget()
        with self.database.session() as session:
            return [self._budget_payload(session, budget) for budget in session.scalars(select(BudgetRecord).order_by(BudgetRecord.is_default.desc(), BudgetRecord.name))]

    def create_budget(self, name: str, *, mode: str = "category", copy_default: bool = True) -> dict[str, Any]:
        allowed = set(self.config.get("modes", ["category"]))
        if mode not in allowed:
            raise ValueError(f"Unknown budget mode: {mode}")
        default = self.ensure_default_budget()
        with self.database.session() as session:
            if session.scalar(select(BudgetRecord).where(BudgetRecord.name == name)) is not None:
                raise ValueError(f"Budget already exists: {name}")
            budget = BudgetRecord(name=name, mode=mode, period="monthly", is_default=False, settings_json="{}")
            session.add(budget)
            session.flush()
            if copy_default:
                for line in default["lines"]:
                    session.add(
                        BudgetLineRecord(
                            budget_id=budget.id,
                            category_slug=line["category_slug"],
                            label=line["label"],
                            amount=float(line["amount"]),
                            source="copied",
                            is_essential=bool(line["is_essential"]),
                            settings_json=json.dumps(line.get("settings", {}), sort_keys=True),
                        )
                    )
            session.flush()
            return self._budget_payload(session, budget)

    def set_line(self, budget: str | int, category_slug: str, amount: float, *, label: str | None = None, essential: bool | None = None) -> dict[str, Any]:
        if amount < 0:
            raise ValueError("Budget amount cannot be negative")
        with self.database.session() as session:
            record = self._budget_record(session, budget)
            line = session.scalar(
                select(BudgetLineRecord).where(
                    BudgetLineRecord.budget_id == record.id,
                    BudgetLineRecord.category_slug == category_slug,
                )
            )
            if line is None:
                line = BudgetLineRecord(
                    budget_id=record.id,
                    category_slug=category_slug,
                    label=label or category_slug.replace("_", " ").title(),
                    amount=float(amount),
                    source="user",
                    is_essential=bool(essential),
                    settings_json="{}",
                )
                session.add(line)
            else:
                line.amount = float(amount)
                line.source = "user"
                if label:
                    line.label = label
                if essential is not None:
                    line.is_essential = essential
            session.flush()
            return self._budget_payload(session, record)

    def evaluate(self, budget: str | int = "NIMO Baseline", *, scenario: str = "Baseline", runs: int | None = None) -> dict[str, Any]:
        self.ensure_default_budget()
        with self.database.session() as session:
            record = self._budget_record(session, budget)
            payload = self._budget_payload(session, record)
            frame = self.transactions.active_frame(session)
        simulation_result = self.forecasting.run(scenario=scenario, horizon_months=1, runs=runs, store=False)
        simulation = simulation_result["simulation"]
        latest_period = pd.Timestamp(frame["booking_date"].max()).to_period("M") if not frame.empty else None
        current = frame.loc[(frame["amount"] < 0) & frame["transfer_group_id"].isna()].copy()
        if latest_period is not None:
            current = current.loc[pd.to_datetime(current["booking_date"]).dt.to_period("M") == latest_period]
        rows: list[dict[str, Any]] = []
        for line in payload["lines"]:
            category = line["category_slug"]
            actual = 0.0 if current.empty else float(-current.loc[current["category_slug"].fillna("uncategorised") == category, "amount"].sum())
            samples = simulation.category_spending.get(category)
            probability = None if samples is None else float(np.mean(samples[:, 0] <= float(line["amount"])))
            projected = None if samples is None else float(np.median(samples[:, 0]))
            rows.append(
                {
                    **line,
                    "current_period_actual": round(actual, 6),
                    "forecast_median": None if projected is None else round(projected, 6),
                    "probability_within_budget": None if probability is None else round(probability, 6),
                }
            )
        return {
            "budget": {key: value for key, value in payload.items() if key != "lines"},
            "lines": rows,
            "total_budget": round(sum(float(line["amount"]) for line in payload["lines"]), 6),
            "forecast_total_spend_median": simulation_result["summary"]["months"][0]["spend_median"],
            "scenario": scenario,
        }

    def add_goal(
        self,
        *,
        name: str,
        target_amount: float,
        target_date: date,
        current_amount: float = 0.0,
        priority: int = 3,
        monthly_contribution: float = 0.0,
        surplus_allocation_fraction: float = 0.0,
    ) -> dict[str, Any]:
        if target_amount <= 0:
            raise ValueError("Goal target must be positive")
        if target_date <= date.today():
            raise ValueError("Goal target date must be in the future")
        with self.database.session() as session:
            record = GoalRecord(
                name=name,
                target_amount=float(target_amount),
                current_amount=max(0.0, float(current_amount)),
                target_date=target_date,
                priority=max(1, min(5, int(priority))),
                monthly_contribution=max(0.0, float(monthly_contribution)),
                surplus_allocation_fraction=max(0.0, min(1.0, float(surplus_allocation_fraction))),
            )
            session.add(record)
            session.flush()
            return self._goal_payload(record)

    def goals(self, *, active_only: bool = True) -> list[dict[str, Any]]:
        with self.database.session() as session:
            statement = select(GoalRecord).order_by(GoalRecord.priority, GoalRecord.target_date)
            if active_only:
                statement = statement.where(GoalRecord.is_active.is_(True))
            return [self._goal_payload(record) for record in session.scalars(statement)]

    def simulate_goal(self, goal: str | int, *, scenario: str = "Baseline", runs: int | None = None, seed: int = 8321) -> dict[str, Any]:
        with self.database.session() as session:
            record = self._goal_record(session, goal)
            goal_payload = self._goal_payload(record)
        resolved = self.forecasting.resolved_scenario(scenario)
        horizon = months_until(resolved["profile"]["as_of_date"], str(record.target_date))
        run_count = int(runs or self.config.get("defaults", {}).get("goal_simulation_runs", 3000))
        simulation = simulate_forecast(
            resolved["profile"],
            events=resolved["events"],
            horizon_months=horizon,
            runs=run_count,
            seed=seed,
        )
        result = simulate_goal(
            simulation,
            current_amount=record.current_amount,
            target_amount=record.target_amount,
            monthly_contribution=record.monthly_contribution,
            surplus_allocation_fraction=record.surplus_allocation_fraction,
        )
        return {"goal": goal_payload, "scenario": scenario, "horizon_months": horizon, **result}

    def intervention(
        self,
        goal: str | int,
        *,
        category_slug: str,
        reduction_fraction: float,
        scenario: str = "Baseline",
        runs: int | None = None,
        seed: int = 8321,
    ) -> dict[str, Any]:
        if not 0 <= reduction_fraction <= 1:
            raise ValueError("Reduction fraction must be between 0 and 1")
        with self.database.session() as session:
            goal_record = self._goal_record(session, goal)
        resolved = self.forecasting.resolved_scenario(scenario)
        horizon = months_until(resolved["profile"]["as_of_date"], str(goal_record.target_date))
        run_count = int(runs or self.config.get("defaults", {}).get("goal_simulation_runs", 3000))
        base_sim = simulate_forecast(resolved["profile"], events=resolved["events"], horizon_months=horizon, runs=run_count, seed=seed)
        altered_profile = json.loads(json.dumps(resolved["profile"]))
        process = altered_profile.get("categories", {}).get(category_slug)
        if process is None:
            raise KeyError(f"Category is not present in forecast profile: {category_slug}")
        process["monthly_mean"] = float(process["monthly_mean"]) * (1.0 - reduction_fraction)
        process["monthly_std"] = float(process["monthly_std"]) * (1.0 - reduction_fraction)
        changed_sim = simulate_forecast(altered_profile, events=resolved["events"], horizon_months=horizon, runs=run_count, seed=seed)
        kwargs = {
            "current_amount": goal_record.current_amount,
            "target_amount": goal_record.target_amount,
            "monthly_contribution": goal_record.monthly_contribution,
            "surplus_allocation_fraction": goal_record.surplus_allocation_fraction,
        }
        base = simulate_goal(base_sim, **kwargs)
        changed = simulate_goal(changed_sim, **kwargs)
        return {
            "goal": self._goal_payload(goal_record),
            "category": category_slug,
            "reduction_fraction": reduction_fraction,
            "baseline_probability": base["probability_achieved"],
            "intervention_probability": changed["probability_achieved"],
            "probability_change": round(changed["probability_achieved"] - base["probability_achieved"], 6),
            "baseline_expected_final": base["expected_final_amount"],
            "intervention_expected_final": changed["expected_final_amount"],
        }

    @staticmethod
    def _budget_record(session, budget: str | int) -> BudgetRecord:
        if isinstance(budget, int) or str(budget).isdigit():
            record = session.get(BudgetRecord, int(budget))
        else:
            record = session.scalar(select(BudgetRecord).where(BudgetRecord.name == str(budget)))
        if record is None:
            raise KeyError(f"Budget not found: {budget}")
        return record

    @staticmethod
    def _goal_record(session, goal: str | int) -> GoalRecord:
        if isinstance(goal, int) or str(goal).isdigit():
            record = session.get(GoalRecord, int(goal))
        else:
            record = session.scalar(select(GoalRecord).where(GoalRecord.name == str(goal), GoalRecord.is_active.is_(True)))
        if record is None:
            raise KeyError(f"Goal not found: {goal}")
        return record

    @staticmethod
    def _budget_payload(session, record: BudgetRecord) -> dict[str, Any]:
        lines = list(session.scalars(select(BudgetLineRecord).where(BudgetLineRecord.budget_id == record.id).order_by(BudgetLineRecord.is_essential.desc(), BudgetLineRecord.label)))
        return {
            "id": record.id,
            "name": record.name,
            "mode": record.mode,
            "period": record.period,
            "is_default": record.is_default,
            "settings": json.loads(record.settings_json),
            "lines": [
                {
                    "id": line.id,
                    "category_slug": line.category_slug,
                    "label": line.label,
                    "amount": line.amount,
                    "source": line.source,
                    "is_essential": line.is_essential,
                    "settings": json.loads(line.settings_json),
                }
                for line in lines
            ],
        }

    @staticmethod
    def _goal_payload(record: GoalRecord) -> dict[str, Any]:
        return {
            "id": record.id,
            "name": record.name,
            "target_amount": record.target_amount,
            "current_amount": record.current_amount,
            "target_date": str(record.target_date),
            "priority": record.priority,
            "monthly_contribution": record.monthly_contribution,
            "surplus_allocation_fraction": record.surplus_allocation_fraction,
            "is_active": record.is_active,
            "settings": json.loads(record.settings_json),
        }
