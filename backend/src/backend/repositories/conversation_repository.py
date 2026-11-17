from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.conversation import Conversation


def create(db: Session, title: str) -> Conversation:
    conversation = Conversation(title=title)
    db.add(conversation)
    db.flush()
    return conversation


def list_all(db: Session) -> list[Conversation]:
    return list(db.scalars(select(Conversation).order_by(Conversation.updated_at.desc())))


def get(db: Session, conversation_id: str) -> Conversation | None:
    return db.get(Conversation, conversation_id)


def delete(db: Session, conversation: Conversation) -> None:
    db.delete(conversation)
