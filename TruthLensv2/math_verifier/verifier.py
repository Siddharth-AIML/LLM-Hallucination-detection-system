"""Conservative math verification using question-derived arithmetic."""

import logging
import re
import time
from dataclasses import asdict, dataclass, field
from fractions import Fraction
from typing import Optional

import sympy

from .answers import extract_final_answer
from .engine import (
    UnsupportedExpression,
    convert_from_base,
    evaluate_expression,
    expression_from_text,
    format_result,
    parse_numeric_answer,
    render_expression,
    unit_info,
)
from .interpreter import (
    InterpretationError,
    StructuredQuestionInterpreter,
)
from .models import MathInterpretation
from .reasoning import check_arithmetic_assertions


logger = logging.getLogger(__name__)


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
_ADD_MORE_ITEMS = re.compile(
    r"\b(?:has|have|had|contains?)\s+"
    r"(?P<left>" + _NUMBER + r")\s+(?P<item>[\w-]+)\b"
    r".{0,120}?\b(?:you\s+)?add(?:s|ed)?\s+"
    r"(?P<right>" + _NUMBER + r")\s+(?:more\s+)?(?P=item)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class _QuestionReconstruction:
    expression: Optional[str] = None
    ambiguous: bool = False


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
    expression_tree: Optional[dict] = None
    quantities: list[dict] = field(default_factory=list)
    solution_trace: list[str] = field(default_factory=list)
    reasoning_assertions: list[dict] = field(default_factory=list)
    intermediate_errors: list[dict] = field(default_factory=list)
    verification_coverage: dict = field(default_factory=dict)
    inconclusive_reason: Optional[str] = None
    final_answer_correct: Optional[bool] = None
    interpreter: str = "deterministic"
    model_calls: int = 0
    latency_ms: float = 0.0
    computed_exact_result: Optional[str] = None
    rounding_digits: Optional[int] = None

    def to_dict(self):
        return asdict(self)


def _question_expression(question):
    matches = list(_QUESTION_EXPRESSION.finditer(question))
    if matches:
        if len(matches) != 1 or not _QUESTION_MATH_CUE.search(question):
            return _QuestionReconstruction(ambiguous=True)
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
                return _QuestionReconstruction(ambiguous=True)
        return _QuestionReconstruction(match.group("expression"))

    sharing_matches = list(_PACKED_EQUAL_SHARING.finditer(question))
    if sharing_matches:
        if len(sharing_matches) != 1:
            return _QuestionReconstruction(ambiguous=True)
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
            return _QuestionReconstruction(ambiguous=True)
        return _QuestionReconstruction(operands[0] + " / " + operands[1])

    addition_matches = list(_ADD_MORE_ITEMS.finditer(question))
    if addition_matches:
        if len(addition_matches) != 1:
            return _QuestionReconstruction(ambiguous=True)
        match = addition_matches[0]
        operands = [
            match.group("left").replace(",", ""),
            match.group("right").replace(",", ""),
        ]
        numbers = [
            value.replace(",", "")
            for value in _QUESTION_NUMBERS.findall(question)
        ]
        if numbers != operands:
            return _QuestionReconstruction(ambiguous=True)
        return _QuestionReconstruction(operands[0] + " + " + operands[1])

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
    if not matches:
        return _QuestionReconstruction()
    if len(matches) != 1:
        return _QuestionReconstruction(ambiguous=True)

    operator, match = matches[0]
    operands = [value.replace(",", "") for value in match.groups()]
    numbers = [
        value.replace(",", "")
        for value in _QUESTION_NUMBERS.findall(question)
    ]
    if numbers != operands:
        return _QuestionReconstruction(ambiguous=True)
    return _QuestionReconstruction(
        operands[0] + " " + operator + " " + operands[1]
    )


def _result(
    question,
    answer,
    verdict,
    expression,
    computed_result,
    extraction,
    explanation,
    started,
    interpreter_name="deterministic",
    interpretation=None,
    assertions=None,
    coverage=None,
    inconclusive_reason=None,
    final_answer_correct=None,
    model_calls=0,
    computed_exact_result=None,
    rounding_digits=None,
):
    assertions = assertions or {}
    coverage = coverage or {}
    tree = interpretation.expression if interpretation else None
    quantities = interpretation.quantities if interpretation else []
    trace = interpretation.solution_steps if interpretation else []
    return MathVerificationResult(
        original_question=question,
        llm_answer=answer,
        verdict=verdict,
        extracted_expression=expression,
        computed_result=computed_result,
        original_answer=extraction.value if extraction else None,
        explanation=explanation,
        verification_status=(
            "conclusive" if verdict != UNABLE_TO_VERIFY else "inconclusive"
        ),
        is_conclusive=verdict != UNABLE_TO_VERIFY,
        expression_tree=tree.model_dump() if tree else None,
        quantities=[item.model_dump() for item in quantities],
        solution_trace=list(trace),
        reasoning_assertions=[
            item.to_dict() for item in assertions.get("assertions", [])
        ],
        intermediate_errors=[
            item.to_dict() for item in assertions.get("false_assertions", [])
        ],
        verification_coverage=coverage,
        inconclusive_reason=inconclusive_reason,
        final_answer_correct=final_answer_correct,
        interpreter=interpreter_name,
        model_calls=model_calls,
        latency_ms=round((time.perf_counter() - started) * 1000, 2),
        computed_exact_result=computed_exact_result,
        rounding_digits=rounding_digits,
    )


def _inconclusive(
    question,
    answer,
    extraction,
    expression,
    explanation,
    started,
    interpreter_name="deterministic",
    interpretation=None,
    assertions=None,
    reason=None,
    model_calls=0,
):
    coverage = {
        "question_interpretation": (
            "complete" if interpretation is not None else "incomplete"
        ),
        "final_answer_extraction": (
            "ambiguous"
            if extraction and extraction.ambiguous
            else "extracted"
            if extraction and extraction.value is not None
            else "failed"
        ),
        "reasoning_assertions": (
            "partial"
            if assertions and assertions.get("unsupported_count")
            else "complete"
            if assertions
            else "not_checked"
        ),
        "assertions_checked": (
            assertions.get("checked_count", 0) if assertions else 0
        ),
        "assertions_excluded": (
            assertions.get("excluded_count", 0) if assertions else 0
        ),
        "unsupported_assertions": (
            assertions.get("unsupported_count", 0) if assertions else 0
        ),
    }
    return _result(
        question,
        answer,
        UNABLE_TO_VERIFY,
        expression,
        None,
        extraction,
        explanation,
        started,
        interpreter_name,
        interpretation,
        assertions,
        coverage,
        reason or explanation,
        model_calls=model_calls,
    )


def _comparison_value(extraction):
    if extraction.value is None:
        return None, None
    value = parse_numeric_answer(extraction.value)
    if value is None:
        return None, None
    try:
        dimension, factor, _ = unit_info(extraction.unit)
    except UnsupportedExpression:
        return None, None
    factor_sympy = sympy.Rational(factor.numerator, factor.denominator)
    return value * factor_sympy, dimension


def _round_rational(value, decimal_places):
    if not value.is_Rational:
        raise UnsupportedExpression(
            "Only exact rational values can be rounded safely."
        )
    scale = 10**decimal_places
    numerator = int(value.p) * scale
    denominator = int(value.q)
    sign = -1 if numerator < 0 else 1
    quotient, remainder = divmod(abs(numerator), denominator)
    if remainder * 2 >= denominator:
        quotient += 1
    return sympy.Rational(sign * quotient, scale)


def _format_rounded_result(value, decimal_places, unit):
    scale = 10**decimal_places
    scaled = int(value * scale)
    sign = "-" if scaled < 0 else ""
    whole, fractional = divmod(abs(scaled), scale)
    rendered = sign + str(whole)
    if decimal_places:
        rendered += "." + str(fractional).zfill(decimal_places)
    return (rendered + " " + unit).strip()


def _false_assertion_result(
    question,
    answer,
    extraction,
    expression,
    computed_result,
    assertions,
    started,
    interpreter_name,
    interpretation=None,
    model_calls=0,
):
    false_assertions = assertions["false_assertions"]
    if not false_assertions:
        return None
    details = "; ".join(
        assertion.expression
        + " = "
        + assertion.stated_result
        + " (computed as "
        + str(assertion.computed_result)
        + ")"
        for assertion in false_assertions
    )
    coverage = {
        "question_interpretation": (
            "complete" if interpretation is not None else "incomplete"
        ),
        "reasoning_assertions": "incorrect",
        "assertions_checked": assertions["checked_count"],
        "assertions_excluded": assertions["excluded_count"],
        "unsupported_assertions": assertions["unsupported_count"],
    }
    return _result(
        question,
        answer,
        INCORRECT,
        expression,
        computed_result,
        extraction,
        "The response contains mathematically incorrect arithmetic "
        "assertion(s): " + details + ".",
        started,
        interpreter_name,
        interpretation,
        assertions,
        coverage,
        final_answer_correct=None,
        model_calls=model_calls,
    )


def _canonical_expression(tree, original):
    if original is not None:
        return original
    if (
        tree.kind in ("add", "subtract", "multiply", "divide")
        and all(child.kind == "number" for child in tree.operands)
    ):
        symbols = {
            "add": "+",
            "subtract": "-",
            "multiply": "*",
            "divide": "/",
        }
        return (
            (tree.operands[0].value or "")
            + " "
            + symbols[tree.kind]
            + " "
            + (tree.operands[1].value or "")
        )
    return render_expression(tree)


def verify_math_answer(question, answer, interpreter=None):
    """Interpret a question, safely execute its tree, then audit the response."""
    started = time.perf_counter()
    question = question.strip()
    answer = answer.strip()
    if len(question) > 4000 or len(answer) > 12000:
        extraction = extract_final_answer(answer)
        return _inconclusive(
            question,
            answer,
            extraction,
            None,
            "Question or answer exceeds the verifier's input limit.",
            started,
            reason="input_limit",
        )

    extraction = extract_final_answer(answer)
    assertions = check_arithmetic_assertions(answer)
    reconstruction = _question_expression(question)
    deterministic_expression = reconstruction.expression
    if reconstruction.ambiguous:
        false_assertion = _false_assertion_result(
            question,
            answer,
            extraction,
            None,
            None,
            assertions,
            started,
            "deterministic",
        )
        if false_assertion is not None:
            return false_assertion
        return _inconclusive(
            question,
            answer,
            extraction,
            None,
            "The question contains a recognized calculation pattern with "
            "ambiguous or additional operands.",
            started,
            assertions=assertions,
            reason="ambiguous_question",
        )
    model_calls_before = getattr(interpreter, "model_calls", 0)
    if deterministic_expression is not None:
        try:
            tree = expression_from_text(deterministic_expression)
            interpretation = MathInterpretation(
                status="supported",
                confidence=1.0,
                quantities=[],
                expression=tree,
                requested_quantity="answer",
                solution_steps=[
                    "Reconstructed supported arithmetic from the original question."
                ],
            )
            interpreter_name = "deterministic"
        except (SyntaxError, UnsupportedExpression, ValueError) as error:
            logger.info(
                "Deterministic math parsing was unsupported (%s).",
                type(error).__name__,
            )
            deterministic_expression = None

    if deterministic_expression is None:
        interpreter = interpreter or StructuredQuestionInterpreter()
        try:
            interpretation = interpreter.interpret(question)
            interpreter_name = "groq_structured"
        except InterpretationError as error:
            logger.warning(
                "Structured math interpretation failed (%s).",
                type(error).__name__,
            )
            model_calls = max(
                0, getattr(interpreter, "model_calls", 0) - model_calls_before
            )
            false_assertion = _false_assertion_result(
                question,
                answer,
                extraction,
                None,
                None,
                assertions,
                started,
                "groq_structured",
                model_calls=model_calls,
            )
            if false_assertion is not None:
                return false_assertion
            return _inconclusive(
                question,
                answer,
                extraction,
                None,
                str(error),
                started,
                interpreter_name="groq_structured",
                reason="question_interpretation_failed",
                model_calls=model_calls,
            )
        if interpretation.status != "supported" or interpretation.expression is None:
            reason = interpretation.reason or (
                "The structured interpreter classified the question as "
                + interpretation.status + "."
            )
            model_calls = max(
                0, getattr(interpreter, "model_calls", 0) - model_calls_before
            )
            false_assertion = _false_assertion_result(
                question,
                answer,
                extraction,
                None,
                None,
                assertions,
                started,
                interpreter_name,
                interpretation,
                model_calls,
            )
            if false_assertion is not None:
                return false_assertion
            return _inconclusive(
                question,
                answer,
                extraction,
                None,
                reason,
                started,
                interpreter_name,
                interpretation,
                reason="ambiguous_question"
                if interpretation.status == "ambiguous"
                else "unsupported_question",
                model_calls=model_calls,
            )

    expression_tree = interpretation.expression
    expression = _canonical_expression(expression_tree, deterministic_expression)
    model_calls = max(
        0, getattr(interpreter, "model_calls", 0) - model_calls_before
    )
    try:
        computed = evaluate_expression(expression_tree)
        computed_display, display_unit = convert_from_base(
            computed.value, computed.dimension, interpretation.target_unit
        )
        exact_result = format_result(computed_display, display_unit)
        expected_value = computed.value
        if interpretation.rounding_digits is not None:
            computed_display = _round_rational(
                computed_display, interpretation.rounding_digits
            )
            if interpretation.target_unit:
                _, factor, _ = unit_info(interpretation.target_unit)
            else:
                factor = Fraction(1)
            expected_value = computed_display * sympy.Rational(
                factor.numerator, factor.denominator
            )
            interpretation.solution_steps.append(
                "Rounded the exact result to "
                + str(interpretation.rounding_digits)
                + " decimal place(s) as requested."
            )
    except (UnsupportedExpression, ArithmeticError, ValueError) as error:
        return _inconclusive(
            question,
            answer,
            extraction,
            expression,
            str(error),
            started,
            interpreter_name,
            interpretation,
            reason="expression_execution_failed",
            model_calls=model_calls,
        )

    computed_result = (
        _format_rounded_result(
            computed_display,
            interpretation.rounding_digits,
            display_unit,
        )
        if interpretation.rounding_digits is not None
        else format_result(computed_display, display_unit)
    )
    if extraction.ambiguous or extraction.value is None:
        false_assertion = _false_assertion_result(
            question,
            answer,
            extraction,
            expression,
            computed_result,
            assertions,
            started,
            interpreter_name,
            interpretation,
            model_calls,
        )
        if false_assertion is not None:
            return false_assertion
        return _inconclusive(
            question,
            answer,
            extraction,
            expression,
            (
                "The response contains multiple incompatible candidate final "
                "answers, so the intended answer cannot be selected reliably."
                if extraction.ambiguous
                else "No unambiguous final numeric answer could be extracted."
            ),
            started,
            interpreter_name,
            interpretation,
            reason=(
                "conflicting_final_answers"
                if extraction.ambiguous
                else "final_answer_extraction_failed"
            ),
            model_calls=model_calls,
        )
    proposed, proposed_dimension = _comparison_value(extraction)
    if proposed is None:
        return _inconclusive(
            question,
            answer,
            extraction,
            expression,
            "The extracted final answer is not a supported exact numeric value.",
            started,
            interpreter_name,
            interpretation,
            reason="unsupported_final_answer",
            model_calls=model_calls,
        )
    if (
        computed.dimension != "dimensionless"
        and proposed_dimension != computed.dimension
    ):
        return _inconclusive(
            question,
            answer,
            extraction,
            expression,
            "The answer unit is missing or incompatible with the computed "
            "quantity.",
            started,
            interpreter_name,
            interpretation,
            reason="answer_unit_mismatch",
            model_calls=model_calls,
        )

    final_answer_correct = sympy.simplify(expected_value - proposed) == 0
    false_assertions = assertions["false_assertions"]
    has_unsupported_assertions = assertions["unsupported_count"] > 0
    coverage = {
        "question_interpretation": "complete",
        "interpreter": interpreter_name,
        "final_answer_extraction": extraction.source,
        "final_answer": "correct" if final_answer_correct else "incorrect",
        "reasoning_assertions": (
            "partial" if has_unsupported_assertions else "complete"
        ),
        "assertions_checked": assertions["checked_count"],
        "assertions_excluded": assertions["excluded_count"],
        "unsupported_assertions": assertions["unsupported_count"],
    }
    error_text = "; ".join(
        assertion.expression + " = " + assertion.stated_result
        for assertion in false_assertions
    )
    sharing = _PACKED_EQUAL_SHARING.search(question)
    if sharing:
        dividend = sharing.group("dividend")
        divisor = sharing.group("divisor")
        item = sharing.group("item")
        container = sharing.group("container")
        container_singular = re.sub(
            r"es$|s$",
            lambda match: "" if match.group().lower() == "es" else "",
            container,
            flags=re.IGNORECASE,
        )
        calculation_summary = (
            f"{dividend} {item} divided equally among {divisor} "
            f"{container} gives {computed_result} {item} per "
            f"{container_singular}"
        )
    elif expression and "/" in expression:
        dividend, divisor = (part.strip() for part in expression.split("/", 1))
        calculation_summary = (
            f"{dividend} divided equally by {divisor} gives {computed_result}"
        )
    else:
        calculation_summary = (
            f"The question-derived expression {expression} evaluates to "
            f"{computed_result}"
        )
    if not final_answer_correct:
        verdict = INCORRECT
        explanation = (
            calculation_summary + ", not the response's final answer "
            + extraction.value + "."
        )
    elif false_assertions:
        verdict = INCORRECT
        explanation = (
            f"The final answer {extraction.value} matches the independently "
            f"computed result {computed_result}, but the intermediate "
            f"calculation {error_text} is incorrect."
        )
    elif has_unsupported_assertions:
        return _inconclusive(
            question,
            answer,
            extraction,
            expression,
            "The final answer matches the computed result, but one or more "
            "equation-like reasoning claims could not be verified safely.",
            started,
            interpreter_name,
            interpretation,
            assertions,
            reason="unsupported_reasoning_assertion",
            model_calls=model_calls,
        )
    else:
        verdict = VERIFIED
        explanation = (
            calculation_summary + ", matching the final answer; all supported "
            "arithmetic assertions in the response are consistent."
        )

    return _result(
        question,
        answer,
        verdict,
        expression,
        computed_result,
        extraction,
        explanation,
        started,
        interpreter_name,
        interpretation,
        assertions,
        coverage,
        final_answer_correct=final_answer_correct,
        model_calls=model_calls,
        computed_exact_result=exact_result,
        rounding_digits=interpretation.rounding_digits,
    )
