from pydantic import BaseModel, ConfigDict


class DocumentOut(BaseModel):
    id: int
    workspace_id: int
    filename: str
    chunk_count: int

    model_config = ConfigDict(from_attributes=True)
