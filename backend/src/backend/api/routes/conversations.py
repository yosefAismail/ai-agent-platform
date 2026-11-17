from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.schemas.conversation import ConversationCreate, ConversationDetail, ConversationRead
from backend.schemas.message import MessageCreate, MessageRead, SendMessageResponse
from backend.services import conversation_service, llm_service

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("", response_model=ConversationRead, status_code=status.HTTP_201_CREATED)
def create_conversation(payload: ConversationCreate, db: Session = Depends(get_db)):
    return conversation_service.create_conversation(db, payload.title)


@router.get("", response_model=list[ConversationRead])
def list_conversations(db: Session = Depends(get_db)):
    return conversation_service.list_conversations(db)


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(conversation_id: str, db: Session = Depends(get_db)):
    conversation = conversation_service.get_conversation(db, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.get("/{conversation_id}/messages", response_model=list[MessageRead])
def get_messages(conversation_id: str, db: Session = Depends(get_db)):
    if conversation_service.get_conversation(db, conversation_id) is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation_service.get_messages(db, conversation_id)


@router.post(
    "/{conversation_id}/messages",
    response_model=SendMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def send_message(conversation_id: str, payload: MessageCreate, db: Session = Depends(get_db)):
    conversation = conversation_service.get_conversation(db, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    try:
        user_message, assistant_message = conversation_service.send_message(
            db, conversation, payload.content
        )
    except llm_service.LLMProviderError:
        db.rollback()
        raise HTTPException(status_code=502, detail="AI provider request failed") from None
    return SendMessageResponse(
        user_message=user_message,
        assistant_message=assistant_message,
        response=assistant_message.content,
    )


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(conversation_id: str, db: Session = Depends(get_db)):
    conversation = conversation_service.get_conversation(db, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    conversation_service.delete_conversation(db, conversation)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
