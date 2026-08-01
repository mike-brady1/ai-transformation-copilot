import requests
import streamlit as st

from services.api_client import generate_sustainability_report

st.title("Sustainability Analyzer")

if "workspace_id" not in st.session_state:
    st.warning("Select or create a workspace on the Home page first.")
    st.stop()

workspace_id = st.session_state["workspace_id"]

uploaded_file = st.file_uploader(
    "Upload machine operational data (CSV)",
    type=["csv"],
    help="Same format as the KPI Dashboard — this reuses that data's energy_kwh and units_produced columns.",
)
if uploaded_file is not None and st.button("Analyze Sustainability"):
    try:
        with st.spinner("Estimating emissions and generating recommendations..."):
            result = generate_sustainability_report(
                workspace_id, uploaded_file.name, uploaded_file.getvalue()
            )
    except requests.exceptions.RequestException as exc:
        st.error(f"Could not generate the analysis — check the CSV has the required columns. ({exc})")
        st.stop()
    st.session_state["sustainability_result"] = result

if "sustainability_result" in st.session_state:
    result = st.session_state["sustainability_result"]

    cols = st.columns(3)
    cols[0].metric("Energy Intensity", f"{result['energy_intensity_kwh_per_unit']} kWh/unit")
    cols[1].metric("Est. CO2 Emissions", f"{result['estimated_co2_emissions_kg']:,.0f} kg")
    cols[2].metric("Total Energy", f"{result['total_energy_kwh']:,.0f} kWh")
    st.caption(
        f"Assumed emissions factor: {result['emissions_factor_kg_co2_per_kwh']} kg CO2/kWh — "
        f"{result['emissions_factor_assumption']}"
    )

    st.subheader("Waste")
    st.write(result["waste_assessment"])

    st.subheader("Transportation")
    st.write(result["transportation_assessment"])

    st.subheader("Improvement Opportunities")
    impact_color = {"High": "green", "Medium": "orange", "Low": "gray"}
    for opp in result["opportunities"]:
        color = impact_color.get(opp.get("estimated_impact"), "gray")
        st.markdown(f"**{opp['initiative']}**  :{color}[{opp.get('estimated_impact') or 'Unknown'} impact]")
        st.caption(opp.get("description") or "")
