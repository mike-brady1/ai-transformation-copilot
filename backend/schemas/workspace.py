from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class WorkspaceCreate(BaseModel):
    client_name: str = Field(min_length=1)
    industry: str = Field(min_length=1)
    employees: int = Field(gt=0)
    countries: list[str]
    current_erp: Optional[str] = None
    current_mes: Optional[str] = None


class WorkspaceOut(WorkspaceCreate):
    id: int

    # Lets this schema be built directly from a SQLAlchemy object's
    # attributes (db_workspace.client_name, ...), not just from a dict.
    model_config = ConfigDict(from_attributes=True)
