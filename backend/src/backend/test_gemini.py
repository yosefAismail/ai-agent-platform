
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch

from google.genai import types

from backend.main import LegacyChatRequest, legacy_chat
from backend.services import llm_service
from backend.services import tools


def text_response(text):
    return SimpleNamespace(text=text, function_calls=[], candidates=[])


def function_response(*calls):
    calls = calls or (("get_current_time", {}, "call-1"),)
    function_calls = [
        SimpleNamespace(name=name, args=args, id=call_id)
        for name, args, call_id in calls
    ]
    call_content = types.Content(
        role="model",
        parts=[
            types.Part(
                function_call=types.FunctionCall(name=name, args=args, id=call_id)
            )
            for name, args, call_id in calls
        ],
    )
    return SimpleNamespace(
        text=None,
        function_calls=function_calls,
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
        call_response = function_response(("get_current_time", {}, "time-1"))
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

        execute.assert_called_once()
        self.assertEqual(execute.call_args.args[0].name, "get_current_time")
        self.assertEqual(result, final_response.text)
        self.assertEqual(generate.call_count, 2)
        second_contents = generate.call_args_list[1].kwargs["contents"]
        self.assertEqual(len(second_contents), 3)
        self.assertIs(second_contents[1], call_response.candidates[0].content)
        self.assertEqual(second_contents[2].role, "user")
        function_response_part = second_contents[2].parts[0].function_response
        self.assertEqual(function_response_part.name, "get_current_time")
        self.assertEqual(function_response_part.response, {"result": deterministic_time})
        self.assertEqual(function_response_part.id, "time-1")

    def test_unknown_tool_name_is_rejected(self):
        with patch.object(
            llm_service.client.models,
            "generate_content",
            return_value=function_response(("run_shell", {}, "bad-1")),
        ) as generate:
            with patch.object(llm_service, "execute_tool") as execute:
                with self.assertRaises(llm_service.LLMProviderError):
                    llm_service.generate_reply([SimpleNamespace(role="user", content="run something")])

        execute.assert_not_called()
        self.assertEqual(generate.call_count, 1)

    def test_unexpected_tool_arguments_are_rejected(self):
        with patch.object(
            llm_service.client.models,
            "generate_content",
            return_value=function_response(("get_current_time", {"command": "unsafe"}, "bad-2")),
        ) as generate:
            with patch.object(llm_service, "execute_tool") as execute:
                with self.assertRaises(llm_service.LLMProviderError):
                    llm_service.generate_reply([SimpleNamespace(role="user", content="get time")])

        execute.assert_not_called()
        self.assertEqual(generate.call_count, 1)

    def test_multiple_function_calls_in_one_round_get_matching_responses(self):
        response = function_response(
            ("get_current_time", {}, "time-1"),
            ("get_current_time", {}, "time-2"),
        )
        final_response = text_response("Here are both timestamps.")
        with patch.object(
            llm_service.client.models,
            "generate_content",
            side_effect=[response, final_response],
        ) as generate:
            with patch.object(
                llm_service,
                "execute_tool",
                side_effect=[{"timestamp": "t1", "timezone": "UTC"}, {"timestamp": "t2", "timezone": "UTC"}],
            ) as execute:
                result = llm_service.generate_reply([SimpleNamespace(role="user", content="compare times")])

        self.assertEqual(result, final_response.text)
        self.assertEqual(execute.call_count, 2)
        returned_parts = generate.call_args_list[1].kwargs["contents"][2].parts
        self.assertEqual(len(returned_parts), 2)
        self.assertEqual([part.function_response.id for part in returned_parts], ["time-1", "time-2"])
        self.assertEqual([part.function_response.name for part in returned_parts], ["get_current_time"] * 2)
        self.assertEqual(
            [part.function_response.response["result"]["timestamp"] for part in returned_parts],
            ["t1", "t2"],
        )

    def test_sequential_tool_rounds_continue_until_final_text(self):
        responses = [
            function_response(("calculate", {"expression": "2+2"}, "calc-1")),
            function_response(("convert_temperature", {"value": 20, "from_unit": "C", "to_unit": "F"}, "temp-1")),
            text_response("The calculation is 4 and 20 C is 68 F."),
        ]
        with patch.object(llm_service, "MAX_TOOL_ITERATIONS", 2):
            with patch.object(llm_service.client.models, "generate_content", side_effect=responses) as generate:
                with patch.object(llm_service, "execute_tool", side_effect=[{"result": 4}, {"result": 68}]) as execute:
                    result = llm_service.generate_reply([SimpleNamespace(role="user", content="calculate and convert")])

        self.assertEqual(result, responses[-1].text)
        self.assertEqual(generate.call_count, 3)
        self.assertEqual(execute.call_count, 2)
        third_contents = generate.call_args_list[2].kwargs["contents"]
        self.assertEqual([content.role for content in third_contents if isinstance(content, types.Content)], ["model", "user", "model", "user"])

    def test_iteration_limit_allows_final_text_after_last_permitted_round(self):
        responses = [
            function_response(("get_current_time", {}, "time-1")),
            text_response("Final answer"),
        ]
        with patch.object(llm_service, "MAX_TOOL_ITERATIONS", 1):
            with patch.object(llm_service.client.models, "generate_content", side_effect=responses):
                with patch.object(llm_service, "execute_tool", return_value={"timezone": "UTC"}):
                    self.assertEqual(
                        llm_service.generate_reply([SimpleNamespace(role="user", content="time?")]),
                        "Final answer",
                    )

    def test_iteration_limit_exhaustion_is_safe(self):
        with patch.object(llm_service, "MAX_TOOL_ITERATIONS", 1):
            with patch.object(
                llm_service.client.models,
                "generate_content",
                side_effect=[
                    function_response(("get_current_time", {}, "time-1")),
                    function_response(("get_current_time", {}, "time-2")),
                ],
            ) as generate:
                with patch.object(llm_service, "execute_tool", return_value={"timezone": "UTC"}) as execute:
                    with self.assertRaisesRegex(llm_service.LLMProviderError, "iteration limit"):
                        llm_service.generate_reply([SimpleNamespace(role="user", content="time?")])

        self.assertEqual(generate.call_count, 2)
        execute.assert_called_once()

    def test_call_count_limit_rejects_whole_batch_before_execution(self):
        response = function_response(
            ("get_current_time", {}, "time-1"),
            ("get_current_time", {}, "time-2"),
        )
        with patch.object(llm_service, "MAX_TOOL_CALLS_PER_ROUND", 1):
            with patch.object(llm_service.client.models, "generate_content", return_value=response):
                with patch.object(llm_service, "execute_tool") as execute:
                    with self.assertRaisesRegex(llm_service.LLMProviderError, "tool call limit"):
                        llm_service.generate_reply([SimpleNamespace(role="user", content="time?")])

        execute.assert_not_called()

    def test_invalid_tool_inputs_and_expression_operations_are_rejected(self):
        invalid_calls = [
            ("calculate", {"expression": "x + 1"}),
            ("calculate", {"expression": "1 ** 100"}),
            ("calculate", {"expression": "1 / 0"}),
            ("calculate", {"expression": "1 + " + "1" * 130}),
            ("convert_units", {"value": 1, "from_unit": "yard", "to_unit": "m"}),
            ("convert_temperature", {"value": -274, "from_unit": "C", "to_unit": "K"}),
            ("count_words", {"text": "x" * 5_001}),
        ]
        for name, arguments in invalid_calls:
            with self.subTest(name=name, arguments=arguments):
                with self.assertRaises(tools.ToolCallValidationError):
                    tools.prepare_tool_call(name, arguments)

    def test_valid_utility_tools_return_structured_results(self):
        calculate_call = tools.prepare_tool_call("calculate", {"expression": "(2 + 3) * 4"})
        length_call = tools.prepare_tool_call(
            "convert_units", {"value": 1, "from_unit": "mi", "to_unit": "km"}
        )
        temperature_call = tools.prepare_tool_call(
            "convert_temperature", {"value": 0, "from_unit": "C", "to_unit": "K"}
        )
        words_call = tools.prepare_tool_call("count_words", {"text": "hello agent world"})

        self.assertEqual(tools.execute_tool(calculate_call)["result"], 20)
        self.assertAlmostEqual(tools.execute_tool(length_call)["result"], 1.609344)
        self.assertAlmostEqual(tools.execute_tool(temperature_call)["result"], 273.15)
        self.assertEqual(tools.execute_tool(words_call), {"word_count": 3, "character_count": 17})

    def test_tool_declarations_match_registry(self):
        registered = set(tools.TOOL_REGISTRY)
        declared = {
            declaration.name
            for tool in tools.TOOL_DECLARATIONS
            for declaration in tool.function_declarations
        }
        self.assertEqual(registered, declared)

    def test_follow_up_provider_failure_is_wrapped(self):
        with patch.object(
            llm_service.client.models,
            "generate_content",
            side_effect=[function_response(), RuntimeError("provider unavailable")],
        ):
            with patch.object(llm_service, "execute_tool", return_value={"timezone": "UTC"}):
                with self.assertRaises(llm_service.LLMProviderError):
                    llm_service.generate_reply([SimpleNamespace(role="user", content="get time")])

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
