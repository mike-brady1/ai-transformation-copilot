import streamlit as st

from services.api_client import list_documents, upload_document

st.title("Documents")

if "workspace_id" not in st.session_state:
    st.warning("Select or create a workspace on the Home page first.")
    st.stop()

workspace_id = st.session_state["workspace_id"]

uploaded_file = st.file_uploader("Upload a document", type=["txt", "pdf"])
if uploaded_file is not None and st.button("Upload"):
    doc = upload_document(workspace_id, uploaded_file.name, uploaded_file.getvalue())
    st.success(f"Uploaded {doc['filename']} — {doc['chunk_count']} chunks")
    st.rerun()

st.subheader("Uploaded documents")
documents = list_documents(workspace_id)
if documents:
    for doc in documents:
        st.write(f"**{doc['filename']}** — {doc['chunk_count']} chunks (id={doc['id']})")
else:
    st.caption("No documents uploaded yet.")
