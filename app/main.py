import streamlit as st

from services.api_client import create_workspace, list_workspaces

st.set_page_config(page_title="AI Transformation Copilot", page_icon="\U0001F4CA")
st.title("AI Transformation Copilot")
st.caption("Select or create a client engagement to get started.")

workspaces = list_workspaces()

if workspaces:
    st.subheader("Existing engagements")
    options = {f"{w['client_name']} ({w['industry']}) — id={w['id']}": w["id"] for w in workspaces}
    selected_label = st.selectbox("Choose a workspace", list(options.keys()))
    if st.button("Use this workspace"):
        st.session_state["workspace_id"] = options[selected_label]
        st.success(f"Active workspace set to {selected_label}. Use the sidebar to navigate.")

st.divider()
st.subheader("New engagement")
with st.form("new_workspace"):
    client_name = st.text_input("Client name")
    industry = st.text_input("Industry")
    employees = st.number_input("Employees", min_value=1, step=1)
    countries = st.text_input("Countries (comma-separated)")
    current_erp = st.text_input("Current ERP (optional)")
    submitted = st.form_submit_button("Create workspace")

    if submitted:
        payload = {
            "client_name": client_name,
            "industry": industry,
            "employees": int(employees),
            "countries": [c.strip() for c in countries.split(",") if c.strip()],
            "current_erp": current_erp or None,
        }
        new_ws = create_workspace(payload)
        st.session_state["workspace_id"] = new_ws["id"]
        st.success(f"Created workspace for {new_ws['client_name']} (id={new_ws['id']})")
        st.rerun()

if "workspace_id" in st.session_state:
    st.info(f"Active workspace id: {st.session_state['workspace_id']}")
else:
    st.warning("No active workspace yet — create or select one above.")
