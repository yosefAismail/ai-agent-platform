
import logging

from google import genai

from backend.core.config import GEMINI_API_KEY, GEMINI_MODEL
from backend.models.message import Message

logger = logging.getLogger(__name__)

client = genai.Client(
    api_key=GEMINI_API_KEY,
    http_options={"timeout": 120_000},
)


class LLMProviderError(Exception):
    """Raised when the configured language model cannot complete a request."""


def generate_reply(history: list[Message]) -> str:
    contents = [
        {
            "role": "model" if message.role == "assistant" else "user",
            "parts": [{"text": message.content}],
        }
        for message in history
    ]

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=contents,
        )

        if not response.text:
            raise LLMProviderError("The AI provider returned an empty response.")

        return response.text

    except LLMProviderError:
        raise

    except Exception as error:
        logger.exception(
            "Gemini request failed. Error type: %s",
            type(error).__name__,
        )
        raise LLMProviderError("The AI provider request failed.") from error
