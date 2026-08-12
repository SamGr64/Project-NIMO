from __future__ import annotations

import csv
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from sqlalchemy import select

from nimo.categorisation.taxonomy import CategoryDefinition, iter_category_definitions
from nimo.storage.database import Database
from nimo.storage.models import CategoryRule, Transaction
from nimo.storage.repositories import CategoryRepository, TransactionRepository
from nimo.users.workspace import UserWorkspace


class CategorisationService:
    def __init__(
        self,
        *,
        database: Database,
        workspace: UserWorkspace,
        categories_config: dict[str, Any],
        prompts_root: Path,
    ) -> None:
        self.database = database
        self.workspace = workspace
        self.categories_config = categories_config
        self.prompts_root = prompts_root
        self.categories = CategoryRepository()
        self.transactions = TransactionRepository()

    def ensure_taxonomy(self) -> int:
        definitions = list(iter_category_definitions(self.categories_config))
        created = 0
        with self.database.session() as session:
            parent_ids: dict[str, int] = {}
            for definition in definitions:
                existing = self.categories.by_slug(session, definition.slug)
                category = self.categories.ensure(
                    session,
                    slug=definition.slug,
                    label=definition.label,
                    direction=definition.direction,
                    is_custom=False,
                    parent_id=(
                        parent_ids.get(definition.parent_slug)
                        if definition.parent_slug is not None
                        else None
                    ),
                )
                parent_ids[definition.slug] = category.id
                if existing is None:
                    created += 1
        return created

    def list_categories(self) -> list[dict[str, Any]]:
        self.ensure_taxonomy()
        with self.database.session() as session:
            return [
                {
                    "id": category.id,
                    "slug": category.slug,
                    "label": category.label,
                    "direction": category.direction,
                    "is_custom": category.is_custom,
                }
                for category in self.categories.list(session)
            ]

    def create_custom_category(
        self,
        *,
        slug: str,
        label: str,
        direction: str = "either",
    ) -> int:
        clean_slug = re.sub(r"[^a-z0-9]+", "_", slug.strip().lower()).strip("_")
        if not clean_slug:
            raise ValueError("Custom category slug cannot be empty")
        with self.database.session() as session:
            category = self.categories.ensure(
                session,
                slug=clean_slug,
                label=label.strip(),
                direction=direction,
                is_custom=True,
            )
            return category.id

    def assign_manual(self, transaction_ids: list[int], category_slug: str) -> int:
        if not transaction_ids:
            return 0
        self.ensure_taxonomy()
        with self.database.session() as session:
            category = self.categories.by_slug(session, category_slug)
            if category is None:
                raise KeyError(f"Unknown category: {category_slug}")
            rows = list(
                session.scalars(
                    select(Transaction).where(
                        Transaction.id.in_(transaction_ids),
                        Transaction.is_active.is_(True),
                    )
                )
            )
            for row in rows:
                row.category_id = category.id
                row.category_source = "manual"
                row.category_confidence = 1.0
            return len(rows)

    def add_rule(
        self,
        *,
        name: str,
        pattern: str,
        category_slug: str,
        is_regex: bool = False,
        field: str = "description",
        priority: int = 100,
    ) -> int:
        self.ensure_taxonomy()
        if field not in {"description", "merchant"}:
            raise ValueError("Category-rule field must be 'description' or 'merchant'")
        if is_regex:
            re.compile(pattern)
        with self.database.session() as session:
            category = self.categories.by_slug(session, category_slug)
            if category is None:
                raise KeyError(f"Unknown category: {category_slug}")
            rule = CategoryRule(
                name=name,
                pattern=pattern,
                category_id=category.id,
                field=field,
                is_regex=is_regex,
                priority=priority,
            )
            session.add(rule)
            session.flush()
            return rule.id

    def auto_categorise(self, *, overwrite_automatic: bool = True) -> dict[str, int]:
        self.ensure_taxonomy()
        definitions = list(iter_category_definitions(self.categories_config))
        definition_by_slug = {definition.slug: definition for definition in definitions}
        assigned_rules = 0
        assigned_builtin = 0

        with self.database.session() as session:
            categories = {category.slug: category for category in self.categories.list(session)}
            rules = self.categories.rules(session)
            statement = select(Transaction).where(Transaction.is_active.is_(True))
            if not overwrite_automatic:
                statement = statement.where(Transaction.category_id.is_(None))
            else:
                statement = statement.where(
                    (Transaction.category_source.is_(None))
                    | (Transaction.category_source.in_(["builtin", "user_rule", "llm"]))
                )
            rows = list(session.scalars(statement))

            for transaction in rows:
                if transaction.category_source in {"builtin", "user_rule", "llm"}:
                    transaction.category_id = None
                    transaction.category_source = None
                    transaction.category_confidence = None
                source_text = transaction.description_raw
                merchant_text = transaction.merchant_normalised or source_text
                matched = False
                for rule in rules:
                    haystack = source_text if rule.field == "description" else merchant_text
                    if _matches(haystack, rule.pattern, rule.is_regex):
                        transaction.category_id = rule.category_id
                        transaction.category_source = "user_rule"
                        transaction.category_confidence = 0.98
                        assigned_rules += 1
                        matched = True
                        break
                if matched:
                    continue

                lowered = f"{source_text} {merchant_text}".lower()
                best: tuple[int, CategoryDefinition] | None = None
                for definition in definitions:
                    if definition.direction == "credit" and transaction.amount <= 0:
                        continue
                    if definition.direction == "debit" and transaction.amount >= 0:
                        continue
                    keyword_hits = sum(1 for keyword in definition.keywords if keyword in lowered)
                    if keyword_hits and (best is None or keyword_hits > best[0]):
                        best = (keyword_hits, definition)
                if best is not None:
                    definition = best[1]
                    transaction.category_id = categories[definition.slug].id
                    transaction.category_source = "builtin"
                    transaction.category_confidence = min(0.97, 0.74 + 0.08 * best[0])
                    assigned_builtin += 1

        return {"user_rule": assigned_rules, "builtin": assigned_builtin}


    def import_llm_suggestions(
        self,
        path: Path,
        *,
        override_builtin: bool = False,
    ) -> dict[str, int]:
        """Import reviewed model suggestions without overriding manual or user-rule choices."""
        self.ensure_taxonomy()
        frame = pd.read_csv(path)
        id_column = (
            "transaction_id"
            if "transaction_id" in frame.columns
            else "id" if "id" in frame.columns else None
        )
        category_column = (
            "category_slug"
            if "category_slug" in frame.columns
            else "category" if "category" in frame.columns else None
        )
        if id_column is None or category_column is None:
            raise KeyError("Suggestion CSV must contain transaction_id/id and category_slug/category")
        confidence_column = "confidence" if "confidence" in frame.columns else None
        counts = {"applied": 0, "skipped": 0, "invalid": 0}
        with self.database.session() as session:
            category_by_slug = {category.slug: category for category in self.categories.list(session)}
            for row in frame.to_dict(orient="records"):
                try:
                    transaction_id = int(row[id_column])
                except (TypeError, ValueError):
                    counts["invalid"] += 1
                    continue
                slug = str(row[category_column]).strip().lower()
                category = category_by_slug.get(slug)
                transaction = session.get(Transaction, transaction_id)
                if category is None or transaction is None or not transaction.is_active:
                    counts["invalid"] += 1
                    continue
                if transaction.category_source in {"manual", "user_rule"}:
                    counts["skipped"] += 1
                    continue
                if transaction.category_source == "builtin" and not override_builtin:
                    counts["skipped"] += 1
                    continue
                confidence = 0.5
                raw_confidence = row.get(confidence_column) if confidence_column else None
                if raw_confidence is not None and not pd.isna(raw_confidence):
                    try:
                        confidence = min(1.0, max(0.0, float(raw_confidence)))
                    except (TypeError, ValueError):
                        confidence = 0.5
                transaction.category_id = category.id
                transaction.category_source = "llm"
                transaction.category_confidence = confidence
                counts["applied"] += 1
        return counts

    def export_for_llm(self, *, filename_prefix: str = "categorisation") -> tuple[Path, Path]:
        self.ensure_taxonomy()
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        csv_path = self.workspace.exports_dir / f"{filename_prefix}_{timestamp}.csv"
        prompt_path = self.workspace.exports_dir / f"{filename_prefix}_{timestamp}_prompt.md"
        self.workspace.exports_dir.mkdir(parents=True, exist_ok=True)

        with self.database.session() as session:
            frame = self.transactions.active_frame(session)
        export_columns = [
            "id",
            "booking_date",
            "account_name",
            "description_raw",
            "merchant_normalised",
            "amount",
            "currency",
            "category_slug",
        ]
        frame.to_csv(csv_path, columns=export_columns, index=False, quoting=csv.QUOTE_MINIMAL)

        system_prompt = (self.prompts_root / "categorisation_system.md").read_text(encoding="utf-8")
        request_prompt = (self.prompts_root / "categorisation_request.md").read_text(encoding="utf-8")
        taxonomy = "\n".join(
            f"- {item['slug']}: {item['label']}" for item in self.list_categories()
        )
        prompt_path.write_text(
            f"# System instruction\n\n{system_prompt}\n\n# Request\n\n{request_prompt}"
            f"\n\n# Allowed taxonomy\n\n{taxonomy}\n\n"
            "Return CSV or JSON containing transaction id, category slug, confidence, and reason.\n",
            encoding="utf-8",
        )
        return csv_path, prompt_path


def _matches(haystack: str, pattern: str, is_regex: bool) -> bool:
    if is_regex:
        return re.search(pattern, haystack, flags=re.IGNORECASE) is not None
    return pattern.lower() in haystack.lower()
