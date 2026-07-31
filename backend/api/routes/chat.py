from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.ai.chat import answer_question
from backend.ai.client import get_anthropic_client
from backend.database import get_db
from backend.models.workspace import Workspace
from backend.rag.vector_store import get_chroma_client, get_collection
from backend.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/workspaces/{workspace_id}/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(
    workspace_id: int,
    payload: ChatRequest,
    db: Session = Depends(get_db),
    chroma_client=Depends(get_chroma_client),
    anthropic_client=Depends(get_anthropic_client),
):
    workspace = db.get(Workspace, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    collection = get_collection(chroma_client, workspace_id)
    messages = [m.model_dump() for m in payload.messages]
    answer, sources = answer_question(anthropic_client, collection, messages)

    return ChatResponse(answer=answer, sources=sources)
