import unittest
import tempfile
from unittest.mock import patch

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from backend.database.base import Base
from backend.models import Conversation, Message  # noqa: F401 - register ORM models
from backend.repositories import conversation_repository, message_repository
from backend.services import conversation_service, llm_service


class ConversationPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")

        @event.listens_for(self.engine, "connect")
        def enable_foreign_keys(connection, _record):
            connection.execute("PRAGMA foreign_keys=ON")

        Base.metadata.create_all(self.engine)
        self.session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)
        self.db = self.session_factory()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_message_history_is_passed_to_llm_and_persisted(self):
        conversation = conversation_service.create_conversation(self.db, "Test")

        calls = 0

        def reply(history):
            nonlocal calls
            calls += 1
            if calls == 1:
                return "First response"
            self.assertEqual(
                [message.content for message in history],
                ["My name is Youssef", "First response", "What is my name?"],
            )
            return "Hello, Youssef."

        with patch.object(llm_service, "generate_reply", side_effect=reply):
            conversation_service.send_message(self.db, conversation, "My name is Youssef")
            user_message, assistant_message = conversation_service.send_message(
                self.db, conversation, "What is my name?"
            )

        self.assertEqual(user_message.role, "user")
        self.assertEqual(assistant_message.content, "Hello, Youssef.")
        self.assertEqual(
            [message.role for message in message_repository.list_for_conversation(self.db, conversation.id)],
            ["user", "assistant", "user", "assistant"],
        )

    def test_llm_failure_keeps_the_user_message(self):
        conversation = conversation_service.create_conversation(self.db, "Test")
        with patch.object(
            llm_service,
            "generate_reply",
            side_effect=llm_service.LLMProviderError("provider unavailable"),
        ):
            with self.assertRaises(llm_service.LLMProviderError):
                conversation_service.send_message(self.db, conversation, "Keep this message")

        messages = message_repository.list_for_conversation(self.db, conversation.id)
        self.assertEqual([(message.role, message.content) for message in messages], [("user", "Keep this message")])

    def test_deleting_conversation_cascades_to_messages(self):
        conversation = conversation_service.create_conversation(self.db, "Test")
        message_repository.create(self.db, conversation.id, "user", "Delete me")
        self.db.commit()

        conversation_service.delete_conversation(self.db, conversation)

        self.assertIsNone(conversation_repository.get(self.db, conversation.id))
        self.assertEqual(message_repository.list_for_conversation(self.db, conversation.id), [])

    def test_conversation_survives_database_reopen(self):
        with tempfile.TemporaryDirectory() as directory:
            database_engine = create_engine(f"sqlite:///{directory}/persistent.db")
            Base.metadata.create_all(database_engine)
            first_session = sessionmaker(bind=database_engine, expire_on_commit=False)()
            conversation = conversation_service.create_conversation(first_session, "Persistent")
            conversation_id = conversation.id
            first_session.close()
            database_engine.dispose()

            reopened_engine = create_engine(f"sqlite:///{directory}/persistent.db")
            second_session = sessionmaker(bind=reopened_engine, expire_on_commit=False)()
            try:
                saved = conversation_repository.get(second_session, conversation_id)
                self.assertIsNotNone(saved)
                self.assertEqual(saved.title, "Persistent")
            finally:
                second_session.close()
                reopened_engine.dispose()


if __name__ == "__main__":
    unittest.main()
