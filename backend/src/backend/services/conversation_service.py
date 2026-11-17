from sqlalchemy.orm import Session

from backend.models.conversation import Conversation
from backend.models.message import Message
from backend.repositories import conversation_repository, message_repository
from backend.services import llm_service


def create_conversation(db: Session, title: str) -> Conversation:
    conversation = conversation_repository.create(db, title)
    db.commit()
    db.refresh(conversation)
    return conversation


def list_conversations(db: Session) -> list[Conversation]:
    return conversation_repository.list_all(db)


def get_conversation(db: Session, conversation_id: str) -> Conversation | None:
    return conversation_repository.get(db, conversation_id)


def get_messages(db: Session, conversation_id: str) -> list[Message]:
    return message_repository.list_for_conversation(db, conversation_id)


def delete_conversation(db: Session, conversation: Conversation) -> None:
    conversation_repository.delete(db, conversation)
    db.commit()


def send_message(db: Session, conversation: Conversation, content: str) -> tuple[Message, Message]:
    user_message = message_repository.create(db, conversation.id, "user", content)
    conversation.updated_at = user_message.created_at
    db.commit()
    db.refresh(user_message)

    history = message_repository.list_for_conversation(db, conversation.id)
    assistant_content = llm_service.generate_reply(history)

    assistant_message = message_repository.create(
        db, conversation.id, "assistant", assistant_content
    )
    db.commit()
    db.refresh(assistant_message)
    db.refresh(conversation)
    return user_message, assistant_message
