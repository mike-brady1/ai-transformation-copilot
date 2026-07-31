from fastapi import FastAPI

from backend.api.routes.chat import router as chat_router
from backend.api.routes.documents import router as documents_router
from backend.api.routes.workspaces import router as workspaces_router
from backend.database import Base, engine

Base.metadata.create_all(engine)

app = FastAPI(title="AI Transformation Copilot")
app.include_router(workspaces_router)
app.include_router(documents_router)
app.include_router(chat_router)


@app.get("/health")
def health():
    return {"status": "ok"}
