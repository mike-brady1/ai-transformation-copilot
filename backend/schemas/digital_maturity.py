from pydantic import BaseModel


class MaturityDimension(BaseModel):
    score: int
    justification: str


class DigitalMaturityResult(BaseModel):
    leadership: MaturityDimension
    operations: MaturityDimension
    technology: MaturityDimension
    data: MaturityDimension
    supply_chain: MaturityDimension
    automation: MaturityDimension
    sustainability: MaturityDimension
    cybersecurity: MaturityDimension
    workforce: MaturityDimension
    # Computed by our own code from the 9 scores above, never asked of
    # Claude — same reasoning as the KPI Dashboard: arithmetic is exact
    # in code and approximate from an LLM, so code does the math.
    overall: float
