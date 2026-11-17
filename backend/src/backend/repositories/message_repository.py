from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.message import Message


def create(db: Session, conversation_id: str, role: str, content: str) -> Message:
    message = Message(conversation_id=conversation_id, role=role, content=content)
    db.add(message)
    db.flush()
    return message


def list_for_conversation(db: Session, conversation_id: str) -> list[Message]:
    statement = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at, Message.id)
    )
    return list(db.scalars(statement))
