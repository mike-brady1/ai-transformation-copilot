import pandas as pd
import requests
import streamlit as st

from services.api_client import generate_digital_maturity

st.title("Digital Maturity Assessment")

if "workspace_id" not in st.session_state:
    st.warning("Select or create a workspace on the Home page first.")
    st.stop()

workspace_id = st.session_state["workspace_id"]

if st.button("Generate Assessment"):
    try:
        with st.spinner("Assessing digital maturity with Claude..."):
            maturity = generate_digital_maturity(workspace_id)
    except requests.exceptions.RequestException as exc:
        st.error(f"Could not generate assessment — make sure documents are uploaded first. ({exc})")
        st.stop()
    st.session_state["maturity_result"] = maturity

if "maturity_result" in st.session_state:
    maturity = st.session_state["maturity_result"]
    categories = [
        "leadership",
        "operations",
        "technology",
        "data",
        "supply_chain",
        "automation",
        "sustainability",
        "cybersecurity",
        "workforce",
    ]

    st.metric("Overall", f"{maturity['overall']} / 5")

    chart_df = pd.DataFrame(
        {
            "dimension": [c.replace("_", " ").title() for c in categories],
            "score": [maturity[c]["score"] for c in categories],
        }
    ).set_index("dimension")
    st.bar_chart(chart_df)

    for category in categories:
        entry = maturity[category]
        stars = "★" * entry["score"] + "☆" * (5 - entry["score"])
        st.markdown(f"**{category.replace('_', ' ').title()}** — {stars}")
        st.caption(entry["justification"])
