import requests
import streamlit as st

from services.api_client import send_chat_message

st.title("AI Consulting Chat")

if "workspace_id" not in st.session_state:
    st.warning("Select or create a workspace on the Home page first.")
    st.stop()

workspace_id = st.session_state["workspace_id"]

if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

for message in st.session_state["chat_history"]:
    with st.chat_message(message["role"]):
        st.write(message["content"])

question = st.chat_input("Ask about this engagement...")
if question:
    st.session_state["chat_history"].append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.write(question)

    with st.chat_message("assistant"):
        try:
            with st.spinner("Thinking..."):
                result = send_chat_message(workspace_id, st.session_state["chat_history"])
        except requests.exceptions.RequestException:
            st.error(
                "Couldn't reach the AI service. Check that the backend is running "
                "and ANTHROPIC_API_KEY is set in its .env file."
            )
            # Drop the question we already added above so a retry doesn't duplicate it.
            st.session_state["chat_history"].pop()
            st.stop()

        st.write(result["answer"])
        if result["sources"]:
            st.caption(f"Sources: {', '.join(set(result['sources']))}")

    st.session_state["chat_history"].append({"role": "assistant", "content": result["answer"]})
