from __future__ import annotations

from pathlib import Path

import pytest

from nimo.application.container import ApplicationContainer


@pytest.fixture(scope="session")
def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture
def data_root(tmp_path: Path) -> Path:
    return tmp_path / "data"


@pytest.fixture
def container(project_root: Path, data_root: Path) -> ApplicationContainer:
    return ApplicationContainer.for_user(
        "test_user",
        project_root=project_root,
        data_root=data_root,
        create=True,
        display_name="Test User",
    )
