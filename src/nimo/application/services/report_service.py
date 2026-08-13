from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select

from nimo.application.services.analysis_service import AnalysisService
from nimo.application.services.behaviour_service import BehaviourService
from nimo.application.services.forecast_service import ForecastService
from nimo.application.services.investment_service import InvestmentService
from nimo.application.services.planning_service import PlanningService
from nimo.reporting import (
    OfflineNarrativeProvider,
    OpenAINarrativeProvider,
    build_evidence,
    render_docx,
    render_html,
    render_markdown,
    render_pdf,
)
from nimo.storage.database import Database
from nimo.storage.models import ReportRunRecord
from nimo.storage.versioning import source_data_version
from nimo.users.workspace import UserWorkspace


class ReportService:
    def __init__(
        self,
        *,
        database: Database,
        workspace: UserWorkspace,
        config: dict[str, Any],
        prompts_root: Path,
        analysis: AnalysisService,
        behaviours: BehaviourService,
        forecasting: ForecastService,
        planning: PlanningService,
        investing: InvestmentService,
    ) -> None:
        self.database = database
        self.workspace = workspace
        self.config = config
        self.prompts_root = prompts_root
        self.analysis = analysis
        self.behaviours = behaviours
        self.forecasting = forecasting
        self.planning = planning
        self.investing = investing

    def build(
        self,
        *,
        period_start: date | None = None,
        period_end: date | None = None,
        formats: list[str] | None = None,
        use_llm: bool | None = None,
        model: str | None = None,
        include_forecast: bool = True,
        include_budget: bool = True,
        include_investing: bool = True,
    ) -> dict[str, Any]:
        formats = [item.lower() for item in (formats or [self.config.get("rendering", {}).get("default_format", "html")])]
        supported = {"html", "md", "markdown", "pdf", "docx"}
        unknown = set(formats) - supported
        if unknown:
            raise ValueError(f"Unsupported report formats: {sorted(unknown)}")
        metrics = self.analysis.overview(start_date=period_start, end_date=period_end)
        accounts = self.analysis.accounts(start_date=period_start, end_date=period_end)
        categories = self.analysis.categories(start_date=period_start, end_date=period_end)
        monthly = self.analysis.monthly(start_date=period_start, end_date=period_end)
        behaviour_map = self.behaviours.current()
        simulation_cfg = self.config.get("simulation", {})
        forecast_runs = int(simulation_cfg.get("forecast_runs", 1000))
        budget_runs = int(simulation_cfg.get("budget_runs", 1000))
        goal_runs = int(simulation_cfg.get("goal_runs", 1000))
        forecast = self.forecasting.latest_run() if include_forecast else None
        if include_forecast and forecast is None:
            forecast = self.forecasting.run(horizon_months=12, runs=forecast_runs, seed=7291)
        budget = self.planning.evaluate(runs=budget_runs) if include_budget else None
        goals: list[dict[str, Any]] = []
        if include_budget:
            for goal in self.planning.goals():
                simulated = self.planning.simulate_goal(
                    goal["id"],
                    runs=goal_runs,
                    seed=91000 + int(goal["id"]),
                )
                goals.append(
                    {
                        **goal,
                        "probability_achieved": simulated.get("probability_achieved"),
                        "expected_final_amount": simulated.get("expected_final_amount"),
                        "median_final_amount": simulated.get("median_final_amount"),
                        "horizon_months": simulated.get("horizon_months"),
                    }
                )
        investment = self.investing.latest_run() if include_investing else None
        with self.database.session() as session:
            data_version = source_data_version(session)
        evidence = build_evidence(
            user_name=self.workspace.slug,
            period_start=period_start or metrics.date_start,
            period_end=period_end or metrics.date_end,
            overview=metrics.as_dict(),
            accounts=accounts,
            categories=categories,
            monthly=monthly,
            behaviour_map=behaviour_map,
            forecast=forecast,
            budget=budget,
            goals=goals,
            investment=investment,
            source_data_version=data_version,
        )
        llm_cfg = self.config.get("llm", {})
        llm_enabled = bool(llm_cfg.get("enabled_by_default", False)) if use_llm is None else bool(use_llm)
        if llm_enabled:
            provider = OpenAINarrativeProvider(prompts_root=self.prompts_root)
            provider_model = model or str(llm_cfg.get("model", "gpt-5-mini"))
        else:
            provider = OfflineNarrativeProvider()
            provider_model = None
        narrative = provider.generate(evidence, model=provider_model)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        base = self.workspace.reports_dir / f"nimo_report_{timestamp}"
        outputs: dict[str, str] = {}
        for format_name in formats:
            if format_name == "html":
                path = render_html(evidence=evidence, narrative=narrative, output_path=base.with_suffix(".html"))
            elif format_name in {"md", "markdown"}:
                path = render_markdown(evidence=evidence, narrative=narrative, output_path=base.with_suffix(".md"))
            elif format_name == "pdf":
                path = render_pdf(evidence=evidence, narrative=narrative, output_path=base.with_suffix(".pdf"))
            else:
                path = render_docx(evidence=evidence, narrative=narrative, output_path=base.with_suffix(".docx"))
            outputs[format_name] = self.workspace.path_for_storage(path)
        with self.database.session() as session:
            record = ReportRunRecord(
                period_start=period_start or metrics.date_start,
                period_end=period_end or metrics.date_end,
                provider=provider.name,
                model=provider_model,
                evidence_json=json.dumps(evidence, sort_keys=True, default=str),
                narrative_json=narrative.model_dump_json(),
                output_paths_json=json.dumps(outputs, sort_keys=True),
                source_data_version=data_version,
            )
            session.add(record)
            session.flush()
            report_id = record.id
        return {
            "report_id": report_id,
            "provider": provider.name,
            "model": provider_model,
            "outputs": outputs,
            "narrative": narrative.model_dump(),
            "source_data_version": data_version,
        }

    def list(self) -> list[dict[str, Any]]:
        with self.database.session() as session:
            return [
                {
                    "id": record.id,
                    "period_start": None if record.period_start is None else str(record.period_start),
                    "period_end": None if record.period_end is None else str(record.period_end),
                    "provider": record.provider,
                    "model": record.model,
                    "outputs": json.loads(record.output_paths_json),
                    "source_data_version": record.source_data_version,
                    "created_at": record.created_at.isoformat(),
                }
                for record in session.scalars(select(ReportRunRecord).order_by(ReportRunRecord.id.desc()))
            ]
