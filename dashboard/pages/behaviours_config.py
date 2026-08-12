def render(ctx) -> None:
    import streamlit as st

    st.title("User Behaviours & Configuration")
    st.subheader("Behaviour model")
    st.info("Phase 6 will infer periodic, distributional and spontaneous properties without reading synthetic ground truth.")
    st.subheader("Appearance")
    st.write(f"Active theme: **{ctx.theme_name}**")
    st.caption("Edit config/themes/light.yaml and config/themes/dark.yaml to control application and chart design tokens.")
    if ctx.container is not None:
        profile = ctx.container.workspace.read_profile()
        st.json(profile)
