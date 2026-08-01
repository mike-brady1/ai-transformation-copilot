import pandas as pd
import requests
import streamlit as st

from services.api_client import generate_technology_recommendations

st.title("Technology Recommendations")

if "workspace_id" not in st.session_state:
    st.warning("Select or create a workspace on the Home page first.")
    st.stop()

workspace_id = st.session_state["workspace_id"]

if st.button("Generate Recommendations"):
    try:
        with st.spinner("Mapping weaknesses to technology recommendations..."):
            result = generate_technology_recommendations(workspace_id)
    except requests.exceptions.RequestException as exc:
        st.error(f"Could not generate recommendations — make sure documents are uploaded first. ({exc})")
        st.stop()
    st.session_state["technology_result"] = result

if "technology_result" in st.session_state:
    recommendations = st.session_state["technology_result"]["recommendations"]
    if not recommendations:
        st.info("No weaknesses identified to recommend technology for yet.")
    else:
        df = pd.DataFrame(recommendations).rename(
            columns={
                "problem": "Problem",
                "recommendation": "Recommendation",
                "technology": "Technology",
                "platform": "Platform",
                "expected_return": "Expected ROI",
            }
        )
        st.dataframe(df, use_container_width=True)
