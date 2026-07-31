from fastapi import FastAPI

from backend.api.routes.workspaces import router as workspaces_router
from backend.database import Base, engine

Base.metadata.create_all(engine)

app = FastAPI(title="AI Transformation Copilot")
app.include_router(workspaces_router)


@app.get("/health")
def health():
    return {"status": "ok"}
