import json
import os
import types
import unittest
from unittest.mock import patch

from math_verifier.engine import (
    UnsupportedExpression,
    convert_from_base,
    evaluate_expression,
    expression_from_text,
)
from math_verifier.interpreter import (
    InterpretationError,
    StructuredQuestionInterpreter,
    validate_interpretation,
)
from math_verifier.models import ExpressionNode, MathInterpretation
from math_verifier.verifier import verify_math_answer


def number(value, evidence, unit=None):
    return ExpressionNode(
        kind="number",
        value=value,
        unit=unit,
        evidence=evidence,
    )


def binary(kind, left, right):
    return ExpressionNode(kind=kind, operands=[left, right])


def interpretation(expression, confidence=0.95):
    return MathInterpretation(
        status="supported",
        confidence=confidence,
        quantities=[],
        expression=expression,
    )


class MathSchemaTests(unittest.TestCase):
    def test_expression_schema_rejects_invalid_arity(self):
        with self.assertRaises(ValueError):
            ExpressionNode(kind="add", operands=[number("2", "2")])

    def test_schema_rejects_unknown_fields_and_operators(self):
        with self.assertRaises(ValueError):
            MathInterpretation.model_validate(
                {
                    "status": "supported",
                    "confidence": 0.95,
                    "quantities": [],
                    "expression": {
                        "kind": "execute",
                        "value": "__import__('os')",
                        "evidence": "2",
                        "operands": [],
                    },
                }
            )

    def test_interpretation_requires_expression_for_supported_status(self):
        with self.assertRaises(ValueError):
            MathInterpretation(
                status="supported",
                confidence=0.95,
                quantities=[],
            )


class SafeExpressionEngineTests(unittest.TestCase):
    def test_exact_fraction_arithmetic(self):
        tree = expression_from_text("(1 / 3) + (1 / 6)")
        self.assertEqual(str(evaluate_expression(tree).value), "1/2")

    def test_exact_square_root(self):
        tree = ExpressionNode(
            kind="sqrt",
            operands=[number("81", "81")],
        )
        self.assertEqual(str(evaluate_expression(tree).value), "9")

    def test_irrational_square_root_is_rejected(self):
        tree = ExpressionNode(
            kind="sqrt",
            operands=[number("2", "2")],
        )
        with self.assertRaises(UnsupportedExpression):
            evaluate_expression(tree)

    def test_zero_division_is_rejected(self):
        tree = expression_from_text("4 / 0")
        with self.assertRaises(UnsupportedExpression):
            evaluate_expression(tree)

    def test_oversized_intermediate_is_rejected(self):
        tree = ExpressionNode(
            kind="power",
            operands=[
                number("9" * 128, "9" * 128),
                number("12", "12"),
            ],
        )
        with self.assertRaises(UnsupportedExpression):
            evaluate_expression(tree)

    def test_generated_python_is_not_executed(self):
        with self.assertRaises(UnsupportedExpression):
            expression_from_text("__import__('os').system('echo unsafe')")

    def test_unit_conversion_is_exact(self):
        tree = binary(
            "add",
            number("1", "1 meter", "meter"),
            number("25", "25 cm", "cm"),
        )
        result = evaluate_expression(tree)
        converted, unit = convert_from_base(
            result.value, result.dimension, "cm"
        )
        self.assertEqual(str(converted), "125")
        self.assertEqual(unit, "cm")

    def test_incompatible_units_are_rejected(self):
        tree = binary(
            "add",
            number("1", "1 meter", "meter"),
            number("1", "1 kilogram", "kg"),
        )
        with self.assertRaises(UnsupportedExpression):
            evaluate_expression(tree)


