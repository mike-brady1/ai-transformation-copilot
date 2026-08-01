import requests
import streamlit as st

from services.api_client import generate_roadmap

st.title("Transformation Roadmap")

if "workspace_id" not in st.session_state:
    st.warning("Select or create a workspace on the Home page first.")
    st.stop()

workspace_id = st.session_state["workspace_id"]

if st.button("Generate Roadmap"):
    try:
        with st.spinner("Building a SWOT, then a roadmap from it..."):
            roadmap = generate_roadmap(workspace_id)
    except requests.exceptions.RequestException as exc:
        st.error(f"Could not generate a roadmap — make sure documents are uploaded first. ({exc})")
        st.stop()
    st.session_state["roadmap_result"] = roadmap


def render_horizon(title: str, items: list[dict]) -> None:
    st.subheader(title)
    if not items:
        st.caption("No initiatives identified for this horizon.")
    for entry in items:
        with st.container(border=True):
            st.markdown(f"**{entry['initiative']}**")
            st.caption(entry.get("business_value") or "")
            cols = st.columns(3)
            cols[0].metric("Cost", entry.get("estimated_cost") or "—")
            cols[1].metric("Complexity", entry.get("complexity") or "—")
            cols[2].metric("Expected ROI", entry.get("expected_return") or "—")
            dependencies = entry.get("dependencies")
            if dependencies and dependencies.lower() != "none":
                st.caption(f"Depends on: {dependencies}")


if "roadmap_result" in st.session_state:
    roadmap = st.session_state["roadmap_result"]
    render_horizon("Quick Wins (0–3 months)", roadmap["quick_wins"])
    render_horizon("Medium-Term (3–12 months)", roadmap["medium_term"])
    render_horizon("Long-Term (12–36 months)", roadmap["long_term"])
