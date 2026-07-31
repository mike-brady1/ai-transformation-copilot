import requests
import streamlit as st

from services.api_client import generate_swot

st.title("SWOT Generator")

if "workspace_id" not in st.session_state:
    st.warning("Select or create a workspace on the Home page first.")
    st.stop()

workspace_id = st.session_state["workspace_id"]

if st.button("Generate SWOT"):
    try:
        with st.spinner("Analyzing all documents with Claude..."):
            swot = generate_swot(workspace_id)
    except requests.exceptions.RequestException as exc:
        st.error(f"Could not generate SWOT — make sure documents are uploaded first. ({exc})")
        st.stop()
    st.session_state["swot_result"] = swot


def render_quadrant(title: str, color: str, items: list[dict]) -> None:
    st.subheader(f":{color}[{title}]")
    if not items:
        st.caption("None identified.")
    for entry in items:
        st.markdown(f"**{entry['item']}**")
        st.caption(entry["explanation"])


if "swot_result" in st.session_state:
    swot = st.session_state["swot_result"]

    top_left, top_right = st.columns(2)
    with top_left:
        render_quadrant("Strengths", "green", swot["strengths"])
    with top_right:
        render_quadrant("Weaknesses", "red", swot["weaknesses"])

    bottom_left, bottom_right = st.columns(2)
    with bottom_left:
        render_quadrant("Opportunities", "orange", swot["opportunities"])
    with bottom_right:
        render_quadrant("Threats", "violet", swot["threats"])
