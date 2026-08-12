from __future__ import annotations

from nimo.config.loader import ConfigManager
from nimo.storage.database import Database
from nimo.users.workspace import UserWorkspace, WorkspaceManager


class UserService:
    def __init__(self, config: ConfigManager) -> None:
        self.config = config
        self.workspaces = WorkspaceManager(config.paths.data_root)

    def create(
        self,
        user_name: str,
        *,
        display_name: str | None = None,
        source_type: str = "imported",
    ) -> UserWorkspace:
        workspace = self.workspaces.create(
            user_name,
            display_name=display_name,
            source_type=source_type,
            currency=self.config.app.application.default_currency,
        )
        profile = workspace.read_profile()
        user = profile.get("user", {})
        database = Database(workspace.database_path)
        database.initialize(
            user_slug=workspace.slug,
            display_name=str(user.get("display_name", display_name or user_name)),
            source_type=str(user.get("source_type", source_type)),
            currency=str(user.get("currency", self.config.app.application.default_currency)),
        )
        return workspace

    def list(self) -> list[str]:
        return self.workspaces.list_users()
