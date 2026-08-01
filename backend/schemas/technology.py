from typing import Optional

from pydantic import BaseModel


class TechnologyRecommendation(BaseModel):
    problem: str
    recommendation: Optional[str] = None
    technology: Optional[str] = None
    platform: Optional[str] = None
    expected_return: Optional[str] = None


class TechnologyRecommendationsResult(BaseModel):
    recommendations: list[TechnologyRecommendation]
