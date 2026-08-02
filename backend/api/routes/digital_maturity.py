from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.ai.client import get_anthropic_client
from backend.ai.digital_maturity import MATURITY_CATEGORIES, generate_digital_maturity
from backend.database import get_db
from backend.models.workspace import Workspace
from backend.rag.vector_store import get_chroma_client, get_full_workspace_context
from backend.schemas.digital_maturity import DigitalMaturityResult

router = APIRouter(prefix="/workspaces/{workspace_id}/maturity", tags=["digital-maturity"])


@router.post("", response_model=DigitalMaturityResult)
def generate_maturity_assessment(
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

    maturity = generate_digital_maturity(anthropic_client, context)

    # Normalize defensively: a missing category, a missing score, or a
    # score outside 1-5 all fall back to 3 (neutral/uncertain) — the same
    # convention Claude itself uses for "insufficient evidence", so a
    # malformed response degrades the same way a genuinely unassessed
    # dimension would, rather than 500ing the whole request.
    scores = []
    normalized = {}
    for category in MATURITY_CATEGORIES:
        entry = maturity.get(category) or {}
        score = entry.get("score")
        if not isinstance(score, int) or not (1 <= score <= 5):
            score = 3
        justification = entry.get("justification") or "Not assessed."
        normalized[category] = {"score": score, "justification": justification}
        scores.append(score)

    overall = round(sum(scores) / len(scores), 1)
    return DigitalMaturityResult(**normalized, overall=overall)
