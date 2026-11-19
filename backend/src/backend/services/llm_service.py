
import logging

from google import genai
from google.genai import types

from backend.core.config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    MAX_TOOL_CALLS_PER_ROUND,
    MAX_TOOL_ITERATIONS,
)
from backend.models.message import Message
from backend.services.tools import (
    TOOL_DECLARATIONS,
    ToolCallValidationError,
    execute_tool,
    prepare_tool_call,
)

logger = logging.getLogger(__name__)

client = genai.Client(
    api_key=GEMINI_API_KEY,
    http_options={"timeout": 120_000},
)


class LLMProviderError(Exception):
    """Raised when the configured language model cannot complete a request."""


def _function_calls(response) -> list:
    """Read function calls across SDK response shapes without requiring response.text."""
    # Prefer the response structure returned by the Gemini SDK.
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

    # Test doubles and some SDK wrappers expose only the convenience property.
    calls = getattr(response, "function_calls", None)
    return list(calls) if calls else []


def _model_call_content(response):
    candidates = getattr(response, "candidates", None) or []
    if not candidates or getattr(candidates[0], "content", None) is None:
        raise LLMProviderError("The AI provider returned an invalid function call.")
    return candidates[0].content


def _generate(contents):
    # Disable automatic execution so the service can validate and run tools itself.
    return client.models.generate_content(
        model=GEMINI_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            tools=TOOL_DECLARATIONS,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        ),
    )


def generate_reply(history: list[Message]) -> str:
    # Convert stored messages to the role and parts format expected by Gemini.
    contents = [
        {
            "role": "model" if message.role == "assistant" else "user",
            "parts": [{"text": message.content}],
        }
        for message in history
    ]

    try:
        for iteration in range(MAX_TOOL_ITERATIONS + 1):
            response = _generate(contents)
            calls = _function_calls(response)

            if not calls:
                if not response.text:
                    raise LLMProviderError("The AI provider returned an empty response.")
                return response.text

            if iteration >= MAX_TOOL_ITERATIONS:
                raise LLMProviderError("The AI provider exceeded the tool iteration limit.")
            if len(calls) > MAX_TOOL_CALLS_PER_ROUND:
                raise LLMProviderError("The AI provider exceeded the tool call limit for one round.")

            # Validate every requested call before executing any call in this batch.
            try:
                prepared_calls = [
                    prepare_tool_call(call.name, call.args)
                    for call in calls
                ]
            except ToolCallValidationError as error:
                logger.warning("Gemini tool call validation failed: %s", type(error).__name__)
                raise LLMProviderError("The AI provider requested an invalid tool call.") from error

            model_call_content = _model_call_content(response)
            function_response_parts = []
            for function_call, prepared_call in zip(calls, prepared_calls, strict=True):
                try:
                    result = execute_tool(prepared_call)
                except Exception as error:
                    logger.warning(
                        "Tool execution failed. Error type: %s",
                        type(error).__name__,
                    )
                    raise LLMProviderError("The requested tool could not be executed.") from error

                # Echo one matching response for each call. Preserve call IDs when
                # supplied so parallel calls with the same name remain correlatable.
                function_response = types.FunctionResponse(
                    name=function_call.name,
                    response={"result": result},
                    id=getattr(function_call, "id", None),
                )
                function_response_parts.append(
                    types.Part(function_response=function_response)
                )

            # Keep the role verified against the configured Gemini API integration.
            tool_response_content = types.Content(
                role="user",
                parts=function_response_parts,
            )
            contents = [*contents, model_call_content, tool_response_content]

        raise LLMProviderError("The AI provider exceeded the tool iteration limit.")

    except LLMProviderError:
        raise

    except Exception as error:
        # Log only the exception class; provider exception strings can contain
        # request details and should not be copied into logs or API responses.
        logger.error("Gemini request failed. Error type: %s", type(error).__name__)
        raise LLMProviderError("The AI provider request failed.") from error
