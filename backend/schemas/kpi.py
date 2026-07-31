from pydantic import BaseModel


class KPIResult(BaseModel):
    machine: str
    availability: float
    performance: float
    quality: float
    oee: float
    mtbf_hours: float
    mttr_hours: float
    energy_per_unit_kwh: float
    scrap_rate: float