class StructuredInterpreterTests(unittest.TestCase):
    def _client(self, payload):
        content = json.dumps(payload)
        message = types.SimpleNamespace(content=content)
        response = types.SimpleNamespace(
            choices=[types.SimpleNamespace(message=message)]
        )
        def create(**kwargs):
            if kwargs.get("temperature") != 0:
                raise AssertionError("The structured model must be deterministic.")
            return response

        completions = types.SimpleNamespace(create=create)
        return types.SimpleNamespace(
            chat=types.SimpleNamespace(completions=completions)
        )

    def _payload(self, **overrides):
        payload = {
            "status": "supported",
            "confidence": 0.95,
            "quantities": [],
            "expression": {
                "kind": "add",
                "operands": [
                    {
                        "kind": "number",
                        "value": "2",
                        "unit": None,
                        "evidence": "2",
                        "operands": [],
                    },
                    {
                        "kind": "number",
                        "value": "3",
                        "unit": None,
                        "evidence": "3",
                        "operands": [],
                    },
                ],
            },
            "requested_quantity": "sum",
            "target_unit": "",
            "rounding_digits": None,
            "assumptions": [],
            "solution_steps": [],
            "reason": "",
        }
        payload.update(overrides)
        return payload

    def test_valid_json_interpretation_is_checked_against_question(self):
        interpreter = StructuredQuestionInterpreter(
            client=self._client(self._payload())
        )
        result = interpreter.interpret("What is the sum of 2 and 3?")
        self.assertEqual(result.expression.kind, "add")
        self.assertEqual(interpreter.model_calls, 1)

    def test_wrong_operator_is_rejected_even_with_grounded_operands(self):
        payload = self._payload(
            expression={
                "kind": "subtract",
                "operands": self._payload()["expression"]["operands"],
            }
        )
        interpreter = StructuredQuestionInterpreter(
            client=self._client(payload)
        )
        with self.assertRaises(InterpretationError):
            interpreter.interpret("What is the sum of 2 and 3?")

    def test_unstated_operator_is_rejected_even_with_grounded_operands(self):
        interpreter = StructuredQuestionInterpreter(
            client=self._client(self._payload())
        )
        with self.assertRaises(InterpretationError):
            interpreter.interpret("A story mentions 2 and 3. What is the answer?")

    def test_leaf_cannot_invent_or_reuse_question_operands(self):
        payload = self._payload(
            expression={
                "kind": "add",
                "operands": [
                    {
                        "kind": "number",
                        "value": "2",
                        "unit": None,
                        "evidence": "2",
                        "operands": [],
                    },
                    {
                        "kind": "number",
                        "value": "2",
                        "unit": None,
                        "evidence": "2",
                        "operands": [],
                    },
                ],
            }
        )
        with self.assertRaises(InterpretationError):
            validate_interpretation(
                "What is the sum of 2 and 3?",
                MathInterpretation.model_validate(payload),
            )

    def test_low_confidence_interpretation_is_rejected(self):
        interpreter = StructuredQuestionInterpreter(
            client=self._client(self._payload(confidence=0.5))
        )
        with self.assertRaises(InterpretationError):
            interpreter.interpret("What is the sum of 2 and 3?")

    def test_malformed_structured_response_is_rejected(self):
        client = self._client(self._payload())
        def malformed_response(**kwargs):
            if "model" not in kwargs:
                raise AssertionError("The structured model name is required.")
            return types.SimpleNamespace(
                choices=[
                    types.SimpleNamespace(
                        message=types.SimpleNamespace(content="{")
                    )
                ]
            )

        client.chat.completions.create = malformed_response
        interpreter = StructuredQuestionInterpreter(client=client)
        with self.assertRaises(InterpretationError):
            interpreter.interpret("What is the sum of 2 and 3?")

    def test_absent_credentials_fail_explicitly_without_network(self):
        interpreter = StructuredQuestionInterpreter()
        with patch.dict(os.environ, {}, clear=True):
            with patch("dotenv.load_dotenv"):
                with self.assertRaisesRegex(
                    InterpretationError, "Configure GROQ_API_KEY"
                ):
                    interpreter.interpret("A problem requiring interpretation.")

    def test_unstated_target_unit_is_rejected(self):
        payload = self._payload(
            expression={
                "kind": "number",
                "value": "2",
                "unit": None,
                "evidence": "2",
                "operands": [],
            },
            target_unit="cm",
        )
        interpreter = StructuredQuestionInterpreter(
            client=self._client(payload)
        )
        with self.assertRaises(InterpretationError):
            interpreter.interpret("What is the value of 2?")


class RoundingTests(unittest.TestCase):
    def test_explicit_rounding_is_applied_and_reported(self):
        result = verify_math_answer(
            "Round 2.55 to one decimal place.",
            "The answer is 2.6.",
            interpreter=StaticInterpreter(
                MathInterpretation(
                    status="supported",
                    confidence=0.95,
                    quantities=[],
                    expression=number("2.55", "2.55"),
                    rounding_digits=1,
                )
            ),
        )
        self.assertEqual(result.verdict, "VERIFIED")
        self.assertEqual(result.computed_result, "2.6")
        self.assertEqual(result.computed_exact_result, "51/20")
        self.assertEqual(result.rounding_digits, 1)

    def test_wrong_rounded_answer_is_incorrect(self):
        result = verify_math_answer(
            "Round 2.55 to one decimal place.",
            "The answer is 2.5.",
            interpreter=StaticInterpreter(
                MathInterpretation(
                    status="supported",
                    confidence=0.95,
                    quantities=[],
                    expression=number("2.55", "2.55"),
                    rounding_digits=1,
                )
            ),
        )
        self.assertEqual(result.verdict, "INCORRECT")


class StaticInterpreter:
    def __init__(self, result):
        self.result = result
        self.model_calls = 0

    def interpret(self, question):
        self.model_calls += 1
        return validate_interpretation(question, self.result)


if __name__ == "__main__":
    unittest.main()
