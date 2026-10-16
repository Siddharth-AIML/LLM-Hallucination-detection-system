"""Final-answer extraction that distinguishes conclusions from reasoning."""

import re
from dataclasses import dataclass
from typing import Optional


_NUMBER = r"-?(?:\d{1,12}(?:,\d{3})*(?:\.\d{1,8})?|\d{1,12}/\d{1,12})"
_UNIT = (
    r"(?P<unit>kilometers?|kilometres?|centimeters?|centimetres?|"
    r"millimeters?|millimetres?|meters?|metres?|kilograms?|grams?|"
    r"USD|EUR|GBP|km|cm|mm|kg|g|lbs?|ft|in|m|L|ml|"
    r"hours?|hrs?|minutes?|mins?|seconds?|secs?|days?|dollars?|"
    r"euros?|pounds?|apples?|chocolates?|cookies?|boxes?|bags?|"
    r"friends?|students?|items?|percent|%)?(?=$|[\s.,!?;])"
)
@dataclass(frozen=True)
class AnswerExtraction:
    value: Optional[str]
    unit: Optional[str]
    source: Optional[str]
    ambiguous: bool
    candidates: tuple[str, ...] = ()


def _matches(pattern: str, text: str):
    return [
        (match, match.group("value"), match.group("unit") or match.group("currency"))
        for match in re.finditer(pattern, text, re.IGNORECASE)
    ]


def _select(candidates, source: str) -> AnswerExtraction:
    unique = []
    for _, value, unit in candidates:
        normalized = (value.replace(",", ""), (unit or "").casefold())
        if normalized not in unique:
            unique.append(normalized)
    if len(unique) > 1:
        return AnswerExtraction(
            value=None,
            unit=None,
            source=source,
            ambiguous=True,
            candidates=tuple(value for value, _ in unique),
        )
    value, unit = unique[0]
    return AnswerExtraction(value, unit or None, source, False, (value,))


def extract_final_answer(text: str) -> AnswerExtraction:
    patterns = (
        (
            "gsm8k_marker",
            r"####\s*(?P<currency>[$€£])?\s*(?P<value>" + _NUMBER + r")\s*" + _UNIT,
        ),
        (
            "final_label",
            r"\bfinal\s+(?:numeric\s+)?answer\s*(?:is|:|=)?\s*"
            r"(?P<currency>[$€£])?\s*(?P<value>"
            + _NUMBER
            + r")\s*"
            + _UNIT,
        ),
        (
            "conclusion",
            r"\b(?:therefore|thus|hence|so|in conclusion)\b"
            r"[^.!?\n]{0,100}?(?:answer|result|total|there (?:are|is)|"
            r"contains?)?[^.!?\n]{0,40}?(?P<currency>[$€£])?\s*"
            r"(?P<value>"
            + _NUMBER
            + r")\s*"
            + _UNIT,
        ),
        (
            "answer_label",
            r"\b(?:the\s+)?(?:answer|result|total)\s*(?:is|:|=)\s*"
            r"(?P<currency>[$€£])?\s*(?P<value>"
            + _NUMBER
            + r")\s*"
            + _UNIT,
        ),
    )
    for source, pattern in patterns:
        candidates = _matches(pattern, text)
        if candidates:
            return _select(candidates, source)

    sentences = re.split(r"(?<=[.!?])\s+|\n+", text.strip())
    if sentences and sentences[-1]:
        candidates = _matches(
            r"(?P<currency>[$€£])?\s*(?P<value>"
            + _NUMBER
            + r")\s*"
            + _UNIT
            + r"\s*[.!?]?\s*$",
            sentences[-1],
        )
        if candidates:
            return _select(candidates, "final_sentence")

    return AnswerExtraction(None, None, None, False)


def extract_numeric_answer(text: str):
    """Compatibility helper for consumers needing only the candidate value."""
    result = extract_final_answer(text)
    return None if result.ambiguous else result.value
