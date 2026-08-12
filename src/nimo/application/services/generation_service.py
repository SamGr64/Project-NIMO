from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from nimo.application.services.ingestion_service import IngestionService
from nimo.categorisation.service import CategorisationService
from nimo.domain.models import GenerationRequest, GenerationResult
from nimo.generation.accounts import build_accounts
from nimo.generation.latent_profile import sample_latent_profile
from nimo.generation.renderers import SeededCsvStatementRenderer
from nimo.generation.simulator import simulate_financial_life
from nimo.generation.truth import write_ground_truth
from nimo.users.workspace import UserWorkspace, slugify_user_name

GENERATOR_VERSION = "2.0.0"


class GenerationService:
    def __init__(
        self,
        *,
        workspace: UserWorkspace,
        generation_config: dict[str, Any],
        archetypes_config: dict[str, Any],
        questionnaire_config: dict[str, Any],
        statement_config: dict[str, Any],
        ingestion: IngestionService,
        categorisation: CategorisationService,
    ) -> None:
        self.workspace = workspace
        self.generation_config = generation_config
        self.archetypes_config = archetypes_config
        self.questionnaire_config = questionnaire_config
        self.statement_config = statement_config
        self.ingestion = ingestion
        self.categorisation = categorisation

    def generate(self, request: GenerationRequest) -> GenerationResult:
        if slugify_user_name(request.user_name) != self.workspace.slug:
            raise ValueError(
                f"Generation request user {request.user_name!r} does not match workspace {self.workspace.slug!r}"
            )
        profile = sample_latent_profile(
            seed=request.seed,
            generator_config=self.generation_config,
            archetypes_config=self.archetypes_config,
            questionnaire_config=self.questionnaire_config,
            archetype=request.archetype,
            questionnaire=request.questionnaire,
        )
        currency = self.generation_config.get("generation", {}).get("default_currency", "GBP")
        accounts = build_accounts(profile, currency=currency)
        simulation = simulate_financial_life(
            profile=profile,
            accounts=accounts,
            start_date=request.start_date,
            end_date=request.end_date,
        )

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        run_dir = self.workspace.synthetic_dir / f"run_{timestamp}_{request.seed}"
        statement_dir = run_dir / "statements"
        renderer = SeededCsvStatementRenderer(
            seed=request.seed,
            statement_config=self.statement_config,
        )
        statement_paths: list[Path] = []
        imported_rows = 0
        warnings: list[str] = []
        for account in accounts:
            path = renderer.render(
                simulation.transactions,
                account,
                statement_dir,
                format_name=request.statement_format,
            )
            statement_paths.append(path)
            result = self.ingestion.import_csv(
                path,
                account_name=account.name,
                account_type=account.account_type,
                post_process=False,
            )
            imported_rows += result.imported_rows
            warnings.extend(result.warnings)

        ground_truth_path = write_ground_truth(
            output_dir=run_dir,
            profile=profile,
            accounts=accounts,
            process_truth=simulation.process_truth,
            transactions=simulation.transactions,
        )
        self.categorisation.auto_categorise()
        self.ingestion.transfer_detector.detect()

        manifest = {
            "schema_version": 1,
            "generator_version": GENERATOR_VERSION,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "user": self.workspace.slug,
            "seed": request.seed,
            "archetype": profile.archetype,
            "start_date": request.start_date.isoformat(),
            "end_date": request.end_date.isoformat(),
            "statement_format": request.statement_format,
            "accounts": [account.as_dict() for account in accounts],
            "statement_paths": [str(path.relative_to(self.workspace.root)) for path in statement_paths],
            "ground_truth_path": str(ground_truth_path.relative_to(self.workspace.root)),
            "imported_rows": imported_rows,
            "warnings": warnings,
        }
        manifest_path = run_dir / "generation_manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        self.workspace.update_profile(
            {
                "user": {"source_type": "generated"},
                "generation": {
                    "latest_seed": request.seed,
                    "latest_archetype": profile.archetype,
                    "latest_manifest": str(manifest_path.relative_to(self.workspace.root)),
                },
            }
        )
        return GenerationResult(
            user_name=self.workspace.slug,
            seed=request.seed,
            archetype=profile.archetype,
            statement_paths=statement_paths,
            imported_rows=imported_rows,
            account_count=len(accounts),
            manifest_path=manifest_path,
            warnings=warnings,
        )
