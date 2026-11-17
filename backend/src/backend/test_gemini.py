
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from backend.main import LegacyChatRequest, legacy_chat
from backend.services import llm_service


class GeminiServiceTests(unittest.TestCase):
    def test_history_roles_are_mapped_for_gemini(self):
        history = [
            SimpleNamespace(role="user", content="Hi"),
            SimpleNamespace(role="assistant", content="Hello"),
        ]
        response = SimpleNamespace(text="How can I help?")

        with patch.object(llm_service.client.models, "generate_content", return_value=response) as generate:
            result = llm_service.generate_reply(history)

        self.assertEqual(result, "How can I help?")
        generate.assert_called_once_with(
            model=llm_service.GEMINI_MODEL,
            contents=[
                {"role": "user", "parts": [{"text": "Hi"}]},
                {"role": "model", "parts": [{"text": "Hello"}]},
            ],
        )

    def test_provider_failure_does_not_expose_details(self):
        history = [SimpleNamespace(role="user", content="Hi")]
        with patch.object(
            llm_service.client.models,
            "generate_content",
            side_effect=RuntimeError("sensitive provider detail"),
        ):
            with self.assertRaises(llm_service.LLMProviderError) as error:
                llm_service.generate_reply(history)

        self.assertNotIn("sensitive provider detail", str(error.exception))

    def test_legacy_chat_contract_is_preserved(self):
        request = LegacyChatRequest(
            messages=[
                {"role": "user", "content": "Hi"},
                {"role": "assistant", "content": "Hello"},
                {"role": "user", "content": "Continue"},
            ]
        )
        with patch.object(llm_service, "generate_reply", return_value="Still here") as generate:
            result = legacy_chat(request)

        self.assertEqual(result, {"response": "Still here"})
        history = generate.call_args.args[0]
        self.assertEqual([message.content for message in history], ["Hi", "Hello", "Continue"])


if __name__ == "__main__":
    unittest.main()
