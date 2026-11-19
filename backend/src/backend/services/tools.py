from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any, Callable

from google.genai import types


def get_current_time() -> dict[str, str]:
    """Return the current time as an ISO 8601 UTC timestamp with an explicit UTC label."""
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    return {"timestamp": timestamp, "timezone": "UTC"}


GET_CURRENT_TIME_DECLARATION = types.FunctionDeclaration(
    name="get_current_time",
    description=(
        "Get the current time. The result is an ISO 8601 timestamp in UTC, "
        "with the timezone explicitly labeled UTC. This function takes no arguments."
    ),
)

TOOL_DECLARATIONS = [
    types.Tool(function_declarations=[GET_CURRENT_TIME_DECLARATION]),
]

TOOL_REGISTRY: dict[str, Callable[[], dict[str, str]]] = {
    "get_current_time": get_current_time,
}


class ToolCallValidationError(ValueError):
    """Raised when a model-requested tool call is not on the explicit allowlist."""


def execute_tool(name: str, arguments: Any) -> dict[str, str]:
    """Validate and execute one registered tool call."""
    if not isinstance(name, str):
        raise ToolCallValidationError("Function name must be a string")
    function = TOOL_REGISTRY.get(name)
    if function is None:
        raise ToolCallValidationError("Unknown function requested")

    if not isinstance(arguments, Mapping):
        raise ToolCallValidationError("Function arguments must be an object")
    if arguments:
        raise ToolCallValidationError("This function does not accept arguments")

    return function()
