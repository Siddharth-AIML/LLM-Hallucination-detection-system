"""Conservative math verification using question-derived arithmetic."""

import ast
import re
from dataclasses import asdict, dataclass
from fractions import Fraction
from typing import Optional

import sympy


VERIFIED = "VERIFIED"
INCORRECT = "INCORRECT"
UNABLE_TO_VERIFY = "UNABLE_TO_VERIFY"

_NUMBER = r"\d{1,12}(?:,\d{3})*(?:\.\d{1,8})?"
_QUESTION_EXPRESSION = re.compile(
    r"(?<![\w.^])"
    r"(?P<expression>-?\d[\d,]*(?:\.\d+)?"
    r"(?:\s*[+*/-]\s*-?\d[\d,]*(?:\.\d+)?)+)"
    r"(?![\w.])"
)
_QUESTION_MATH_CUE = re.compile(
    r"\b(?:what is|calculate|compute|evaluate|solve|"
    r"equals?|sum|product|difference|quotient|confirm|"
    r"assert|insist|correct)\b|=",
    re.IGNORECASE,
)
_QUESTION_NUMBERS = re.compile(r"(?<![\w.])(" + _NUMBER + r")(?![\w.])")
_PACKED_EQUAL_SHARING = re.compile(
    r"\b(?:has|have|had|contains?|there are|there were)\s+"
    r"(?P<dividend>" + _NUMBER + r")\s+(?P<item>[\w-]+)\b"
    r".{0,160}?\b(?:packs?|distributes?|places?|puts?|splits?|divides?)\s+"
    r"them\s+equally\s+(?:into|among|between)\s+"
    r"(?P<divisor>" + _NUMBER + r")\s+"
    r"(?P<container>boxes?|bags?|groups?|baskets?|containers?|"
    r"people|friends|students|children|teams|piles|packets?)\b",
    re.IGNORECASE,
)
_FINAL_HASHED_ANSWER = re.compile(
    r"####\s*\$?\s*(" + _NUMBER + r")", re.IGNORECASE
)
_LABELED_ANSWER = re.compile(
    r"\b(?:final answer|answer|result|total)\s*(?:is|:|=)\s*"
    r"\$?\s*(" + _NUMBER + r")",
    re.IGNORECASE,
)
_EQUATION_RESULT = re.compile(
    r"=\s*\$?\s*(" + _NUMBER + r")\s*(?:[.!?]|$)"
)
_ENDING_NUMBER = re.compile(
    r"(?<![\w.])\$?\s*(" + _NUMBER + r")\s*%?"
    r"(?:\s+[A-Za-z][A-Za-z-]*){0,3}\s*[.!?]?\s*$"
)


@dataclass(frozen=True)
class MathVerificationResult:
    original_question: str
    llm_answer: str
    verdict: str
    extracted_expression: Optional[str]
    computed_result: Optional[str]
    original_answer: Optional[str]
    explanation: str
    verification_status: str
    is_conclusive: bool

    def to_dict(self):
        return asdict(self)


def _parse_number(value):
    return Fraction(value.replace(",", ""))


def _format_number(value):
    if value.denominator == 1:
        return str(value.numerator)
    return str(value.numerator) + "/" + str(value.denominator)


def _extract_answer(answer):
    for pattern in (
        _FINAL_HASHED_ANSWER,
        _LABELED_ANSWER,
        _EQUATION_RESULT,
        _ENDING_NUMBER,
    ):
        matches = list(pattern.finditer(answer))
        if matches:
            return matches[-1].group(1)
    return None


