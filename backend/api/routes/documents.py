from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.document import Document
from backend.models.workspace import Workspace
from backend.rag.chunking import chunk_text
from backend.rag.loaders import load_text
from backend.rag.vector_store import get_chroma_client, get_collection
from backend.schemas.document import DocumentOut

router = APIRouter(prefix="/workspaces/{workspace_id}/documents", tags=["documents"])


@router.post("", response_model=DocumentOut)
async def upload_document(
    workspace_id: int,
    file: UploadFile,
    db: Session = Depends(get_db),
    chroma_client=Depends(get_chroma_client),
):
    workspace = db.get(Workspace, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    raw_bytes = await file.read()
    text = load_text(file.filename, raw_bytes)
    chunks = chunk_text(text)

    # Insert into the relational DB first so we get a real document id —
    # that id is what makes the chunk ids in Chroma unique and traceable
    # back to this exact upload.
    db_document = Document(workspace_id=workspace_id, filename=file.filename, chunk_count=len(chunks))
    db.add(db_document)
    db.commit()
    db.refresh(db_document)

    collection = get_collection(chroma_client, workspace_id)
    collection.add(
        documents=chunks,
        ids=[f"doc{db_document.id}_chunk{i}" for i in range(len(chunks))],
        metadatas=[{"source": file.filename, "document_id": db_document.id} for _ in chunks],
    )

    return db_document


@router.get("", response_model=list[DocumentOut])
def list_documents(workspace_id: int, db: Session = Depends(get_db)):
    return db.query(Document).filter(Document.workspace_id == workspace_id).all()


@router.get("/search")
def search_documents(
    workspace_id: int,
    q: str,
    n_results: int = 3,
    chroma_client=Depends(get_chroma_client),
):
    collection = get_collection(chroma_client, workspace_id)
    results = collection.query(query_texts=[q], n_results=n_results)
    return [
        {"text": doc, "distance": dist, "metadata": meta}
        for doc, dist, meta in zip(
            results["documents"][0], results["distances"][0], results["metadatas"][0]
        )
    ]
