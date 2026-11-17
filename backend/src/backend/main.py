from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.api.routes.conversations import router as conversations_router
from backend.core.config import CORS_ORIGINS
from backend.database.base import Base
from backend.database.connection import engine
from backend.models import Conversation, Message  # noqa: F401 - register ORM models
from backend.services import llm_service

Base.metadata.create_all(bind=engine)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(conversations_router)


class LegacyChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class LegacyChatRequest(BaseModel):
    messages: list[LegacyChatMessage]


@app.get("/")
def read_root():
    return {"message": "Hello from my first AI agent!"}


@app.post("/chat")
def legacy_chat(request: LegacyChatRequest):
    # Preserve the existing frontend contract while new clients use persisted
    # conversations through /conversations/{id}/messages.
    history = [
        Message(role=message.role, content=message.content)
        for message in request.messages
    ]
    try:
        return {"response": llm_service.generate_reply(history)}
    except llm_service.LLMProviderError:
        raise HTTPException(status_code=502, detail="AI provider request failed") from None


def main() -> None:
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000)
