from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.ai.client import get_anthropic_client
from backend.ai.executive_report import format_findings_as_text, generate_executive_narrative
from backend.database import get_db
from backend.models.workspace import Workspace
from backend.schemas.executive_report import ExecutiveReportNarrative, ExecutiveReportRequest

router = APIRouter(prefix="/workspaces/{workspace_id}/executive-report", tags=["executive-report"])


@router.post("/narrative", response_model=ExecutiveReportNarrative)
def generate_narrative(
    workspace_id: int,
    payload: ExecutiveReportRequest,
    db: Session = Depends(get_db),
    anthropic_client=Depends(get_anthropic_client),
):
    workspace = db.get(Workspace, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    if not any([payload.swot, payload.roadmap, payload.maturity, payload.technology, payload.kpi]):
        raise HTTPException(
            status_code=400, detail="No findings provided — generate at least one analysis first"
        )

    findings_text = format_findings_as_text(
        workspace.client_name,
        workspace.industry,
        payload.swot,
        payload.roadmap,
        payload.maturity,
        payload.technology,
        payload.kpi,
    )
    narrative = generate_executive_narrative(anthropic_client, findings_text)

    return ExecutiveReportNarrative(
        executive_summary=narrative.get("executive_summary") or "",
        current_situation=narrative.get("current_situation") or "",
        key_findings=narrative.get("key_findings") or [],
        financial_impact=narrative.get("financial_impact") or "",
        next_steps=narrative.get("next_steps") or [],
    )
