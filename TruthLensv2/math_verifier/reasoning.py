"""Conservative checking of explicit arithmetic assertions in responses."""

import re
from dataclasses import asdict, dataclass
from typing import Optional

from .engine import evaluate_expression, expression_from_text


_NUMBER = r"\d{1,12}(?:,\d{3})*(?:\.\d{1,8})?"
_EQUATION = re.compile(
    r"(?<![\w.])(?P<left>-?"
    + _NUMBER
    + r"(?:\s*[+*/-]\s*-?"
    + _NUMBER
    + r"){1,8})\s*=\s*(?P<right>-?"
    + _NUMBER
    + r")(?![\w])"
)
_EQUATION_LIKE = re.compile(r"(?<![<>=])=(?!=)")
_REJECTED_CONTEXT = re.compile(
    r"\b(?:incorrect|wrong|false|hypothetical|suppose|imagine|"
    r"for example|e\.g\.|mistaken|claims? that)\b|"
    r"\bnot\s+(?:true|correct|valid|the case)\b",
    re.IGNORECASE,
)
_REJECTED_FOLLOWUP = re.compile(
    r"^\s*(?:(?:,|but)\s*)?(?:that|it|this)?\s*"
    r"(?:is|was|were|are|seems?)?\s*(?:not\s+)?"
    r"(?:incorrect|wrong|false|a mistake|invalid)\b",
    re.IGNORECASE,
)
_QUOTE_PAIRS = {'"': '"', "'": "'", "“": "”", "‘": "’"}


@dataclass(frozen=True)
class ReasoningAssertion:
    expression: str
    stated_result: str
    computed_result: Optional[str]
    status: str
    start: int
    end: int
    explanation: str

    def to_dict(self):
        return asdict(self)


def _is_quoted(text: str, start: int, end: int) -> bool:
    opening_quote = None
    for index, character in enumerate(text[:start]):
        if character not in _QUOTE_PAIRS:
            continue
        if (
            character == "'"
            and index > 0
            and index + 1 < len(text)
            and text[index - 1].isalnum()
            and text[index + 1].isalnum()
        ):
            continue
        if opening_quote is None:
            opening_quote = character
        elif _QUOTE_PAIRS[opening_quote] == character:
            opening_quote = None
    if opening_quote is None:
        return False
    closing_quote = _QUOTE_PAIRS[opening_quote]
    return closing_quote in text[end:]


def _is_rejected(text: str, start: int) -> bool:
    clause_start = max(
        text.rfind(mark, 0, start) for mark in ".!?;\n"
    ) + 1
    prefix = text[clause_start:start]
    if _REJECTED_CONTEXT.search(prefix[-100:]):
        return True
    clause_end_candidates = [
        index
        for mark in ".!?;\n"
        if (index := text.find(mark, start)) >= 0
    ]
    clause_end = min(clause_end_candidates, default=len(text))
    return bool(_REJECTED_FOLLOWUP.search(text[start:clause_end]))


def check_arithmetic_assertions(text: str):
    """Return supported assertion evidence, errors, and coverage statistics."""
    assertions = []
    false_assertions = []
    unsupported_count = 0
    excluded_count = 0
    covered_spans = []

    for match in _EQUATION.finditer(text):
        if _is_quoted(text, match.start(), match.end()) or _is_rejected(
            text, match.start()
        ):
            excluded_count += 1
            continue

        left = match.group("left")
        right = match.group("right")
        try:
            left_value = evaluate_expression(expression_from_text(left)).value
            right_value = evaluate_expression(expression_from_text(right)).value
        except (SyntaxError, ValueError, ZeroDivisionError):
            unsupported_count += 1
            assertions.append(
                ReasoningAssertion(
                    expression=left,
                    stated_result=right,
                    computed_result=None,
                    status="unsupported",
                    start=match.start(),
                    end=match.end(),
                    explanation="This equation uses unsupported arithmetic.",
                )
            )
            continue

        correct = left_value.equals(right_value) is True
        computed = str(left_value)
        status = "verified" if correct else "incorrect"
        assertion = ReasoningAssertion(
            expression=left,
            stated_result=right,
            computed_result=computed,
            status=status,
            start=match.start(),
            end=match.end(),
            explanation=(
                "The equation is arithmetically correct."
                if correct
                else f"The expression evaluates to {computed}, not {right}."
            ),
        )
        assertions.append(assertion)
        covered_spans.append((match.start(), match.end()))
        if not correct:
            false_assertions.append(assertion)

    for match in _EQUATION_LIKE.finditer(text):
        if any(start <= match.start() < end for start, end in covered_spans):
            continue
        if _is_quoted(text, match.start(), match.end()) or _is_rejected(
            text, match.start()
        ):
            excluded_count += 1
            continue
        clause_start = max(
            text.rfind(mark, 0, match.start()) for mark in ".!?;\n"
        ) + 1
        clause_end_candidates = [
            index
            for mark in ".!?;\n"
            if (index := text.find(mark, match.end())) >= 0
        ]
        clause_end = min(clause_end_candidates, default=len(text))
        clause = text[clause_start:clause_end]
        if re.search(r"\d|[A-Za-z_]", clause):
            unsupported_count += 1
            assertions.append(
                ReasoningAssertion(
                    expression=clause.strip(),
                    stated_result="",
                    computed_result=None,
                    status="unsupported",
                    start=match.start(),
                    end=match.end(),
                    explanation=(
                        "An equation-like claim could not be safely parsed."
                    ),
                )
            )

    return {
        "assertions": assertions,
        "false_assertions": false_assertions,
        "unsupported_count": unsupported_count,
        "excluded_count": excluded_count,
        "checked_count": sum(
            assertion.status in ("verified", "incorrect")
            for assertion in assertions
        ),
    }