class _ArithmeticEvaluator(ast.NodeVisitor):
    _operations = {
        ast.Add: lambda left, right: left + right,
        ast.Sub: lambda left, right: left - right,
        ast.Mult: lambda left, right: left * right,
        ast.Div: lambda left, right: left / right,
    }

    def visit_Expression(self, node):
        return self.visit(node.body)

    def visit_Constant(self, node):
        if isinstance(node.value, bool) or not isinstance(
            node.value, (int, float)
        ):
            raise ValueError("Only numeric constants are supported.")
        return Fraction(str(node.value))

    def visit_UnaryOp(self, node):
        value = self.visit(node.operand)
        if isinstance(node.op, ast.USub):
            return -value
        if isinstance(node.op, ast.UAdd):
            return value
        raise ValueError("Unsupported unary operator.")

    def visit_BinOp(self, node):
        operation = self._operations.get(type(node.op))
        if operation is None:
            raise ValueError("Unsupported arithmetic operator.")
        return operation(self.visit(node.left), self.visit(node.right))

    def generic_visit(self, node):
        raise ValueError("Unsupported expression syntax.")


def _evaluate(expression):
    if len(expression) > 200 or expression.count(" ") > 32:
        raise ValueError("Expression is too large.")
    normalized = expression.replace(",", "")
    tree = ast.parse(normalized, mode="eval")
    if sum(isinstance(node, ast.BinOp) for node in ast.walk(tree)) > 8:
        raise ValueError("Expression has too many operations.")
    return _ArithmeticEvaluator().visit(tree)


def _question_expression(question):
    matches = list(_QUESTION_EXPRESSION.finditer(question))
    if matches:
        if len(matches) != 1 or not _QUESTION_MATH_CUE.search(question):
            return None
        match = matches[0]
        expression_numbers = [
            value.replace(",", "")
            for value in re.findall(_NUMBER, match.group("expression"))
        ]
        question_numbers = [
            value.replace(",", "")
            for value in _QUESTION_NUMBERS.findall(question)
        ]
        if question_numbers != expression_numbers:
            suffix = question[match.end():]
            equation_result = re.match(
                r"\s*=\s*(" + _NUMBER + r")(?![\w.])", suffix
            )
            if (
                not equation_result
                or question_numbers
                != expression_numbers + [equation_result.group(1).replace(",", "")]
            ):
                return None
        return match.group("expression")

    sharing_matches = list(_PACKED_EQUAL_SHARING.finditer(question))
    if sharing_matches:
        if len(sharing_matches) != 1:
            return None
        match = sharing_matches[0]
        operands = [
            match.group("dividend").replace(",", ""),
            match.group("divisor").replace(",", ""),
        ]
        numbers = [
            value.replace(",", "")
            for value in _QUESTION_NUMBERS.findall(question)
        ]
        if numbers != operands:
            return None
        return operands[0] + " / " + operands[1]

    number = r"(" + _NUMBER + r")"
    templates = (
        (
            "+",
            re.compile(r"\b" + number + r"\s+plus\s+" + number + r"\b", re.I),
        ),
        (
            "+",
            re.compile(
                r"\bsum of\s+" + number + r"\s+and\s+" + number + r"\b", re.I
            ),
        ),
        (
            "+",
            re.compile(
                r"\b(?:has|had|starts with|started with)\s+"
                + number
                + r"\s+[\w-]+\s*,?\s*(?:and\s+)?(?:then\s+)?"
                r"(?:buys?|gets?|receives?|earns?|collects?|gains?)\s+"
                + number
                + r"\b",
                re.I,
            ),
        ),
        (
            "+",
            re.compile(
                r"\b"
                + number
                + r"\s+[\w-]+\s+and\s+"
                + number
                + r"\s+[\w-]+\s+(?:altogether|in total|combined)\b",
                re.I,
            ),
        ),
        (
            "-",
            re.compile(r"\b" + number + r"\s+minus\s+" + number + r"\b", re.I),
        ),
        (
            "-",
            re.compile(
                r"\b(?:has|had|starts with|started with)\s+"
                + number
                + r"\s+[\w-]+\s*,?\s*(?:and\s+)?"
                r"(?:then\s+)?(?:gives? away|gave away|sells?|sold|"
                r"spends?|spent|uses?|used|eats?|ate|loses?|lost)\s+"
                + number
                + r"\b",
                re.I,
            ),
        ),
        (
            "*",
            re.compile(
                r"\b" + number + r"\s+groups? of\s+" + number + r"\b", re.I
            ),
        ),
        (
            "*",
            re.compile(
                r"\b"
                + number
                + r"\s+[\w-]+\s+(?:with|containing)\s+"
                + number
                + r"\s+[\w-]+\s+each\b",
                re.I,
            ),
        ),
        (
            "*",
            re.compile(
                r"\b"
                + number
                + r"\s+[\w-]+\s+each\s+with\s+"
                + number
                + r"\s+[\w-]+\b",
                re.I,
            ),
        ),
        (
            "/",
            re.compile(
                r"\b"
                + number
                + r"\s+[\w-]+\s+(?:(?:are|were|is|was)\s+)?"
                r"(?:shared|split|divided)\s+equally\s+"
                r"(?:among|between|by|into)\s+"
                + number
                + r"\b",
                re.I,
            ),
        ),
    )
    matches = []
    for operator, pattern in templates:
        matches.extend(
            (operator, match) for match in pattern.finditer(question)
        )
    if len(matches) != 1:
        return None

    operator, match = matches[0]
    operands = [value.replace(",", "") for value in match.groups()]
    numbers = [
        value.replace(",", "")
        for value in _QUESTION_NUMBERS.findall(question)
    ]
    if numbers != operands:
        return None
    return operands[0] + " " + operator + " " + operands[1]


