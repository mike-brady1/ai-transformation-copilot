from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.ai.client import get_anthropic_client
from backend.ai.swot import format_weaknesses_as_text, generate_swot
from backend.ai.technology import generate_technology_recommendations
from backend.database import get_db
from backend.models.workspace import Workspace
from backend.rag.vector_store import get_chroma_client, get_full_workspace_context
from backend.schemas.technology import TechnologyRecommendationsResult

router = APIRouter(prefix="/workspaces/{workspace_id}/technology-recommendations", tags=["technology"])


@router.post("", response_model=TechnologyRecommendationsResult)
def generate_technology_recommendations_for_workspace(
    workspace_id: int,
    db: Session = Depends(get_db),
    chroma_client=Depends(get_chroma_client),
    anthropic_client=Depends(get_anthropic_client),
):
    workspace = db.get(Workspace, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    context = get_full_workspace_context(chroma_client, workspace_id)
    if context is None:
        raise HTTPException(status_code=400, detail="No documents uploaded for this workspace yet")

    swot = generate_swot(anthropic_client, context)
    problems_text = format_weaknesses_as_text(swot)
    if not problems_text.strip():
        # No weaknesses identified means nothing to recommend technology
        # for — return empty rather than spending a second Claude call
        # on nothing.
        return TechnologyRecommendationsResult(recommendations=[])

    return generate_technology_recommendations(anthropic_client, problems_text)
