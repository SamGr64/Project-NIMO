from __future__ import annotations

from dataclasses import dataclass

from nimo.application.container import ApplicationContainer
from nimo.application.services.user_service import UserService
from nimo.config.loader import ConfigManager


@dataclass(slots=True)
class DashboardContext:
    config: ConfigManager
    users: UserService
    selected_user: str | None
    container: ApplicationContainer | None
    theme_name: str
