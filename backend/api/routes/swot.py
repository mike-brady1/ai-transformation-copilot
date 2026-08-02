from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.ai.client import get_anthropic_client
from backend.ai.swot import generate_swot
from backend.database import get_db
from backend.models.workspace import Workspace
from backend.rag.vector_store import get_chroma_client, get_full_workspace_context
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

    context = get_full_workspace_context(chroma_client, db, workspace_id)
    if context is None:
        raise HTTPException(status_code=400, detail="No documents uploaded for this workspace yet")

    return generate_swot(anthropic_client, context)
