from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.ai.client import get_anthropic_client
from backend.ai.interview_analysis import analyze_transcript
from backend.database import get_db
from backend.models.document import Document
from backend.models.workspace import Workspace
from backend.rag.chunking import chunk_text
from backend.rag.loaders import load_text
from backend.rag.vector_store import get_chroma_client, get_collection, reindex_workspace_documents
from backend.schemas.document import DocumentOut
from backend.schemas.interview import PainPoint

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
    db_document = Document(
        workspace_id=workspace_id, filename=file.filename, chunk_count=len(chunks), content=text
    )
    db.add(db_document)
    db.commit()
    db.refresh(db_document)

    collection = get_collection(chroma_client, workspace_id)
    collection.add(
        documents=chunks,
        ids=[f"doc{db_document.id}_chunk{i}" for i in range(len(chunks))],
        metadatas=[
            {"source": file.filename, "document_id": db_document.id, "chunk_index": i}
            for i in range(len(chunks))
        ],
    )

    return db_document


@router.get("", response_model=list[DocumentOut])
def list_documents(workspace_id: int, db: Session = Depends(get_db)):
    return db.query(Document).filter(Document.workspace_id == workspace_id).all()


@router.post("/{document_id}/analyze", response_model=list[PainPoint])
def analyze_document(
    workspace_id: int,
    document_id: int,
    db: Session = Depends(get_db),
    chroma_client=Depends(get_chroma_client),
    anthropic_client=Depends(get_anthropic_client),
):
    document = db.get(Document, document_id)
    if document is None or document.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Document not found")

    reindex_workspace_documents(chroma_client, db, workspace_id)

    # .get() with a metadata filter — different from .query(): this is an
    # exact lookup ("give me every chunk from this document"), not a
    # similarity search. Order isn't guaranteed, so we sort by the
    # chunk_index we stored at upload time to rebuild the original text.
    collection = get_collection(chroma_client, workspace_id)
    result = collection.get(where={"document_id": document_id})
    if not result["documents"]:
        # The Document row (Postgres) can outlive its chunks (Chroma) —
        # e.g. a hosting environment with an ephemeral disk that resets
        # on redeploy while the database persists. Fail clearly instead
        # of sending an empty message to Claude, which raised an
        # unhandled exception (500) rather than a useful error.
        raise HTTPException(
            status_code=404,
            detail="No content found for this document — it may need to be re-uploaded.",
        )

    ordered = sorted(
        zip(result["metadatas"], result["documents"]),
        key=lambda pair: pair[0]["chunk_index"],
    )
    full_text = "\n\n".join(text for _, text in ordered)

    findings = analyze_transcript(anthropic_client, full_text)
    return findings


@router.get("/search")
def search_documents(
    workspace_id: int,
    q: str,
    n_results: int = 3,
    db: Session = Depends(get_db),
    chroma_client=Depends(get_chroma_client),
):
    reindex_workspace_documents(chroma_client, db, workspace_id)
    collection = get_collection(chroma_client, workspace_id)
    results = collection.query(query_texts=[q], n_results=n_results)
    return [
        {"text": doc, "distance": dist, "metadata": meta}
        for doc, dist, meta in zip(
            results["documents"][0], results["distances"][0], results["metadatas"][0]
        )
    ]
