from pydantic import BaseModel


class PainPoint(BaseModel):
    pain_point: str
    severity: str
    business_impact: str
    recommendation: str
