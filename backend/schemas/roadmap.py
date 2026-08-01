from typing import Optional

from pydantic import BaseModel


class RoadmapInitiative(BaseModel):
    initiative: str
    # Everything except the name is Optional: if Claude ever misnames or
    # drops a field (it has, in practice — see backend/ai/roadmap.py),
    # this renders as a blank/missing value instead of a 500 error.
    business_value: Optional[str] = None
    estimated_cost: Optional[str] = None
    complexity: Optional[str] = None
    implementation_effort: Optional[str] = None
    expected_return: Optional[str] = None
    dependencies: Optional[str] = None


class RoadmapResult(BaseModel):
    quick_wins: list[RoadmapInitiative]
    medium_term: list[RoadmapInitiative]
    long_term: list[RoadmapInitiative]
