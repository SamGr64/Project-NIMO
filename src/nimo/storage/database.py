from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import Engine, create_engine, event, select
from sqlalchemy.orm import Session, sessionmaker

from nimo.storage.migrations import run_migrations
from nimo.storage.models import Base, UserRecord


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.engine: Engine = create_engine(
            f"sqlite:///{self.path}",
            future=True,
            connect_args={"check_same_thread": False},
        )
        event.listen(self.engine, "connect", _enable_sqlite_foreign_keys)
        self.session_factory = sessionmaker(bind=self.engine, expire_on_commit=False, future=True)

    def initialize(
        self,
        *,
        user_slug: str,
        display_name: str,
        source_type: str = "imported",
        currency: str = "GBP",
    ) -> None:
        Base.metadata.create_all(self.engine)
        with self.session() as session:
            run_migrations(self.engine, session)
            existing = session.scalar(select(UserRecord).where(UserRecord.slug == user_slug))
            if existing is None:
                session.add(
                    UserRecord(
                        slug=user_slug,
                        display_name=display_name,
                        source_type=source_type,
                        currency=currency,
                    )
                )

    @contextmanager
    def session(self) -> Iterator[Session]:
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


def _enable_sqlite_foreign_keys(dbapi_connection: object, _connection_record: object) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
