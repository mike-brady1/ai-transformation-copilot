from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.ai.client import get_anthropic_client
from backend.ai.roadmap import generate_roadmap
from backend.ai.swot import format_swot_as_text, generate_swot
from backend.database import get_db
from backend.models.workspace import Workspace
from backend.rag.vector_store import get_chroma_client, get_collection
from backend.schemas.roadmap import RoadmapResult

router = APIRouter(prefix="/workspaces/{workspace_id}/roadmap", tags=["roadmap"])


@router.post("", response_model=RoadmapResult)
def generate_roadmap_for_workspace(
    workspace_id: int,
    db: Session = Depends(get_db),
    chroma_client=Depends(get_chroma_client),
    anthropic_client=Depends(get_anthropic_client),
):
    workspace = db.get(Workspace, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    collection = get_collection(chroma_client, workspace_id)
    result = collection.get()
    if not result["documents"]:
        raise HTTPException(status_code=400, detail="No documents uploaded for this workspace yet")

    ordered = sorted(
        zip(result["metadatas"], result["documents"]),
        key=lambda pair: (pair[0].get("document_id", 0), pair[0].get("chunk_index", 0)),
    )
    context = "\n\n---\n\n".join(f"[Source: {meta.get('source')}]\n{doc}" for meta, doc in ordered)

    # Step 1: distill raw documents into a SWOT (reuses Module 7's logic).
    swot = generate_swot(anthropic_client, context)
    # Step 2: build the roadmap FROM the SWOT, not from raw documents
    # again — this is the actual "pipeline": one Claude call's structured
    # output becomes the next call's input.
    swot_text = format_swot_as_text(swot)
    return generate_roadmap(anthropic_client, swot_text)
