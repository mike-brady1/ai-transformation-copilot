import pandas as pd
import requests
import streamlit as st

from services.api_client import upload_kpi_csv

st.title("KPI Dashboard")

if "workspace_id" not in st.session_state:
    st.warning("Select or create a workspace on the Home page first.")
    st.stop()

workspace_id = st.session_state["workspace_id"]

uploaded_file = st.file_uploader(
    "Upload machine operational data (CSV)",
    type=["csv"],
    help=(
        "Required columns: machine, planned_production_time_hours, downtime_hours, "
        "units_produced, good_units, ideal_cycle_time_seconds, failure_count, energy_kwh"
    ),
)
if uploaded_file is not None and st.button("Compute KPIs"):
    try:
        results = upload_kpi_csv(workspace_id, uploaded_file.name, uploaded_file.getvalue())
    except requests.exceptions.RequestException as exc:
        st.error(f"Could not compute KPIs — check the CSV has the required columns. ({exc})")
        st.stop()
    st.session_state["kpi_results"] = pd.DataFrame(results)

if "kpi_results" in st.session_state:
    df = st.session_state["kpi_results"]
    st.subheader("Computed KPIs")
    st.dataframe(df)

    st.subheader("OEE by machine")
    st.bar_chart(df.set_index("machine")["oee"])
