from __future__ import annotations

from pathlib import Path

from nimo.application.container import ApplicationContainer
from nimo.application.services.user_service import UserService
from nimo.config.loader import ConfigManager

from dashboard.lib.context import DashboardContext


def bootstrap_dashboard(st, project_root: Path) -> DashboardContext:
    config = ConfigManager.discover(project_root=project_root)
    users = UserService(config)
    available = users.list()

    if "nimo_user" not in st.session_state:
        st.session_state.nimo_user = "sample_user" if "sample_user" in available else (available[0] if available else None)

    with st.sidebar:
        st.markdown("## NIMO")
        if available:
            current = st.session_state.nimo_user if st.session_state.nimo_user in available else available[0]
            selected_user = st.selectbox(
                "User profile",
                available,
                index=available.index(current),
                key="user_selector",
            )
            st.session_state.nimo_user = selected_user
        else:
            selected_user = None
            st.info("Create or generate a user from Data & Setup.")

        stored_theme = "light"
        if selected_user is not None:
            workspace = users.workspaces.workspace(selected_user)
            preference = str(workspace.read_profile().get("preferences", {}).get("theme", "light")).lower()
            if preference in {"light", "dark"}:
                stored_theme = preference
        selected_theme = st.selectbox(
            "Appearance",
            ["light", "dark"],
            index=0 if stored_theme == "light" else 1,
            key=f"theme_selector_{selected_user or 'no_user'}",
        )
        st.session_state.nimo_theme = selected_theme
        if selected_user is not None and selected_theme != stored_theme:
            users.workspaces.workspace(selected_user).update_profile(
                {"preferences": {"theme": selected_theme}}
            )

    container = None
    if selected_user is not None:
        container = ApplicationContainer.for_user(
            selected_user,
            project_root=config.paths.project_root,
            data_root=config.paths.data_root,
        )
    return DashboardContext(
        config=config,
        users=users,
        selected_user=selected_user,
        container=container,
        theme_name=selected_theme,
    )
