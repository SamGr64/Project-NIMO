from __future__ import annotations

import secrets
from datetime import date

from nimo.application.container import ApplicationContainer
from nimo.domain.models import GenerationRequest


def render(ctx) -> None:
    import streamlit as st

    st.title("Data & Setup")
    st.caption("Create a synthetic profile or import statements into a normalised local database.")
    if message := st.session_state.pop("nimo_flash", None):
        st.success(message)
    generate_tab, import_tab, users_tab = st.tabs(["Generate", "Import", "Profiles"])

    with generate_tab:
        generation_mode = st.radio(
            "How should NIMO shape the synthetic user?",
            ["Seeded random", "Choose an archetype", "Build a financial twin"],
            horizontal=True,
            help=(
                "An archetype supplies broad priors. The financial-twin questionnaire constrains "
                "continuous behavioural traits; the seed still creates an individual inside those ranges."
            ),
        )
        seed_mode = st.radio(
            "Seed",
            ["Choose a seed", "Create one automatically"],
            horizontal=True,
        )
        questionnaire_config = ctx.config.mapping("questionnaire")
        with st.form("generate_user_form"):
            user_name = st.text_input("Profile name", value="sample_user")
            archetype_choice: str | None = None
            questionnaire_answers: dict[str, str] = {}
            if generation_mode == "Choose an archetype":
                archetypes = ctx.config.mapping("archetypes").get("archetypes", {})
                archetype_choice = st.selectbox(
                    "Archetype",
                    sorted(archetypes),
                    format_func=lambda key: archetypes[key].get("label", key),
                )
                selected = archetypes.get(archetype_choice, {})
                if selected.get("description"):
                    st.caption(selected["description"])
            elif generation_mode == "Build a financial twin":
                st.subheader("Financial-twin questionnaire")
                for question in questionnaire_config.get("questions", []):
                    answers = question.get("answers", {})
                    answer_id = st.selectbox(
                        question.get("text", question["id"]),
                        list(answers),
                        format_func=lambda key: key.replace("_", " ").title(),
                        key=f"twin_{question['id']}",
                    )
                    questionnaire_answers[str(question["id"])] = str(answer_id)

            chosen_seed = st.number_input(
                "Numeric seed",
                value=42,
                step=1,
                disabled=seed_mode == "Create one automatically",
                help="The same seed, dates and generator inputs reproduce the same synthetic person.",
            )
            start_date = st.date_input("Start date", value=date(2024, 1, 1))
            end_date = st.date_input("End date", value=date.today())
            submitted = st.form_submit_button("Generate and analyse")
        if submitted:
            seed = secrets.randbits(63) if seed_mode == "Create one automatically" else int(chosen_seed)
            workspace = ctx.users.create(user_name, source_type="generated")
            container = ApplicationContainer.for_user(
                workspace.slug,
                project_root=ctx.config.paths.project_root,
                data_root=ctx.config.paths.data_root,
            )
            result = container.generation.generate(
                GenerationRequest(
                    user_name=workspace.slug,
                    seed=seed,
                    start_date=start_date,
                    end_date=end_date,
                    archetype=archetype_choice,
                    questionnaire=questionnaire_answers or None,
                )
            )
            st.session_state.nimo_user = workspace.slug
            st.session_state.nimo_flash = (
                f"Generated {result.imported_rows:,} rows across {result.account_count} accounts "
                f"using seed {seed} and inferred archetype {result.archetype}."
            )
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
            st.session_state.nimo_flash = (
                f"Imported {result.imported_rows:,} rows and superseded "
                f"{result.superseded_rows:,} older overlapping rows."
            )
            st.rerun()

    with users_tab:
        st.dataframe({"User profile": ctx.users.list()}, use_container_width=True)