def _unable(question, answer, extracted_answer, expression, explanation):
    return MathVerificationResult(
        original_question=question,
        llm_answer=answer,
        verdict=UNABLE_TO_VERIFY,
        extracted_expression=expression,
        computed_result=None,
        original_answer=extracted_answer,
        explanation=explanation,
        verification_status="inconclusive",
        is_conclusive=False,
    )


def verify_math_answer(question, answer):
    """Verify a final numeric answer only when the question is reconstructable."""
    question = question.strip()
    answer = answer.strip()
    extracted_answer = _extract_answer(answer)
    expression = _question_expression(question)

    if expression is None:
        return _unable(
            question,
            answer,
            extracted_answer,
            None,
            "The calculation cannot be reconstructed unambiguously from "
            "the question, so the answer was not guessed.",
        )
    if extracted_answer is None:
        return _unable(
            question,
            answer,
            None,
            expression,
            "No unambiguous final numeric answer could be extracted from "
            "the response.",
        )

    try:
        computed = _evaluate(expression)
        proposed = _parse_number(extracted_answer)
    except (ArithmeticError, SyntaxError, ValueError, ZeroDivisionError):
        return _unable(
            question,
            answer,
            extracted_answer,
            expression,
            "The reconstructed arithmetic is unsupported or could not be "
            "evaluated safely.",
        )

    computed_sympy = sympy.Rational(computed.numerator, computed.denominator)
    proposed_sympy = sympy.Rational(proposed.numerator, proposed.denominator)
    correct = sympy.simplify(computed_sympy - proposed_sympy) == 0
    computed_result = _format_number(computed)
    sharing = _PACKED_EQUAL_SHARING.search(question)
    if sharing:
        dividend = sharing.group("dividend")
        divisor = sharing.group("divisor")
        item = sharing.group("item")
        container = sharing.group("container")
        container_singular = re.sub(r"s$", "", container, flags=re.IGNORECASE)
        explanation = (
            f"{dividend} {item} divided equally among {divisor} "
            f"{container} gives {computed_result} {item} per "
            f"{container_singular}"
        )
    elif expression and "/" in expression:
        dividend, divisor = (part.strip() for part in expression.split("/", 1))
        explanation = (
            f"{dividend} divided equally by {divisor} gives {computed_result}"
        )
    else:
        explanation = (
            "The question-derived expression " + expression + " evaluates to "
            + computed_result
        )
    if correct:
        verdict = VERIFIED
        explanation += ", matching the response's final answer."
    else:
        verdict = INCORRECT
        explanation += (
            ", not the response's final answer " + extracted_answer + "."
        )

    return MathVerificationResult(
        original_question=question,
        llm_answer=answer,
        verdict=verdict,
        extracted_expression=expression,
        computed_result=computed_result,
        original_answer=extracted_answer,
        explanation=explanation,
        verification_status="conclusive",
        is_conclusive=True,
    )
