from typing import Optional

from pydantic import BaseModel, ConfigDict


class WorkspaceCreate(BaseModel):
    client_name: str
    industry: str
    employees: int
    countries: list[str]
    current_erp: Optional[str] = None
    current_mes: Optional[str] = None


class WorkspaceOut(WorkspaceCreate):
    id: int

    # Lets this schema be built directly from a SQLAlchemy object's
    # attributes (db_workspace.client_name, ...), not just from a dict.
    model_config = ConfigDict(from_attributes=True)
