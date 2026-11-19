
import logging

from google import genai
from google.genai import types

from backend.core.config import GEMINI_API_KEY, GEMINI_MODEL
from backend.models.message import Message
from backend.services.tools import TOOL_DECLARATIONS, ToolCallValidationError, execute_tool

logger = logging.getLogger(__name__)

client = genai.Client(
    api_key=GEMINI_API_KEY,
    http_options={"timeout": 120_000},
)


class LLMProviderError(Exception):
    """Raised when the configured language model cannot complete a request."""


def _function_calls(response) -> list:
    """Read function calls across SDK response shapes without requiring response.text."""
    candidates = getattr(response, "candidates", None) or []
    if candidates:
        content = getattr(candidates[0], "content", None)
        found = [
            part.function_call
            for part in (getattr(content, "parts", None) or [])
            if getattr(part, "function_call", None) is not None
        ]
        if found:
            return found

    # Some response doubles or SDK wrappers expose the convenience property only.
    calls = getattr(response, "function_calls", None)
    return list(calls) if calls else []


def _model_call_content(response):
    candidates = getattr(response, "candidates", None) or []
    if not candidates or getattr(candidates[0], "content", None) is None:
        raise LLMProviderError("The AI provider returned an invalid function call.")
    return candidates[0].content


def _generate(contents):
    return client.models.generate_content(
        model=GEMINI_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            tools=TOOL_DECLARATIONS,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        ),
    )


def generate_reply(history: list[Message]) -> str:
    contents = [
        {
            "role": "model" if message.role == "assistant" else "user",
            "parts": [{"text": message.content}],
        }
        for message in history
    ]

    try:
        response = _generate(contents)

        calls = _function_calls(response)
        if not calls:
            if not response.text:
                raise LLMProviderError("The AI provider returned an empty response.")
            return response.text

        if len(calls) != 1:
            raise LLMProviderError("The AI provider requested an unsupported number of tools.")

        function_call = calls[0]
        try:
            tool_result = execute_tool(function_call.name, function_call.args)
        except ToolCallValidationError as error:
            raise LLMProviderError("The AI provider requested an invalid tool call.") from error

        model_call_content = _model_call_content(response)
        tool_response_content = types.Content(
            role="tool",
            parts=[
                types.Part.from_function_response(
                    name=function_call.name,
                    response={"result": tool_result},
                )
            ],
        )

        follow_up_response = _generate(
            [*contents, model_call_content, tool_response_content]
        )

        if _function_calls(follow_up_response):
            raise LLMProviderError("The AI provider requested more than one tool round.")

        if not follow_up_response.text:
            raise LLMProviderError("The AI provider returned an empty response.")

        return follow_up_response.text

    except LLMProviderError:
        raise

    except ToolCallValidationError as error:
        logger.warning("Gemini tool call validation failed: %s", type(error).__name__)
        raise LLMProviderError("The AI provider requested an invalid tool call.") from error

    except Exception as error:
        logger.exception(
            "Gemini request failed. Error type: %s",
            type(error).__name__,
        )
        raise LLMProviderError("The AI provider request failed.") from error
