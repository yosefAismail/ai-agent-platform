import ast
import math
import operator
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Literal

from google.genai import types
from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, ValidationError, field_validator, model_validator


class ToolArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CurrentTimeArguments(ToolArguments):
    pass


_BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPERATORS = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_MAX_EXPRESSION_LENGTH = 120
_MAX_AST_NODES = 25
_MAX_AST_DEPTH = 8
_MAX_CALCULATION_VALUE = 1_000_000_000_000
_MAX_EXPONENT = 10


def _evaluate_arithmetic(expression: str) -> int | float:
    if len(expression) > _MAX_EXPRESSION_LENGTH:
        raise ValueError("Expression is too long")
    try:
        root = ast.parse(expression, mode="eval")
    except SyntaxError as error:
        raise ValueError("Expression is not valid arithmetic") from error

    nodes_seen = 0

    def visit(node: ast.AST, depth: int = 0) -> int | float:
        nonlocal nodes_seen
        nodes_seen += 1
        if nodes_seen > _MAX_AST_NODES or depth > _MAX_AST_DEPTH:
            raise ValueError("Expression is too complex")

        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            value = node.value
            if abs(value) > _MAX_CALCULATION_VALUE:
                raise ValueError("Numeric value is outside the supported range")
            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError("Numeric value is outside the supported range")
            return value

        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPERATORS:
            return _UNARY_OPERATORS[type(node.op)](visit(node.operand, depth + 1))

        if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPERATORS:
            left = visit(node.left, depth + 1)
            right = visit(node.right, depth + 1)
            if isinstance(node.op, ast.Pow) and abs(right) > _MAX_EXPONENT:
                raise ValueError("Exponent is outside the supported range")
            try:
                result = _BINARY_OPERATORS[type(node.op)](left, right)
            except (ArithmeticError, TypeError) as error:
                raise ValueError("Arithmetic operation is not valid") from error
            if isinstance(result, complex) or not math.isfinite(result):
                raise ValueError("Calculation result is not a finite real number")
            if abs(result) > _MAX_CALCULATION_VALUE:
                raise ValueError("Calculation result is outside the supported range")
            return result

        raise ValueError("Expression contains an unsupported operation")

    return visit(root.body)


class CalculateArguments(ToolArguments):
    expression: str = Field(min_length=1, max_length=_MAX_EXPRESSION_LENGTH)

    @field_validator("expression")
    @classmethod
    def validate_supported_arithmetic(cls, expression: str) -> str:
        _evaluate_arithmetic(expression)
        return expression


class ConvertUnitsArguments(ToolArguments):
    value: FiniteFloat = Field(ge=-1_000_000_000_000, le=1_000_000_000_000)
    from_unit: Literal["mm", "cm", "m", "km", "in", "ft", "mi"]
    to_unit: Literal["mm", "cm", "m", "km", "in", "ft", "mi"]


class ConvertTemperatureArguments(ToolArguments):
    value: FiniteFloat = Field(ge=-1_000_000_000, le=1_000_000_000)
    from_unit: Literal["C", "F", "K"]
    to_unit: Literal["C", "F", "K"]

    @model_validator(mode="after")
    def not_below_absolute_zero(self):
        kelvin = {
            "C": self.value + 273.15,
            "F": (self.value - 32) * (5 / 9) + 273.15,
            "K": self.value,
        }[self.from_unit]
        if kelvin < -1e-9:
            raise ValueError("Temperature is below absolute zero")
        return self


class CountWordsArguments(ToolArguments):
    text: str = Field(max_length=5_000)


def get_current_time() -> dict[str, str]:
    """Return the current time as an ISO 8601 UTC timestamp with an explicit UTC label."""
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    return {"timestamp": timestamp, "timezone": "UTC"}


def calculate(expression: str) -> dict[str, int | float | str]:
    """Safely calculate a bounded arithmetic expression."""
    return {"expression": expression, "result": _evaluate_arithmetic(expression)}


_LENGTH_IN_METERS = {
    "mm": 0.001,
    "cm": 0.01,
    "m": 1.0,
    "km": 1_000.0,
    "in": 0.0254,
    "ft": 0.3048,
    "mi": 1_609.344,
}


def convert_units(value: float, from_unit: str, to_unit: str) -> dict[str, Any]:
    """Convert a length between supported metric and imperial units."""
    converted = value * _LENGTH_IN_METERS[from_unit] / _LENGTH_IN_METERS[to_unit]
    return {"value": value, "from_unit": from_unit, "to_unit": to_unit, "result": converted}


def convert_temperature(value: float, from_unit: str, to_unit: str) -> dict[str, Any]:
    """Convert a temperature between Celsius, Fahrenheit, and Kelvin."""
    kelvin = {
        "C": value + 273.15,
        "F": (value - 32) * (5 / 9) + 273.15,
        "K": value,
    }[from_unit]
    converted = {
        "C": kelvin - 273.15,
        "F": (kelvin - 273.15) * (9 / 5) + 32,
        "K": kelvin,
    }[to_unit]
    return {"value": value, "from_unit": from_unit, "to_unit": to_unit, "result": converted}


def count_words(text: str) -> dict[str, int]:
    """Count whitespace-separated words and characters in text."""
    return {"word_count": len(text.split()), "character_count": len(text)}


@dataclass(frozen=True)
class ToolSpec:
    arguments_model: type[ToolArguments]
    function: Callable[..., Any]
    declaration: types.FunctionDeclaration


def _tool_spec(
    name: str,
    description: str,
    arguments_model: type[ToolArguments],
    function: Callable[..., Any],
) -> ToolSpec:
    return ToolSpec(
        arguments_model=arguments_model,
        function=function,
        declaration=types.FunctionDeclaration(
            name=name,
            description=description,
            parameters_json_schema=arguments_model.model_json_schema(),
        ),
    )


TOOL_REGISTRY: dict[str, ToolSpec] = {
    "get_current_time": _tool_spec(
        "get_current_time",
        "Get the current time as an ISO 8601 UTC timestamp. Takes no arguments.",
        CurrentTimeArguments,
        get_current_time,
    ),
    "calculate": _tool_spec(
        "calculate",
        "Safely calculate a short arithmetic expression using numbers and +, -, *, /, //, %, and **.",
        CalculateArguments,
        calculate,
    ),
    "convert_units": _tool_spec(
        "convert_units",
        "Convert a numeric length between mm, cm, m, km, in, ft, and mi.",
        ConvertUnitsArguments,
        convert_units,
    ),
    "convert_temperature": _tool_spec(
        "convert_temperature",
        "Convert a temperature between C, F, and K; temperatures below absolute zero are invalid.",
        ConvertTemperatureArguments,
        convert_temperature,
    ),
    "count_words": _tool_spec(
        "count_words",
        "Count whitespace-separated words and characters in text up to 5000 characters.",
        CountWordsArguments,
        count_words,
    ),
}

TOOL_DECLARATIONS = [
    types.Tool(function_declarations=[spec.declaration for spec in TOOL_REGISTRY.values()])
]


class ToolCallValidationError(ValueError):
    """Raised when a model-requested tool call is unknown or has invalid arguments."""


@dataclass(frozen=True)
class PreparedToolCall:
    name: str
    spec: ToolSpec
    arguments: ToolArguments


def prepare_tool_call(name: str, arguments: Any) -> PreparedToolCall:
    """Validate a call without executing it, so a whole parallel batch can be checked first."""
    if not isinstance(name, str):
        raise ToolCallValidationError("Function name must be a string")
    spec = TOOL_REGISTRY.get(name)
    if spec is None:
        raise ToolCallValidationError("Unknown function requested")

    if arguments is None and not spec.arguments_model.model_fields:
        arguments = {}
    if not isinstance(arguments, Mapping):
        raise ToolCallValidationError("Function arguments must be an object")

    try:
        validated_arguments = spec.arguments_model.model_validate(arguments)
    except ValidationError as error:
        raise ToolCallValidationError("Function arguments are invalid") from error
    except ValueError as error:
        raise ToolCallValidationError("Function arguments are invalid") from error

    return PreparedToolCall(name=name, spec=spec, arguments=validated_arguments)


def execute_tool(call: PreparedToolCall) -> Any:
    """Execute a previously validated, allowlisted call."""
    return call.spec.function(**call.arguments.model_dump())
