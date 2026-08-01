from typing import Optional

from pydantic import BaseModel


class SustainabilityOpportunity(BaseModel):
    initiative: str
    description: Optional[str] = None
    estimated_impact: Optional[str] = None


class SustainabilityResult(BaseModel):
    total_energy_kwh: float
    total_units_produced: float
    # These two are always well-formed — computed by our own arithmetic,
    # never taken directly from Claude's response.
    energy_intensity_kwh_per_unit: float
    estimated_co2_emissions_kg: float
    emissions_factor_kg_co2_per_kwh: float
    emissions_factor_assumption: str
    waste_assessment: str
    transportation_assessment: str
    opportunities: list[SustainabilityOpportunity]
