import requests
import streamlit as st

from services.api_client import analyze_document, list_documents

st.title("Interview Analyzer")

if "workspace_id" not in st.session_state:
    st.warning("Select or create a workspace on the Home page first.")
    st.stop()

workspace_id = st.session_state["workspace_id"]
documents = list_documents(workspace_id)

if not documents:
    st.caption("Upload a document on the Documents page first.")
    st.stop()

options = {f"{d['filename']} (id={d['id']})": d["id"] for d in documents}
selected_label = st.selectbox("Choose a document to analyze", list(options.keys()))

if st.button("Analyze"):
    try:
        with st.spinner("Analyzing with Claude..."):
            findings = analyze_document(workspace_id, options[selected_label])
    except requests.exceptions.RequestException:
        st.error(
            "Analysis failed. Check that the backend is running and "
            "ANTHROPIC_API_KEY is set in its .env file."
        )
        st.stop()
    # Persisted so other pages (e.g. the PowerPoint export's Pain Points
    # slide) can reuse it, and so it survives navigating away and back —
    # same pattern as swot_result/roadmap_result/etc, missed here since
    # this page predates that convention.
    st.session_state["interview_findings"] = findings

if "interview_findings" in st.session_state:
    findings = st.session_state["interview_findings"]
    if not findings:
        st.info("No pain points found.")

    severity_color = {"High": "red", "Medium": "orange", "Low": "green"}
    for finding in findings:
        color = severity_color.get(finding["severity"], "gray")
        st.markdown(f"### {finding['pain_point']}  :{color}[{finding['severity']}]")
        st.write(f"**Business impact:** {finding['business_impact']}")
        st.write(f"**Recommendation:** {finding['recommendation']}")
        st.divider()
