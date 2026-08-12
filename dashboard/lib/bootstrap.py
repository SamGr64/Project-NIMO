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

    if "nimo_theme" not in st.session_state:
        st.session_state.nimo_theme = "light"
    if "nimo_user" not in st.session_state:
        st.session_state.nimo_user = "sample_user" if "sample_user" in available else (available[0] if available else None)

    with st.sidebar:
        st.markdown("## NIMO")
        selected_theme = st.selectbox(
            "Appearance",
            ["light", "dark"],
            index=0 if st.session_state.nimo_theme == "light" else 1,
            key="theme_selector",
        )
        st.session_state.nimo_theme = selected_theme
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
