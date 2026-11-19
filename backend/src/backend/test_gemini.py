
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from google.genai import types

from backend.main import LegacyChatRequest, legacy_chat
from backend.services import llm_service
from backend.services import tools


def text_response(text):
    return SimpleNamespace(text=text, function_calls=[], candidates=[])


def function_response(name="get_current_time", args=None):
    args = {} if args is None else args
    function_call = SimpleNamespace(name=name, args=args)
    call_content = types.Content(
        role="model",
        parts=[types.Part.from_function_call(name=name, args=args)],
    )
    return SimpleNamespace(
        text=None,
        function_calls=[function_call],
        candidates=[SimpleNamespace(content=call_content)],
    )


class GeminiServiceTests(unittest.TestCase):
    def test_direct_text_response_keeps_history_role_mapping(self):
        history = [
            SimpleNamespace(role="user", content="Hi"),
            SimpleNamespace(role="assistant", content="Hello"),
        ]
        response = text_response("How can I help?")

        with patch.object(llm_service.client.models, "generate_content", return_value=response) as generate:
            with patch.object(llm_service, "execute_tool") as execute:
                result = llm_service.generate_reply(history)

        execute.assert_not_called()
        self.assertEqual(result, "How can I help?")
        generate.assert_called_once()
        first_request = generate.call_args.kwargs
        self.assertEqual(first_request["model"], llm_service.GEMINI_MODEL)
        self.assertEqual(first_request["contents"], [
            {"role": "user", "parts": [{"text": "Hi"}]},
            {"role": "model", "parts": [{"text": "Hello"}]},
        ])
        self.assertTrue(first_request["config"].automatic_function_calling.disable)
        self.assertEqual(first_request["config"].tools, tools.TOOL_DECLARATIONS)

    def test_time_tool_returns_explicit_utc_without_reading_real_clock(self):
        fixed_time = datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
        with patch.object(tools, "datetime") as datetime_mock:
            datetime_mock.now.return_value = fixed_time
            result = tools.get_current_time()

        self.assertEqual(result, {"timestamp": "2025-01-02T03:04:05Z", "timezone": "UTC"})

    def test_successful_time_call_is_sent_back_to_gemini(self):
        call_response = function_response()
        final_response = text_response("It is 2025-01-02T03:04:05Z (UTC).")
        deterministic_time = {"timestamp": "2025-01-02T03:04:05Z", "timezone": "UTC"}
        history = [SimpleNamespace(role="user", content="What time is it?")]

        with patch.object(
            llm_service.client.models,
            "generate_content",
            side_effect=[call_response, final_response],
        ) as generate:
            with patch.object(llm_service, "execute_tool", return_value=deterministic_time) as execute:
                result = llm_service.generate_reply(history)

        execute.assert_called_once_with("get_current_time", {})
        self.assertEqual(result, final_response.text)
        self.assertEqual(generate.call_count, 2)
        second_contents = generate.call_args_list[1].kwargs["contents"]
        self.assertEqual(len(second_contents), 3)
        self.assertIs(second_contents[1], call_response.candidates[0].content)
        function_response_part = second_contents[2].parts[0].function_response
        self.assertEqual(function_response_part.name, "get_current_time")
        self.assertEqual(function_response_part.response, {"result": deterministic_time})

    def test_unknown_tool_name_is_rejected(self):
        with patch.object(
            llm_service.client.models,
            "generate_content",
            return_value=function_response(name="run_shell"),
        ) as generate:
            with patch.dict(tools.TOOL_REGISTRY, {"get_current_time": unittest.mock.Mock()}):
                with self.assertRaises(llm_service.LLMProviderError):
                    llm_service.generate_reply([SimpleNamespace(role="user", content="run something")])

        self.assertEqual(generate.call_count, 1)

    def test_unexpected_tool_arguments_are_rejected(self):
        with patch.object(
            llm_service.client.models,
            "generate_content",
            return_value=function_response(args={"command": "unsafe"}),
        ) as generate:
            with patch.dict(tools.TOOL_REGISTRY, {"get_current_time": unittest.mock.Mock()}):
                with self.assertRaises(llm_service.LLMProviderError):
                    llm_service.generate_reply([SimpleNamespace(role="user", content="get time")])

        self.assertEqual(generate.call_count, 1)

    def test_multiple_function_calls_are_rejected(self):
        response = function_response()
        response.function_calls.append(SimpleNamespace(name="get_current_time", args={}))
        response.candidates[0].content = types.Content(
            role="model",
            parts=[
                types.Part.from_function_call(name="get_current_time", args={}),
                types.Part.from_function_call(name="get_current_time", args={}),
            ],
        )
        with patch.object(llm_service.client.models, "generate_content", return_value=response):
            with patch.object(llm_service, "execute_tool") as execute:
                with self.assertRaises(llm_service.LLMProviderError):
                    llm_service.generate_reply([SimpleNamespace(role="user", content="get time")])

        execute.assert_not_called()

    def test_follow_up_provider_failure_is_wrapped(self):
        with patch.object(
            llm_service.client.models,
            "generate_content",
            side_effect=[function_response(), RuntimeError("provider unavailable")],
        ):
            with patch.object(llm_service, "execute_tool", return_value={"timezone": "UTC"}):
                with self.assertRaises(llm_service.LLMProviderError):
                    llm_service.generate_reply([SimpleNamespace(role="user", content="get time")])

    def test_follow_up_tool_request_is_rejected_without_a_second_execution(self):
        with patch.object(
            llm_service.client.models,
            "generate_content",
            side_effect=[function_response(), function_response()],
        ) as generate:
            with patch.object(llm_service, "execute_tool", return_value={"timezone": "UTC"}) as execute:
                with self.assertRaises(llm_service.LLMProviderError):
                    llm_service.generate_reply([SimpleNamespace(role="user", content="get time")])

        self.assertEqual(generate.call_count, 2)
        execute.assert_called_once_with("get_current_time", {})

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
