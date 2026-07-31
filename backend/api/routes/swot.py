from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.ai.client import get_anthropic_client
from backend.ai.swot import generate_swot
from backend.database import get_db
from backend.models.workspace import Workspace
from backend.rag.vector_store import get_chroma_client, get_collection
from backend.schemas.swot import SWOTResult

router = APIRouter(prefix="/workspaces/{workspace_id}/swot", tags=["swot"])


@router.post("", response_model=SWOTResult)
def generate_swot_analysis(
    workspace_id: int,
    db: Session = Depends(get_db),
    chroma_client=Depends(get_chroma_client),
    anthropic_client=Depends(get_anthropic_client),
):
    workspace = db.get(Workspace, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # No query, no filter — every chunk from every document in this
    # workspace. A SWOT needs the whole picture, not the top few matches
    # for a specific question like Chat's retrieval does.
    collection = get_collection(chroma_client, workspace_id)
    result = collection.get()
    if not result["documents"]:
        raise HTTPException(status_code=400, detail="No documents uploaded for this workspace yet")

    ordered = sorted(
        zip(result["metadatas"], result["documents"]),
        key=lambda pair: (pair[0].get("document_id", 0), pair[0].get("chunk_index", 0)),
    )
    context = "\n\n---\n\n".join(f"[Source: {meta.get('source')}]\n{doc}" for meta, doc in ordered)

    return generate_swot(anthropic_client, context)
