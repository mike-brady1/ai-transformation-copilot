from typing import Optional

from pydantic import BaseModel


class ExecutiveReportRequest(BaseModel):
    # Everything optional and pre-computed — the frontend passes whatever
    # it already has in session state from earlier pages. This endpoint
    # never re-runs SWOT/Roadmap/etc itself.
    swot: Optional[dict] = None
    roadmap: Optional[dict] = None
    maturity: Optional[dict] = None
    technology: Optional[dict] = None
    kpi: Optional[list[dict]] = None


class ExecutiveReportNarrative(BaseModel):
    executive_summary: str
    current_situation: str
    key_findings: list[str]
    financial_impact: str
    next_steps: list[str]
