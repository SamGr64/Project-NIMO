from __future__ import annotations

from pathlib import Path

from nimo.analysis.transfers import TransferDetector
from nimo.categorisation.service import CategorisationService
from nimo.domain.models import ImportResult
from nimo.ingestion.pipeline import StatementIngestionPipeline


class IngestionService:
    def __init__(
        self,
        *,
        pipeline: StatementIngestionPipeline,
        categorisation: CategorisationService,
        transfer_detector: TransferDetector,
    ) -> None:
        self.pipeline = pipeline
        self.categorisation = categorisation
        self.transfer_detector = transfer_detector

    def import_csv(
        self,
        path: Path,
        *,
        account_name: str | None = None,
        account_type: str | None = None,
        column_overrides: dict[str, str] | None = None,
        post_process: bool = True,
    ) -> ImportResult:
        result = self.pipeline.import_csv(
            path,
            account_name=account_name,
            account_type=account_type,
            column_overrides=column_overrides,
        )
        if post_process and not result.duplicate_file:
            self.categorisation.auto_categorise()
            self.transfer_detector.detect()
        return result
