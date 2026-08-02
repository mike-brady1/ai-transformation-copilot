import io

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.ai.client import get_anthropic_client
from backend.ai.sustainability import DEFAULT_EMISSIONS_FACTOR, generate_sustainability_analysis
from backend.database import get_db
from backend.kpi.calculations import compute_kpis
from backend.models.workspace import Workspace
from backend.rag.vector_store import get_chroma_client, get_full_workspace_context
from backend.schemas.sustainability import SustainabilityResult

router = APIRouter(prefix="/workspaces/{workspace_id}/sustainability", tags=["sustainability"])


@router.post("", response_model=SustainabilityResult)
async def generate_sustainability_report(
    workspace_id: int,
    file: UploadFile,
    db: Session = Depends(get_db),
    chroma_client=Depends(get_chroma_client),
    anthropic_client=Depends(get_anthropic_client),
):
    workspace = db.get(Workspace, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    raw_bytes = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(raw_bytes))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Could not parse the CSV file") from exc

    try:
        result_df = compute_kpis(df)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    total_energy_kwh = float(result_df["energy_kwh"].sum())
    total_units_produced = float(result_df["units_produced"].sum())

    # Documents are optional here (unlike SWOT/Roadmap/Maturity) — the
    # energy math is meaningful on its own from the CSV alone; document
    # context just enriches the waste/transportation assessment if present.
    document_context = get_full_workspace_context(chroma_client, db, workspace_id)
    if document_context is None:
        document_context = "No supporting documents uploaded for this workspace."

    analysis = generate_sustainability_analysis(
        anthropic_client, total_energy_kwh, total_units_produced, document_context
    )

    factor = analysis.get("emissions_factor_kg_co2_per_kwh")
    factor_assumption = analysis.get("emissions_factor_assumption")
    if not isinstance(factor, (int, float)) or factor <= 0:
        factor = DEFAULT_EMISSIONS_FACTOR
        factor_assumption = (
            f"Claude did not provide a usable factor; defaulted to a global "
            f"average grid intensity of {DEFAULT_EMISSIONS_FACTOR} kg CO2/kWh."
        )

    return SustainabilityResult(
        total_energy_kwh=total_energy_kwh,
        total_units_produced=total_units_produced,
        energy_intensity_kwh_per_unit=round(total_energy_kwh / total_units_produced, 4),
        estimated_co2_emissions_kg=round(total_energy_kwh * factor, 1),
        emissions_factor_kg_co2_per_kwh=factor,
        emissions_factor_assumption=factor_assumption or "Not provided.",
        waste_assessment=analysis.get("waste_assessment") or "Not assessed.",
        transportation_assessment=analysis.get("transportation_assessment") or "Not assessed.",
        opportunities=analysis.get("opportunities") or [],
    )
