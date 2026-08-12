from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from nimo.storage.models import Category, CategoryRule


class CategoryRepository:
    def list(self, session: Session, *, active_only: bool = True) -> list[Category]:
        statement = select(Category).order_by(Category.label)
        if active_only:
            statement = statement.where(Category.is_active.is_(True))
        return list(session.scalars(statement))

    def by_slug(self, session: Session, slug: str) -> Category | None:
        return session.scalar(select(Category).where(Category.slug == slug))

    def ensure(
        self,
        session: Session,
        *,
        slug: str,
        label: str,
        direction: str = "either",
        is_custom: bool = False,
        parent_id: int | None = None,
    ) -> Category:
        existing = self.by_slug(session, slug)
        if existing is not None:
            return existing
        category = Category(
            slug=slug,
            label=label,
            direction=direction,
            is_custom=is_custom,
            parent_id=parent_id,
        )
        session.add(category)
        session.flush()
        return category

    def rules(self, session: Session) -> list[CategoryRule]:
        return list(
            session.scalars(
                select(CategoryRule)
                .where(CategoryRule.is_active.is_(True))
                .order_by(CategoryRule.priority.desc(), CategoryRule.id)
            )
        )
