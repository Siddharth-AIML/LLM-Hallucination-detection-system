
"""TruthLens V2 unified contextual reliability orchestrator."""

import logging
from typing import Any

from contextual_audit.contextual_auditor import ContextualAuditor
from contextual_audit.context_memory import ContextMemoryAnalyzer

logger = logging.getLogger(__name__)


class ReliabilityOrchestrator:
    """Combine contextual auditing and explicit memory analysis."""

    def __init__(
        self,
        contextual_auditor: ContextualAuditor | None = None,
        memory_analyzer: ContextMemoryAnalyzer | None = None,
    ):
        self.contextual_auditor = (
            contextual_auditor or ContextualAuditor()
        )
        self.memory_analyzer = (
            memory_analyzer or ContextMemoryAnalyzer()
        )

    def audit(
        self,
        question: str,
        answer: str,
        context: str = "",
        conversation_history: str = "",
        instructions: str = "",
    ) -> dict[str, Any]:
        """Run both analyzers and combine their findings."""

        if not question or not question.strip():
            raise ValueError("The current question is required.")

        if not answer or not answer.strip():
            raise ValueError("The answer is required.")

        # Analyzer 1: four-dimensional contextual audit.
        contextual_result = self.contextual_auditor.audit(
            question=question,
            answer=answer,
            context=context,
            conversation_history=conversation_history,
            instructions=instructions,
        )

        # Analyzer 2: explicit memory extraction and consistency.
        memory_result = self.memory_analyzer.analyze(
            conversation_history=conversation_history,
            current_question=question,
            answer=answer,
            instructions=instructions,
        )

        # Collect actionable findings from both independent analyses.
        issues = []

        context_faithfulness = contextual_result.get(
            "context_faithfulness", {}
        )
        if not isinstance(context_faithfulness, dict):
            context_faithfulness = {}

        faithfulness_verdict = context_faithfulness.get("verdict")

        if faithfulness_verdict in {
            "CONTRADICTED",
            "PARTIALLY_SUPPORTED",
        }:
            issues.append({
                "source": "contextual_audit",
                "dimension": "context_faithfulness",
                "verdict": faithfulness_verdict,
                "reason": "The answer has a potential evidence "
                          "contradiction or partial-support issue.",
            })

        alignment = contextual_result.get(
            "conversation_alignment", {}
        )
        if not isinstance(alignment, dict):
            alignment = {}

        if alignment.get("verdict") == "MISALIGNED":
            issues.append({
                "source": "contextual_audit",
                "dimension": "conversation_alignment",
                "verdict": "MISALIGNED",
                "reason": alignment.get("reason", ""),
            })

        instruction_check = contextual_result.get(
            "instruction_consistency", {}
        )
        if not isinstance(instruction_check, dict):
            instruction_check = {}

        if instruction_check.get("verdict") == "INCONSISTENT":
            issues.append({
                "source": "contextual_audit",
                "dimension": "instruction_consistency",
                "verdict": "INCONSISTENT",
                "reason": instruction_check.get("reason", ""),
            })

        memory_consistency = memory_result.get(
            "answer_consistency", {}
        )
        if not isinstance(memory_consistency, dict):
            memory_consistency = {}

        memory_verdict = memory_consistency.get("verdict")

        if memory_verdict in {
            "CONFLICTED",
            "PARTIALLY_CONSISTENT",
        }:
            issues.append({
                "source": "context_memory",
                "dimension": "answer_consistency",
                "verdict": memory_verdict,
                "reason": memory_consistency.get("reason", ""),
                "conflicts": memory_consistency.get("conflicts", []),
            })

        # These are screening results, not proof that an answer is true.
        has_issues = bool(issues)

        if has_issues:
            overall_status = "issues_detected"
        elif (
            faithfulness_verdict == "NOT_ASSESSABLE"
            and alignment.get("verdict") == "NOT_ASSESSABLE"
            and instruction_check.get("verdict") == "NOT_ASSESSABLE"
            and memory_verdict == "NOT_ASSESSABLE"
        ):
            overall_status = "not_assessable"
        else:
            overall_status = "no_actionable_issues_detected"

        limitations = []

        for item in contextual_result.get("limitations", []):
            if item not in limitations:
                limitations.append(item)

        for item in memory_result.get("limitations", []):
            if item not in limitations:
                limitations.append(item)

        return {
            "status": "completed",
            "overall_status": overall_status,
            "issue_count": len(issues),
            "issues": issues,
            "original_answer": answer,
            "contextual_audit": contextual_result,
            "memory_analysis": memory_result,
            "limitations": limitations,
            "scope": "supplied_context_and_conversation_history_only",
            "mitigation_performed": False,
            "reverification_performed": False,
        }
