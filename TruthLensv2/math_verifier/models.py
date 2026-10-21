"""Validated schemas shared by math interpretation and verification."""

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


ExpressionKind = Literal[
    "number",
    "add",
    "subtract",
    "multiply",
    "divide",
    "power",
    "sqrt",
    "negate",
]


class ExpressionNode(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    kind: ExpressionKind
    value: Optional[str] = None
    unit: Optional[str] = None
    evidence: Optional[str] = None
    operands: list["ExpressionNode"] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_shape(self):
        expected_operands = {
            "number": 0,
            "add": 2,
            "subtract": 2,
            "multiply": 2,
            "divide": 2,
            "power": 2,
            "sqrt": 1,
            "negate": 1,
        }[self.kind]
        if len(self.operands) != expected_operands:
            raise ValueError(
                f"{self.kind} requires {expected_operands} operand(s)."
            )
        if self.kind == "number":
            if self.value is None or not self.evidence:
                raise ValueError(
                    "Numeric leaves require a value and question evidence."
                )
        elif self.value is not None or self.unit is not None or self.evidence:
            raise ValueError(
                "Only numeric leaves may define values, units, or evidence."
            )
        return self


class QuestionQuantity(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    value: str
    unit: str = ""
    semantic_role: str = Field(min_length=1, max_length=120)
    evidence: str = Field(min_length=1, max_length=240)


class MathInterpretation(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    status: Literal["supported", "ambiguous", "unsupported"]
    confidence: float = Field(ge=0.0, le=1.0)
    quantities: list[QuestionQuantity] = Field(max_length=32)
    expression: Optional[ExpressionNode] = None
    requested_quantity: str = Field(default="", max_length=200)
    target_unit: str = Field(default="", max_length=40)
    rounding_digits: Optional[int] = Field(default=None, ge=0, le=8)
    assumptions: list[str] = Field(default_factory=list, max_length=8)
    solution_steps: list[str] = Field(default_factory=list, max_length=12)
    reason: str = Field(default="", max_length=400)

    @model_validator(mode="after")
    def validate_status_expression(self):
        if self.status == "supported" and self.expression is None:
            raise ValueError("Supported interpretations require an expression.")
        if self.status != "supported" and self.expression is not None:
            raise ValueError(
                "Ambiguous and unsupported interpretations cannot include "
                "an executable expression."
            )
        return self


ExpressionNode.model_rebuild()
