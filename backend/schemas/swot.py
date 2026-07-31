from pydantic import BaseModel


class SWOTItem(BaseModel):
    item: str
    explanation: str


class SWOTResult(BaseModel):
    strengths: list[SWOTItem]
    weaknesses: list[SWOTItem]
    opportunities: list[SWOTItem]
    threats: list[SWOTItem]
