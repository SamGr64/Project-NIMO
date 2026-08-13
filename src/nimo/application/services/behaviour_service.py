from __future__ import annotations

import hashlib
import json
from typing import Any

import pandas as pd
from sqlalchemy import delete, select, update

from nimo import __version__
from nimo.analysis.behaviours import build_behavioural_map
from nimo.analysis.overview import compute_overview_metrics
from nimo.storage.database import Database
from nimo.storage.models import (
    Account,
    BehaviouralMapRecord,
    BehaviourPattern,
    BehaviourRun,
    TransactionOutlier,
)
from nimo.storage.repositories import TransactionRepository
from nimo.storage.versioning import source_data_version


class BehaviourService:
    def __init__(self, *, database: Database, analysis_config: dict[str, Any]) -> None:
        self.database = database
        self.analysis_config = analysis_config
        self.transactions = TransactionRepository()

    def refresh(self, *, force: bool = False) -> dict[str, Any]:
        with self.database.session() as session:
            data_version = source_data_version(session)
            existing = session.scalar(
                select(BehaviouralMapRecord)
                .where(
                    BehaviouralMapRecord.is_current.is_(True),
                    BehaviouralMapRecord.source_data_version == data_version,
                )
                .order_by(BehaviouralMapRecord.id.desc())
            )
            if existing is not None and not force:
                return json.loads(existing.map_json)
            frame = self.transactions.active_frame(session)
            opening = {
                account.id: float(account.opening_balance)
                for account in session.scalars(select(Account).where(Account.is_active.is_(True)))
            }
            metrics = compute_overview_metrics(
                frame,
                account_opening=opening,
                recent_weight_decay=float(self.analysis_config.get("metrics", {}).get("recent_weight_decay", 0.85)),
            )
            config_hash = hashlib.sha256(
                json.dumps(self.analysis_config.get("behaviour", {}), sort_keys=True).encode("utf-8")
            ).hexdigest()
            run = BehaviourRun(
                source_data_version=data_version,
                model_version=__version__,
                config_hash=config_hash,
                status="running",
                diagnostics_json="{}",
            )
            session.add(run)
            session.flush()

            payload, patterns, outliers = build_behavioural_map(
                frame,
                overview=metrics.as_dict(),
                config=self.analysis_config,
            )
            for pattern in patterns:
                session.add(
                    BehaviourPattern(
                        run_id=run.id,
                        scope_type=pattern["scope_type"],
                        scope_key=pattern["scope_key"],
                        account_id=pattern["account_id"],
                        category_id=pattern["category_id"],
                        sample_count=pattern["sample_count"],
                        periodic_score=pattern["periodic_score"],
                        spontaneous_score=pattern["spontaneous_score"],
                        distributional_score=pattern["distributional_score"],
                        pattern_json=json.dumps(pattern["payload"], sort_keys=True),
                    )
                )
            if not outliers.empty:
                for row in outliers.to_dict(orient="records"):
                    session.add(
                        TransactionOutlier(
                            run_id=run.id,
                            transaction_id=int(row["transaction_id"]),
                            scope_key=str(row["scope_key"]),
                            robust_z=float(row["robust_z"]),
                            surprise_score=float(row["surprise_score"]),
                            is_outlier=bool(row["is_outlier"]),
                            evidence_json=json.dumps(row["evidence"], sort_keys=True),
                        )
                    )
            session.execute(update(BehaviouralMapRecord).values(is_current=False))
            archetype = payload["archetype"]
            record = BehaviouralMapRecord(
                run_id=run.id,
                source_data_version=data_version,
                map_json=json.dumps(payload, sort_keys=True),
                archetype_label=str(archetype["label"]),
                archetype_confidence=float(archetype["confidence"]),
                is_current=True,
            )
            session.add(record)
            run.status = "complete"
            run.diagnostics_json = json.dumps(
                {
                    "pattern_count": len(patterns),
                    "outlier_scores": int(len(outliers)),
                    "flagged_outliers": int(outliers["is_outlier"].sum()) if not outliers.empty else 0,
                },
                sort_keys=True,
            )
            return payload

    def current(self, *, refresh_if_stale: bool = True) -> dict[str, Any]:
        with self.database.session() as session:
            current_version = source_data_version(session)
            record = session.scalar(
                select(BehaviouralMapRecord)
                .where(BehaviouralMapRecord.is_current.is_(True))
                .order_by(BehaviouralMapRecord.id.desc())
            )
            if record is not None and (not refresh_if_stale or record.source_data_version == current_version):
                return json.loads(record.map_json)
        return self.refresh()

    def current_record_id(self) -> int | None:
        with self.database.session() as session:
            return session.scalar(
                select(BehaviouralMapRecord.id)
                .where(BehaviouralMapRecord.is_current.is_(True))
                .order_by(BehaviouralMapRecord.id.desc())
            )

    def patterns_frame(self, *, scope_type: str | None = None) -> pd.DataFrame:
        with self.database.session() as session:
            current = session.scalar(
                select(BehaviouralMapRecord)
                .where(BehaviouralMapRecord.is_current.is_(True))
                .order_by(BehaviouralMapRecord.id.desc())
            )
            if current is None:
                return pd.DataFrame()
            statement = select(BehaviourPattern).where(BehaviourPattern.run_id == current.run_id)
            if scope_type:
                statement = statement.where(BehaviourPattern.scope_type == scope_type)
            records = list(session.scalars(statement.order_by(BehaviourPattern.periodic_score.desc())))
            return pd.DataFrame(
                [
                    {
                        "scope_type": record.scope_type,
                        "scope_key": record.scope_key,
                        "sample_count": record.sample_count,
                        "periodic_score": record.periodic_score,
                        "spontaneous_score": record.spontaneous_score,
                        "distributional_score": record.distributional_score,
                        **json.loads(record.pattern_json),
                    }
                    for record in records
                ]
            )

    def outliers_frame(self, *, flagged_only: bool = True) -> pd.DataFrame:
        with self.database.session() as session:
            current = session.scalar(
                select(BehaviouralMapRecord)
                .where(BehaviouralMapRecord.is_current.is_(True))
                .order_by(BehaviouralMapRecord.id.desc())
            )
            if current is None:
                return pd.DataFrame()
            statement = select(TransactionOutlier).where(TransactionOutlier.run_id == current.run_id)
            if flagged_only:
                statement = statement.where(TransactionOutlier.is_outlier.is_(True))
            records = list(session.scalars(statement.order_by(TransactionOutlier.surprise_score.desc())))
            return pd.DataFrame(
                [
                    {
                        "transaction_id": record.transaction_id,
                        "scope_key": record.scope_key,
                        "robust_z": record.robust_z,
                        "surprise_score": record.surprise_score,
                        "is_outlier": record.is_outlier,
                        "evidence": json.loads(record.evidence_json),
                    }
                    for record in records
                ]
            )

    def clear(self) -> None:
        with self.database.session() as session:
            session.execute(delete(TransactionOutlier))
            session.execute(delete(BehaviourPattern))
            session.execute(delete(BehaviouralMapRecord))
            session.execute(delete(BehaviourRun))
