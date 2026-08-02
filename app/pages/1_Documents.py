import requests
import streamlit as st

from services.api_client import delete_document, error_detail, list_documents, upload_document

st.title("Documents")

if "workspace_id" not in st.session_state:
    st.warning("Select or create a workspace on the Home page first.")
    st.stop()

workspace_id = st.session_state["workspace_id"]

uploaded_file = st.file_uploader("Upload a document", type=["txt", "pdf"])
if uploaded_file is not None and st.button("Upload"):
    try:
        doc = upload_document(workspace_id, uploaded_file.name, uploaded_file.getvalue())
    except requests.exceptions.RequestException as exc:
        st.error(f"Upload failed: {error_detail(exc)}")
        st.stop()
    st.success(f"Uploaded {doc['filename']} — {doc['chunk_count']} chunks")
    st.rerun()

st.subheader("Uploaded documents")
documents = list_documents(workspace_id)
if documents:
    for doc in documents:
        col1, col2 = st.columns([5, 1])
        with col1:
            st.write(f"**{doc['filename']}** — {doc['chunk_count']} chunks (id={doc['id']})")
        with col2:
            if st.button("Delete", key=f"delete_{doc['id']}"):
                try:
                    delete_document(workspace_id, doc["id"])
                except requests.exceptions.RequestException as exc:
                    st.error(f"Could not delete: {error_detail(exc)}")
                    st.stop()
                st.rerun()
else:
    st.caption("No documents uploaded yet.")
