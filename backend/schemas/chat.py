from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    # Full conversation so far, ending with the new user question — the
    # caller (eventually Streamlit) owns this state, the backend doesn't.
    messages: list[ChatMessage]


class ChatResponse(BaseModel):
    answer: str
    sources: list[str]
