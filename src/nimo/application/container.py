from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from nimo.analysis.transfers import TransferDetector
from nimo.application.services import (
    AnalysisService,
    BackupService,
    BehaviourService,
    ForecastService,
    InvestmentService,
    GenerationService,
    IngestionService,
    LayoutService,
    PlanningService,
    ReportService,
    UserService,
)
from nimo.categorisation.service import CategorisationService
from nimo.config.loader import ConfigManager
from nimo.ingestion.pipeline import StatementIngestionPipeline
from nimo.storage.database import Database
from nimo.users.workspace import UserWorkspace, WorkspaceManager


class ApplicationContainer:
    """Construct the shared services used by both CLI and dashboard."""

    def __init__(
        self,
        *,
        config: ConfigManager,
        workspace: UserWorkspace,
        database: Database,
    ) -> None:
        self.config = config
        self.workspace = workspace
        self.database = database
        profile_overrides = workspace.read_profile().get("model_overrides", {})
        analysis_config = _deep_merge(config.mapping("analysis"), profile_overrides.get("analysis", {}))
        forecasting_config = _deep_merge(config.mapping("forecasting"), profile_overrides.get("forecasting", {}))
        budgeting_config = _deep_merge(config.mapping("budgeting"), profile_overrides.get("budgeting", {}))
        investing_config = _deep_merge(config.mapping("investing"), profile_overrides.get("investing", {}))
        reporting_config = _deep_merge(config.mapping("reporting"), profile_overrides.get("reporting", {}))

        self.categorisation = CategorisationService(
            database=database,
            workspace=workspace,
            categories_config=config.mapping("categories"),
            prompts_root=config.paths.prompts_root,
        )
        self.transfer_detector = TransferDetector(
            database=database,
            analysis_config=analysis_config,
        )
        pipeline = StatementIngestionPipeline(
            database=database,
            workspace=workspace,
            statement_config=config.mapping("statement_formats"),
            currency_default=config.app.application.default_currency,
        )
        self.ingestion = IngestionService(
            pipeline=pipeline,
            categorisation=self.categorisation,
            transfer_detector=self.transfer_detector,
        )
        self.generation = GenerationService(
            workspace=workspace,
            generation_config=config.mapping("generator"),
            archetypes_config=config.mapping("archetypes"),
            questionnaire_config=config.mapping("questionnaire"),
            statement_config=config.mapping("statement_formats"),
            ingestion=self.ingestion,
            categorisation=self.categorisation,
        )
        self.analysis = AnalysisService(
            database=database,
            analysis_config=analysis_config,
            categorisation=self.categorisation,
            transfer_detector=self.transfer_detector,
        )
        self.behaviours = BehaviourService(
            database=database,
            analysis_config=analysis_config,
        )
        self.forecasting = ForecastService(
            database=database,
            workspace=workspace,
            config=forecasting_config,
            behaviours=self.behaviours,
        )
        self.planning = PlanningService(
            database=database,
            config=budgeting_config,
            forecasting=self.forecasting,
        )
        self.investing = InvestmentService(
            database=database,
            workspace=workspace,
            config=investing_config,
            forecasting=self.forecasting,
        )
        self.reporting = ReportService(
            database=database,
            workspace=workspace,
            config=reporting_config,
            prompts_root=config.paths.prompts_root,
            analysis=self.analysis,
            behaviours=self.behaviours,
            forecasting=self.forecasting,
            planning=self.planning,
            investing=self.investing,
        )
        self.layouts = LayoutService(
            database=database,
            default_layouts=config.mapping("dashboard/default_layouts"),
        )
        self.backups = BackupService(database=database, workspace=workspace)

    @classmethod
    def for_user(
        cls,
        user_name: str,
        *,
        project_root: Path | None = None,
        data_root: Path | None = None,
        create: bool = False,
        display_name: str | None = None,
        source_type: str = "imported",
    ) -> "ApplicationContainer":
        config = ConfigManager.discover(project_root=project_root, data_root=data_root)
        users = UserService(config)
        manager = WorkspaceManager(config.paths.data_root)
        if create:
            workspace = users.create(
                user_name,
                display_name=display_name,
                source_type=source_type,
            )
        else:
            workspace = manager.workspace(user_name)
        profile = workspace.read_profile()
        user = profile.get("user", {})
        database = Database(workspace.database_path)
        database.initialize(
            user_slug=workspace.slug,
            display_name=str(user.get("display_name", display_name or user_name)),
            source_type=str(user.get("source_type", source_type)),
            currency=str(user.get("currency", config.app.application.default_currency)),
        )
        container = cls(config=config, workspace=workspace, database=database)
        container.categorisation.ensure_taxonomy()
        return container


def _deep_merge(base: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged
