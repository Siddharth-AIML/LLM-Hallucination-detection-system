"""Bounded execution of schema-validated mathematical expression trees."""

import ast
import re
from dataclasses import dataclass
from fractions import Fraction
from typing import Optional

import sympy

from .models import ExpressionNode


_NUMBER = re.compile(r"-?(?:\d+(?:\.\d+)?|\d+/\d+)\Z")
_MAX_VALUE_BITS = 850
_UNIT_ALIASES = {
    "m": ("length", Fraction(1), "m"),
    "meter": ("length", Fraction(1), "m"),
    "meters": ("length", Fraction(1), "m"),
    "metre": ("length", Fraction(1), "m"),
    "metres": ("length", Fraction(1), "m"),
    "cm": ("length", Fraction(1, 100), "m"),
    "centimeter": ("length", Fraction(1, 100), "m"),
    "centimeters": ("length", Fraction(1, 100), "m"),
    "mm": ("length", Fraction(1, 1000), "m"),
    "millimeter": ("length", Fraction(1, 1000), "m"),
    "millimeters": ("length", Fraction(1, 1000), "m"),
    "millimetre": ("length", Fraction(1, 1000), "m"),
    "millimetres": ("length", Fraction(1, 1000), "m"),
    "km": ("length", Fraction(1000), "m"),
    "kilometer": ("length", Fraction(1000), "m"),
    "kilometers": ("length", Fraction(1000), "m"),
    "ft": ("length", Fraction(381, 1250), "m"),
    "foot": ("length", Fraction(381, 1250), "m"),
    "feet": ("length", Fraction(381, 1250), "m"),
    "in": ("length", Fraction(127, 5000), "m"),
    "inch": ("length", Fraction(127, 5000), "m"),
    "inches": ("length", Fraction(127, 5000), "m"),
    "mile": ("length", Fraction(201168, 125), "m"),
    "miles": ("length", Fraction(201168, 125), "m"),
    "g": ("mass", Fraction(1, 1000), "kg"),
    "gram": ("mass", Fraction(1, 1000), "kg"),
    "grams": ("mass", Fraction(1, 1000), "kg"),
    "kg": ("mass", Fraction(1), "kg"),
    "kilogram": ("mass", Fraction(1), "kg"),
    "kilograms": ("mass", Fraction(1), "kg"),
    "lb": ("mass", Fraction(45359237, 100000000), "kg"),
    "lbs": ("mass", Fraction(45359237, 100000000), "kg"),
    "pound": ("mass", Fraction(45359237, 100000000), "kg"),
    "pounds": ("mass", Fraction(45359237, 100000000), "kg"),
    "s": ("time", Fraction(1), "s"),
    "sec": ("time", Fraction(1), "s"),
    "second": ("time", Fraction(1), "s"),
    "seconds": ("time", Fraction(1), "s"),
    "min": ("time", Fraction(60), "s"),
    "minute": ("time", Fraction(60), "s"),
    "minutes": ("time", Fraction(60), "s"),
    "h": ("time", Fraction(3600), "s"),
    "hr": ("time", Fraction(3600), "s"),
    "hour": ("time", Fraction(3600), "s"),
    "hours": ("time", Fraction(3600), "s"),
    "day": ("time", Fraction(86400), "s"),
    "days": ("time", Fraction(86400), "s"),
    "ml": ("volume", Fraction(1, 1000), "L"),
    "milliliter": ("volume", Fraction(1, 1000), "L"),
    "milliliters": ("volume", Fraction(1, 1000), "L"),
    "l": ("volume", Fraction(1), "L"),
    "liter": ("volume", Fraction(1), "L"),
    "liters": ("volume", Fraction(1), "L"),
    "$": ("currency:USD", Fraction(1), "USD"),
    "usd": ("currency:USD", Fraction(1), "USD"),
    "dollar": ("currency:USD", Fraction(1), "USD"),
    "dollars": ("currency:USD", Fraction(1), "USD"),
    "usd$": ("currency:USD", Fraction(1), "USD"),
    "eur": ("currency:EUR", Fraction(1), "EUR"),
    "€": ("currency:EUR", Fraction(1), "EUR"),
    "euro": ("currency:EUR", Fraction(1), "EUR"),
    "euros": ("currency:EUR", Fraction(1), "EUR"),
    "gbp": ("currency:GBP", Fraction(1), "GBP"),
    "£": ("currency:GBP", Fraction(1), "GBP"),
    "percent": ("dimensionless", Fraction(1, 100), ""),
    "%": ("dimensionless", Fraction(1, 100), ""),
    "apple": ("count:apple", Fraction(1), "apple"),
    "apples": ("count:apple", Fraction(1), "apple"),
    "chocolate": ("count:chocolate", Fraction(1), "chocolate"),
    "chocolates": ("count:chocolate", Fraction(1), "chocolate"),
    "cookie": ("count:cookie", Fraction(1), "cookie"),
    "cookies": ("count:cookie", Fraction(1), "cookie"),
    "box": ("count:box", Fraction(1), "box"),
    "boxes": ("count:box", Fraction(1), "box"),
    "bag": ("count:bag", Fraction(1), "bag"),
    "bags": ("count:bag", Fraction(1), "bag"),
    "person": ("count:person", Fraction(1), "person"),
    "people": ("count:person", Fraction(1), "person"),
    "friend": ("count:person", Fraction(1), "person"),
    "friends": ("count:person", Fraction(1), "person"),
    "student": ("count:student", Fraction(1), "student"),
    "students": ("count:student", Fraction(1), "student"),
    "item": ("count:item", Fraction(1), "item"),
    "items": ("count:item", Fraction(1), "item"),
    "": ("dimensionless", Fraction(1), ""),
}
_BASE_UNITS = {
    "length": "m",
    "mass": "kg",
    "time": "s",
    "volume": "L",
    "currency:USD": "USD",
    "currency:EUR": "EUR",
    "currency:GBP": "GBP",
    "dimensionless": "",
    "count:apple": "apple",
    "count:chocolate": "chocolate",
    "count:cookie": "cookie",
    "count:box": "box",
    "count:bag": "bag",
    "count:person": "person",
    "count:student": "student",
    "count:item": "item",
}


class UnsupportedExpression(ValueError):
    """Raised when an expression cannot be safely evaluated."""


@dataclass(frozen=True)
class EvaluatedQuantity:
    value: sympy.Expr
    dimension: str
    display_unit: str


def _number(value: str) -> Fraction:
    if len(value) > 128 or not _NUMBER.fullmatch(value):
        raise UnsupportedExpression("Malformed or oversized numeric literal.")
    if "/" in value:
        numerator, denominator = value.split("/", 1)
        if int(denominator) == 0:
            raise UnsupportedExpression("Division by zero in numeric literal.")
        return Fraction(int(numerator), int(denominator))
    return Fraction(value)


def _to_sympy(value: Fraction) -> sympy.Rational:
    return sympy.Rational(value.numerator, value.denominator)


def _unit(unit: Optional[str]):
    normalized = (unit or "").strip().casefold()
    try:
        return _UNIT_ALIASES[normalized]
    except KeyError as error:
        raise UnsupportedExpression(
            f"Unsupported unit {unit!r}; no conversion was guessed."
        ) from error


def unit_info(unit: Optional[str]):
    """Return a canonical dimension, scale-to-base, and base unit."""
    return _unit(unit)


def _tree_size(node: ExpressionNode, depth: int = 0) -> int:
    if depth > 8:
        raise UnsupportedExpression("Expression tree is too deeply nested.")
    return 1 + sum(_tree_size(child, depth + 1) for child in node.operands)


def _bound_quantity(quantity: EvaluatedQuantity) -> EvaluatedQuantity:
    value = quantity.value
    if not value.is_Rational:
        raise UnsupportedExpression(
            "Only exact rational intermediate values are supported."
        )
    if (
        int(value.p).bit_length() > _MAX_VALUE_BITS
        or int(value.q).bit_length() > _MAX_VALUE_BITS
    ):
        raise UnsupportedExpression(
            "The exact result exceeds the verifier's numeric size limit."
        )
    return quantity


def evaluate_expression(node: ExpressionNode) -> EvaluatedQuantity:
    """Evaluate a validated tree without parsing or executing generated code."""
    if _tree_size(node) > 32:
        raise UnsupportedExpression("Expression tree exceeds 32 nodes.")

    def evaluate(current: ExpressionNode) -> EvaluatedQuantity:
        return _bound_quantity(evaluate_node(current))

    def evaluate_node(current: ExpressionNode) -> EvaluatedQuantity:
        if current.kind == "number":
            dimension, factor, base_unit = _unit(current.unit)
            value = _to_sympy(_number(current.value))
            return EvaluatedQuantity(value * _to_sympy(factor), dimension, base_unit)

        values = [evaluate(child) for child in current.operands]
        if current.kind in ("add", "subtract"):
            left, right = values
            if left.dimension != right.dimension:
                raise UnsupportedExpression(
                    "Addition and subtraction require compatible units."
                )
            result = (
                left.value + right.value
                if current.kind == "add"
                else left.value - right.value
            )
            return EvaluatedQuantity(result, left.dimension, left.display_unit)

        if current.kind == "multiply":
            left, right = values
            if left.dimension != "dimensionless" and right.dimension != "dimensionless":
                raise UnsupportedExpression(
                    "Products of two unit-bearing quantities are unsupported."
                )
            measured = left if left.dimension != "dimensionless" else right
            scalar = right if measured is left else left
            return EvaluatedQuantity(
                measured.value * scalar.value,
                measured.dimension,
                measured.display_unit,
            )

        if current.kind == "divide":
            left, right = values
            if right.value == 0:
                raise UnsupportedExpression("Division by zero.")
            if right.dimension == "dimensionless":
                return EvaluatedQuantity(
                    left.value / right.value, left.dimension, left.display_unit
                )
            if left.dimension == right.dimension:
                return EvaluatedQuantity(
                    left.value / right.value, "dimensionless", ""
                )
            raise UnsupportedExpression(
                "Division of incompatible units is unsupported."
            )

        if current.kind == "power":
            base, exponent = values
            if exponent.dimension != "dimensionless" or not exponent.value.is_Integer:
                raise UnsupportedExpression(
                    "Only integer powers with a unitless exponent are supported."
                )
            power = int(exponent.value)
            if abs(power) > 12:
                raise UnsupportedExpression("Power magnitude exceeds 12.")
            if base.dimension != "dimensionless" and power not in (0, 1):
                raise UnsupportedExpression(
                    "Powers of unit-bearing quantities are unsupported."
                )
            return EvaluatedQuantity(
                base.value**power,
                base.dimension if power == 1 else "dimensionless",
                base.display_unit if power == 1 else "",
            )

        if current.kind == "sqrt":
            value = values[0]
            if value.dimension != "dimensionless":
                raise UnsupportedExpression(
                    "Square roots of unit-bearing quantities are unsupported."
                )
            result = sympy.sqrt(value.value)
            if result.is_real is False:
                raise UnsupportedExpression("Complex roots are unsupported.")
            if not result.is_Rational:
                raise UnsupportedExpression(
                    "Only exact rational square roots are supported."
                )
            return EvaluatedQuantity(result, "dimensionless", "")

        if current.kind == "negate":
            value = values[0]
            return EvaluatedQuantity(
                -value.value, value.dimension, value.display_unit
            )

        raise UnsupportedExpression(f"Unsupported operation {current.kind!r}.")

    return evaluate(node)


def expression_from_text(expression: str) -> ExpressionNode:
    """Convert deterministic arithmetic text into an allowlisted tree."""
    if len(expression) > 200:
        raise UnsupportedExpression("Expression is too large.")
    try:
        parsed = ast.parse(expression.replace(",", ""), mode="eval")
    except SyntaxError as error:
        raise UnsupportedExpression("Malformed arithmetic expression.") from error
    if sum(isinstance(node, ast.BinOp) for node in ast.walk(parsed)) > 8:
        raise UnsupportedExpression("Expression has too many operations.")

    operation_kinds = {
        ast.Add: "add",
        ast.Sub: "subtract",
        ast.Mult: "multiply",
        ast.Div: "divide",
        ast.Pow: "power",
    }

    def convert(node: ast.AST) -> ExpressionNode:
        if isinstance(node, ast.Expression):
            return convert(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            if isinstance(node.value, bool):
                raise UnsupportedExpression("Boolean values are unsupported.")
            return ExpressionNode(
                kind="number",
                value=str(node.value),
                evidence=str(node.value),
            )
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
            child = convert(node.operand)
            if isinstance(node.op, ast.UAdd):
                return child
            return ExpressionNode(kind="negate", operands=[child])
        if isinstance(node, ast.BinOp) and type(node.op) in operation_kinds:
            return ExpressionNode(
                kind=operation_kinds[type(node.op)],
                operands=[convert(node.left), convert(node.right)],
            )
        raise UnsupportedExpression("Expression contains unsupported syntax.")

    return convert(parsed)


def render_expression(node: ExpressionNode) -> str:
    if node.kind == "number":
        return node.value or ""
    symbols = {
        "add": "+",
        "subtract": "-",
        "multiply": "*",
        "divide": "/",
        "power": "^",
    }
    if node.kind == "negate":
        return "-(" + render_expression(node.operands[0]) + ")"
    if node.kind == "sqrt":
        return "sqrt(" + render_expression(node.operands[0]) + ")"
    symbol = symbols.get(node.kind)
    if symbol is None:
        raise UnsupportedExpression("Cannot render unsupported operation.")
    return (
        "("
        + render_expression(node.operands[0])
        + " "
        + symbol
        + " "
        + render_expression(node.operands[1])
        + ")"
    )


def format_result(value: sympy.Expr, unit: str = "") -> str:
    value = sympy.simplify(value)
    if value.is_Rational:
        rational = Fraction(int(value.p), int(value.q))
        rendered = str(rational.numerator)
        if rational.denominator != 1:
            rendered += "/" + str(rational.denominator)
    else:
        rendered = str(value)
    return (rendered + " " + unit).strip()


def convert_from_base(
    value: sympy.Expr, dimension: str, target_unit: Optional[str]
):
    if not target_unit:
        return value, _BASE_UNITS.get(dimension, "")
    target_dimension, factor, canonical = _unit(target_unit)
    if target_dimension != dimension:
        raise UnsupportedExpression(
            "The requested answer unit is incompatible with the result."
        )
    display_units = {
        "meter": "m",
        "meters": "m",
        "metre": "m",
        "metres": "m",
        "centimeter": "cm",
        "centimeters": "cm",
        "centimetre": "cm",
        "centimetres": "cm",
        "millimeter": "mm",
        "millimeters": "mm",
        "millimetre": "mm",
        "millimetres": "mm",
        "kilometer": "km",
        "kilometers": "km",
        "kilometre": "km",
        "kilometres": "km",
        "kilogram": "kg",
        "kilograms": "kg",
        "gram": "g",
        "grams": "g",
        "dollar": "USD",
        "dollars": "USD",
        "euro": "EUR",
        "euros": "EUR",
        "pound": "GBP",
        "pounds": "GBP",
    }
    output_unit = display_units.get(target_unit.casefold(), canonical)
    if target_unit in ("cm", "mm", "km", "m", "kg", "g", "L", "ml"):
        output_unit = target_unit
    return value / _to_sympy(factor), output_unit


def parse_numeric_answer(value: str):
    """Parse a numeric final answer into an exact SymPy value."""
    normalized = value.strip().replace(",", "")
    try:
        return _to_sympy(_number(normalized))
    except (ValueError, ZeroDivisionError):
        return None
