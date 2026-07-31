import io

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.kpi.calculations import compute_kpis
from backend.models.workspace import Workspace
from backend.schemas.kpi import KPIResult

router = APIRouter(prefix="/workspaces/{workspace_id}/kpi", tags=["kpi"])

OUTPUT_COLUMNS = [
    "machine",
    "availability",
    "performance",
    "quality",
    "oee",
    "mtbf_hours",
    "mttr_hours",
    "energy_per_unit_kwh",
    "scrap_rate",
]


@router.post("", response_model=list[KPIResult])
async def upload_kpi_data(workspace_id: int, file: UploadFile, db: Session = Depends(get_db)):
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

    return result_df[OUTPUT_COLUMNS].to_dict(orient="records")
