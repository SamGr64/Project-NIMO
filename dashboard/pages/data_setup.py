from __future__ import annotations

from datetime import date

from nimo.application.container import ApplicationContainer
from nimo.domain.models import GenerationRequest


def render(ctx) -> None:
    import streamlit as st

    st.title("Data & Setup")
    st.caption("Create a synthetic profile or import statements into a normalised local database.")
    generate_tab, import_tab, users_tab = st.tabs(["Generate", "Import", "Profiles"])

    with generate_tab:
        with st.form("generate_user_form"):
            user_name = st.text_input("Profile name", value="sample_user")
            archetypes = sorted(ctx.config.mapping("archetypes").get("archetypes", {}))
            archetype_choice = st.selectbox("Archetype", ["Seeded random", *archetypes])
            seed = st.number_input("Seed", value=42, step=1)
            start_date = st.date_input("Start date", value=date(2024, 1, 1))
            end_date = st.date_input("End date", value=date.today())
            submitted = st.form_submit_button("Generate and analyse")
        if submitted:
            workspace = ctx.users.create(user_name, source_type="generated")
            container = ApplicationContainer.for_user(
                workspace.slug,
                project_root=ctx.config.paths.project_root,
                data_root=ctx.config.paths.data_root,
            )
            result = container.generation.generate(
                GenerationRequest(
                    user_name=workspace.slug,
                    seed=int(seed),
                    start_date=start_date,
                    end_date=end_date,
                    archetype=None if archetype_choice == "Seeded random" else archetype_choice,
                )
            )
            st.session_state.nimo_user = workspace.slug
            st.success(f"Generated {result.imported_rows:,} rows across {result.account_count} accounts.")
            st.rerun()

    with import_tab:
        user_name = st.text_input("Profile name for import", value=ctx.selected_user or "my_profile")
        account_name = st.text_input("Account name (optional)")
        uploaded = st.file_uploader("CSV statement", type=["csv"])
        if st.button("Import statement", disabled=uploaded is None):
            workspace = ctx.users.create(user_name, source_type="imported")
            temporary = workspace.cache_dir / uploaded.name
            temporary.parent.mkdir(parents=True, exist_ok=True)
            temporary.write_bytes(uploaded.getbuffer())
            container = ApplicationContainer.for_user(
                workspace.slug,
                project_root=ctx.config.paths.project_root,
                data_root=ctx.config.paths.data_root,
            )
            result = container.ingestion.import_csv(
                temporary,
                account_name=account_name or None,
            )
            st.session_state.nimo_user = workspace.slug
            st.success(
                f"Imported {result.imported_rows:,} rows and superseded {result.superseded_rows:,} older overlapping rows."
            )
            st.rerun()

    with users_tab:
        st.dataframe({"User profile": ctx.users.list()}, use_container_width=True)
