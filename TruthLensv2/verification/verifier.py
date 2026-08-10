"""
TruthLens V2 - Verification Engine V1

The verifier combines deterministic evidence checks with
LLM semantic analysis. The LLM does not directly decide
the final TruthLens verdict.
"""

import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from groq import Groq


SUPPORTED = "SUPPORTED"
CONTRADICTED = "CONTRADICTED"
PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
INSUFFICIENT_INFORMATION = "INSUFFICIENT_INFORMATION"

MODEL_NAME = "llama-3.3-70b-versatile"

MAX_EVIDENCE = 8
MIN_EVIDENCE = 2
MIN_RELIABILITY = 0.50
MIN_COVERAGE = 0.20
MIN_ENTITY = 0.50


@dataclass
class VerificationResult:
    """Structured output of the verification engine."""

    claim: str
    verdict: str
    confidence: float
    explanation: str

    supporting_evidence: List[Any] = field(
        default_factory=list
    )

    contradicting_evidence: List[Any] = field(
        default_factory=list
    )

    retrieved_topics: List[str] = field(
        default_factory=list
    )

    retrieval_confidence: float = 0.0
    verifier_confidence: float = 0.0

    deterministic_signals: Dict[str, float] = field(
        default_factory=dict
    )

    llm_relation: str = "NEUTRAL"

    created_at: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )

    def to_dict(self):
        """Convert the result to a JSON-compatible dictionary."""

        return {
            "claim": self.claim,
            "verdict": self.verdict,
            "confidence": self.confidence,
            "explanation": self.explanation,
            "supporting_evidence": [
                self._object_to_dict(item)
                for item in self.supporting_evidence
            ],
            "contradicting_evidence": [
                self._object_to_dict(item)
                for item in self.contradicting_evidence
            ],
            "retrieved_topics": self.retrieved_topics,
            "retrieval_confidence": self.retrieval_confidence,
            "verifier_confidence": self.verifier_confidence,
            "deterministic_signals": self.deterministic_signals,
            "llm_relation": self.llm_relation,
            "created_at": self.created_at,
        }

    @staticmethod
    def _object_to_dict(value):
        if isinstance(value, dict):
            return value

        if hasattr(value, "__dict__"):
            return dict(value.__dict__)

        return {"text": str(value)}


class Verifier:
    """
    TruthLens V1 verifier.

    Final verdict logic belongs to this class. Groq is used
    only for semantic claim-evidence analysis.
    """

    def __init__(
        self,
        groq_client: Optional[Groq] = None
    ):
        print("Loading Verification Engine...")

        load_dotenv()

        api_key = os.getenv("GROQ_API_KEY")

        if groq_client is not None:
            self.client = groq_client

        else:
            if not api_key:
                raise ValueError(
                    "GROQ_API_KEY not found in .env file."
                )

            self.client = Groq(
                api_key=api_key
            )

        self.model_name = MODEL_NAME

        print("Verification Engine Ready.\n")

    # =====================================================
    # Main Verification
    # =====================================================

    def verify(
        self,
        claim: str,
        retrieval_result: Dict[str, Any]
    ) -> VerificationResult:
        """
        Verify one claim against HybridRetriever output.
        """

        if not claim or not claim.strip():
            return VerificationResult(
                claim=claim,
                verdict=INSUFFICIENT_INFORMATION,
                confidence=0.0,
                explanation="No claim was provided."
            )

        if retrieval_result.get("status") == (
            INSUFFICIENT_INFORMATION
        ):
            return VerificationResult(
                claim=claim,
                verdict=INSUFFICIENT_INFORMATION,
                confidence=0.0,
                explanation=(
                    "The Knowledge Base does not contain "
                    "sufficient evidence for this claim."
                )
            )

        candidates = retrieval_result.get(
            "results",
            []
        )

        evidence_items = self.collect_evidence(
            candidates
        )

        if len(evidence_items) < MIN_EVIDENCE:
            return VerificationResult(
                claim=claim,
                verdict=INSUFFICIENT_INFORMATION,
                confidence=0.0,
                explanation=(
                    "The retrieved results do not contain "
                    "enough evidence for verification."
                ),
                retrieved_topics=[
                    self.topic_name(item)
                    for item in candidates
                ]
            )

        signals = self.calculate_signals(
            claim,
            candidates,
            evidence_items
        )

        llm_analysis = self.analyze_with_llm(
            claim,
            evidence_items
        )

        verdict = self.fuse_verification(
            signals,
            llm_analysis,
            evidence_items
        )

        verifier_confidence = (
            self.calculate_verifier_confidence(
                signals,
                llm_analysis,
                verdict
            )
        )

        retrieval_confidence = (
            self.get_retrieval_confidence(
                candidates
            )
        )

        final_confidence = min(
            retrieval_confidence,
            verifier_confidence
        )

        if verdict == INSUFFICIENT_INFORMATION:
            final_confidence = min(
                final_confidence,
                0.49
            )

        explanation = self.build_explanation(
            verdict,
            llm_analysis
        )

        return VerificationResult(
            claim=claim,
            verdict=verdict,
            confidence=round(
                final_confidence,
                4
            ),
            explanation=explanation,
            supporting_evidence=(
                self.select_supporting_evidence(
                    evidence_items,
                    llm_analysis
                )
            ),
            contradicting_evidence=(
                self.select_contradicting_evidence(
                    evidence_items,
                    llm_analysis
                )
            ),
            retrieved_topics=[
                self.topic_name(item)
                for item in candidates
            ],
            retrieval_confidence=(
                retrieval_confidence
            ),
            verifier_confidence=(
                verifier_confidence
            ),
            deterministic_signals=signals,
            llm_relation=llm_analysis.get(
                "relation",
                "NEUTRAL"
            )
        )

    # =====================================================
    # Evidence Collection
    # =====================================================

    def collect_evidence(
        self,
        candidates: List[Any]
    ) -> List[Dict[str, Any]]:
        """Collect unique evidence from retrieved topics."""

        collected = []
        seen = set()

        for candidate in candidates:
            evidence_list = getattr(
                candidate,
                "evidence",
                []
            )

            for evidence in evidence_list:
                text = self.evidence_text(
                    evidence
                )

                normalized = self.normalize_text(
                    text
                )

                if not normalized:
                    continue

                if normalized in seen:
                    continue

                seen.add(normalized)

                collected.append({
                    "evidence": evidence,
                    "candidate": candidate
                })

                if len(collected) >= MAX_EVIDENCE:
                    return collected

        return collected

    # =====================================================
    # Deterministic Signals
    # =====================================================

    def calculate_signals(
        self,
        claim: str,
        candidates: List[Any],
        evidence_items: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Calculate transparent deterministic signals."""

        return {
            "entity_consistency": round(
                self.entity_consistency(
                    claim,
                    candidates
                ),
                4
            ),
            "keyword_consistency": round(
                self.keyword_consistency(
                    claim,
                    evidence_items
                ),
                4
            ),
            "temporal_consistency": round(
                self.temporal_consistency(
                    claim,
                    evidence_items
                ),
                4
            ),
            "evidence_coverage": round(
                self.evidence_coverage(
                    claim,
                    evidence_items
                ),
                4
            ),
            "source_reliability": round(
                self.source_reliability(
                    candidates
                ),
                4
            ),
            "evidence_agreement": round(
                self.evidence_agreement(
                    evidence_items
                ),
                4
            ),
            "evidence_count": round(
                min(
                    len(evidence_items) / 5.0,
                    1.0
                ),
                4
            )
        }

    def entity_consistency(
        self,
        claim: str,
        candidates: List[Any]
    ) -> float:
        """
        Compare capitalized/entity-like terms in the claim
        with the entities stored in retrieved topics.
        """

        claim_entities = self.entity_like_terms(
            claim
        )

        if not claim_entities:
            return 0.5

        topic_entities = set()

        for candidate in candidates:
            topic = getattr(
                candidate,
                "topic",
                candidate
            )

            for entity in getattr(
                topic,
                "entities",
                []
            ):
                topic_entities.add(
                    self.normalize_text(entity)
                )

        if not topic_entities:
            return 0.0

        matches = 0

        for entity in claim_entities:
            if entity in topic_entities:
                matches += 1
                continue

            for candidate_entity in topic_entities:
                if (
                    entity in candidate_entity
                    or candidate_entity in entity
                ):
                    matches += 1
                    break

        return matches / len(claim_entities)

    def keyword_consistency(
        self,
        claim: str,
        evidence_items: List[Dict[str, Any]]
    ) -> float:
        """Measure lexical overlap with retrieved evidence."""

        claim_tokens = set(
            self.tokens(claim)
        )

        if not claim_tokens:
            return 0.0

        evidence_tokens = set()

        for item in evidence_items:
            evidence_tokens.update(
                self.tokens(
                    self.evidence_text(
                        item["evidence"]
                    )
                )
            )

        overlap = claim_tokens.intersection(
            evidence_tokens
        )

        return min(
            len(overlap) / len(claim_tokens),
            1.0
        )

    def temporal_consistency(
        self,
        claim: str,
        evidence_items: List[Dict[str, Any]]
    ) -> float:
        """
        If the claim explicitly contains a year, check whether
        the evidence contains that year.
        """

        claim_years = self.years(claim)

        if not claim_years:
            return 1.0

        evidence_years = set()

        for item in evidence_items:
            evidence = item["evidence"]

            evidence_years.update(
                self.years(
                    self.evidence_text(
                        evidence
                    )
                )
            )

            evidence_years.update(
                self.years(
                    str(
                        getattr(
                            evidence,
                            "published_date",
                            ""
                        )
                    )
                )
            )

        if not evidence_years:
            return 0.0

        return len(
            set(claim_years).intersection(
                evidence_years
            )
        ) / len(
            set(claim_years)
        )

    def evidence_coverage(
        self,
        claim: str,
        evidence_items: List[Dict[str, Any]]
    ) -> float:
        """Measure how much claim vocabulary is represented."""

        claim_tokens = set(
            self.tokens(claim)
        )

        if not claim_tokens:
            return 0.0

        evidence_tokens = set()

        for item in evidence_items:
            evidence_tokens.update(
                self.tokens(
                    self.evidence_text(
                        item["evidence"]
                    )
                )
            )

        return min(
            len(
                claim_tokens.intersection(
                    evidence_tokens
                )
            ) / len(claim_tokens),
            1.0
        )

    def source_reliability(
        self,
        candidates: List[Any]
    ) -> float:
        """Use reliability already stored in the Knowledge Base."""

        scores = []

        for candidate in candidates:
            topic = getattr(
                candidate,
                "topic",
                candidate
            )

            value = getattr(
                topic,
                "source_reliability",
                0.0
            )

            try:
                value = float(value)
            except (TypeError, ValueError):
                value = 0.0

            if value > 0:
                scores.append(
                    min(
                        max(value, 0.0),
                        1.0
                    )
                )

        if not scores:
            return 0.0

        return sum(scores) / len(scores)

    def evidence_agreement(
        self,
        evidence_items: List[Dict[str, Any]]
    ) -> float:
        """
        Lightweight lexical agreement signal.

        This is not treated as proof of truth.
        """

        if len(evidence_items) < 2:
            return 0.0

        sets = []

        for item in evidence_items:
            token_set = set(
                self.tokens(
                    self.evidence_text(
                        item["evidence"]
                    )
                )
            )

            if token_set:
                sets.append(token_set)

        if len(sets) < 2:
            return 0.0

        base = sets[0]
        values = []

        for other in sets[1:]:
            union = base.union(other)

            if not union:
                continue

            values.append(
                len(
                    base.intersection(other)
                ) / len(union)
            )

        if not values:
            return 0.0

        return sum(values) / len(values)

    # =====================================================
    # LLM Semantic Analysis
    # =====================================================

    def analyze_with_llm(
        self,
        claim: str,
        evidence_items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Ask Groq only for semantic relation.

        It cannot return the final TruthLens verdict.
        """

        evidence_text = ""

        for index, item in enumerate(
            evidence_items,
            start=1
        ):
            evidence = item["evidence"]

            evidence_text += (
                f"\nEVIDENCE {index}:\n"
            )

            evidence_text += (
                self.evidence_text(
                    evidence
                )
            )

            source = getattr(
                evidence,
                "source",
                ""
            )

            if source:
                evidence_text += (
                    f"\nSource: {source}"
                )

            evidence_text += "\n"

        prompt = f"""
You are the semantic evidence analyst for TruthLens.

Do NOT decide the final TruthLens verdict.

Analyze only whether the supplied evidence semantically
supports, contradicts, or fails to establish the claim.

CLAIM:
{claim}

EVIDENCE:
{evidence_text}

Return ONLY valid JSON:

{{
    "relation": "SUPPORT",
    "confidence": 0.0,
    "supported_aspects": [],
    "contradicted_aspects": [],
    "unresolved_aspects": [],
    "reason": ""
}}

Allowed relation values:
SUPPORT
CONTRADICT
NEUTRAL
MIXED

Rules:
1. Use only the supplied evidence.
2. Do not use outside knowledge.
3. Do not treat missing evidence as support.
4. SUPPORT requires meaningful evidence for the claim.
5. CONTRADICT requires meaningful conflict with the claim.
6. MIXED means important parts support and conflict.
7. NEUTRAL means the evidence is relevant but does not
   establish the claim.
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a strict evidence "
                            "analysis component."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0
            )

            text = response.choices[0].message.content

            return self.parse_llm_json(
                text
            )

        except Exception as exc:
            return {
                "relation": "NEUTRAL",
                "confidence": 0.0,
                "supported_aspects": [],
                "contradicted_aspects": [],
                "unresolved_aspects": [],
                "reason": (
                    "Semantic analysis failed: "
                    f"{exc}"
                )
            }

    def parse_llm_json(
        self,
        text: str
    ) -> Dict[str, Any]:
        """Parse and sanitize Groq JSON output."""

        cleaned = text.strip()

        cleaned = cleaned.replace(
            "```json",
            ""
        )

        cleaned = cleaned.replace(
            "```",
            ""
        )

        data = json.loads(
            cleaned.strip()
        )

        relation = str(
            data.get(
                "relation",
                "NEUTRAL"
            )
        ).upper()

        if relation not in {
            "SUPPORT",
            "CONTRADICT",
            "NEUTRAL",
            "MIXED"
        }:
            relation = "NEUTRAL"

        try:
            confidence = float(
                data.get(
                    "confidence",
                    0.0
                )
            )
        except (TypeError, ValueError):
            confidence = 0.0

        return {
            "relation": relation,
            "confidence": min(
                max(confidence, 0.0),
                1.0
            ),
            "supported_aspects": data.get(
                "supported_aspects",
                []
            ),
            "contradicted_aspects": data.get(
                "contradicted_aspects",
                []
            ),
            "unresolved_aspects": data.get(
                "unresolved_aspects",
                []
            ),
            "reason": str(
                data.get(
                    "reason",
                    ""
                )
            )
        }

    # =====================================================
    # Fusion Logic
    # =====================================================

    def fuse_verification(
        self,
        signals: Dict[str, float],
        llm_analysis: Dict[str, Any],
        evidence_items: List[Dict[str, Any]]
    ) -> str:
        """
        Rule-based fusion.

        We deliberately do not use arbitrary weighted scores
        to determine the verdict.
        """

        if len(evidence_items) < MIN_EVIDENCE:
            return INSUFFICIENT_INFORMATION

        coverage = signals.get(
            "evidence_coverage",
            0.0
        )

        entity = signals.get(
            "entity_consistency",
            0.0
        )

        reliability = signals.get(
            "source_reliability",
            0.0
        )

        relation = str(
            llm_analysis.get(
                "relation",
                "NEUTRAL"
            )
        ).upper()

        llm_confidence = float(
            llm_analysis.get(
                "confidence",
                0.0
            )
        )

        enough_context = (
            coverage >= MIN_COVERAGE
            or entity >= MIN_ENTITY
        )

        if not enough_context:
            return INSUFFICIENT_INFORMATION

        if (
            reliability < MIN_RELIABILITY
            and len(evidence_items) < 3
        ):
            return INSUFFICIENT_INFORMATION

        if (
            relation == "CONTRADICT"
            and llm_confidence >= 0.60
        ):
            return CONTRADICTED

        if (
            relation == "MIXED"
            and llm_confidence >= 0.60
        ):
            return PARTIALLY_SUPPORTED

        if (
            relation == "SUPPORT"
            and llm_confidence >= 0.60
        ):
            return SUPPORTED

        return INSUFFICIENT_INFORMATION

    # =====================================================
    # Confidence
    # =====================================================

    def calculate_verifier_confidence(
        self,
        signals: Dict[str, float],
        llm_analysis: Dict[str, Any],
        verdict: str
    ) -> float:
        """
        Confidence is a reporting signal in V1.
        It does not determine the verdict.
        """

        values = [
            signals.get(
                "evidence_coverage",
                0.0
            ),
            signals.get(
                "source_reliability",
                0.0
            ),
            signals.get(
                "evidence_agreement",
                0.0
            ),
            signals.get(
                "entity_consistency",
                0.0
            )
        ]

        deterministic = sum(values) / len(values)

        llm = float(
            llm_analysis.get(
                "confidence",
                0.0
            )
        )

        confidence = (
            deterministic + llm
        ) / 2.0

        if verdict == INSUFFICIENT_INFORMATION:
            confidence *= 0.5

        return round(
            min(
                max(confidence, 0.0),
                1.0
            ),
            4
        )

    # =====================================================
    # Evidence Selection
    # =====================================================

    def select_supporting_evidence(
        self,
        evidence_items: List[Dict[str, Any]],
        llm_analysis: Dict[str, Any]
    ) -> List[Any]:
        relation = llm_analysis.get(
            "relation",
            "NEUTRAL"
        )

        if relation not in {
            "SUPPORT",
            "MIXED"
        }:
            return []

        return [
            item["evidence"]
            for item in evidence_items
        ]

    def select_contradicting_evidence(
        self,
        evidence_items: List[Dict[str, Any]],
        llm_analysis: Dict[str, Any]
    ) -> List[Any]:
        relation = llm_analysis.get(
            "relation",
            "NEUTRAL"
        )

        if relation not in {
            "CONTRADICT",
            "MIXED"
        }:
            return []

        return [
            item["evidence"]
            for item in evidence_items
        ]

    # =====================================================
    # Explanation
    # =====================================================

    def build_explanation(
        self,
        verdict: str,
        llm_analysis: Dict[str, Any]
    ) -> str:
        """Build a transparent human-readable explanation."""

        reason = str(
            llm_analysis.get(
                "reason",
                ""
            )
        ).strip()

        if verdict == SUPPORTED:
            base = (
                "The retrieved evidence provides sufficient "
                "support for the claim."
            )

        elif verdict == CONTRADICTED:
            base = (
                "The retrieved evidence contains information "
                "that conflicts with the claim."
            )

        elif verdict == PARTIALLY_SUPPORTED:
            base = (
                "The retrieved evidence supports some aspects "
                "of the claim but not the claim as a whole."
            )

        else:
            base = (
                "The available evidence is not sufficient "
                "to verify the claim."
            )

        if reason:
            return f"{base} {reason}"

        return base

    # =====================================================
    # Retrieval Helpers
    # =====================================================

    def get_retrieval_confidence(
        self,
        candidates: List[Any]
    ) -> float:
        """Read and conservatively normalize top hybrid score."""

        if not candidates:
            return 0.0

        score = getattr(
            candidates[0],
            "hybrid_score",
            0.0
        )

        try:
            score = float(score)
        except (TypeError, ValueError):
            score = 0.0

        return round(
            min(
                max(score, 0.0),
                1.0
            ),
            4
        )

    def topic_name(
        self,
        candidate: Any
    ) -> str:
        topic = getattr(
            candidate,
            "topic",
            candidate
        )

        return str(
            getattr(
                topic,
                "topic_name",
                "Unknown Topic"
            )
        )

    def evidence_text(
        self,
        evidence: Any
    ) -> str:
        if isinstance(
            evidence,
            dict
        ):
            return str(
                evidence.get(
                    "text",
                    ""
                )
            ).strip()

        return str(
            getattr(
                evidence,
                "text",
                ""
            )
        ).strip()

    # =====================================================
    # Text Utilities
    # =====================================================

    def normalize_text(
        self,
        text: str
    ) -> str:
        text = text.lower()

        text = re.sub(
            r"[^a-z0-9\s]",
            " ",
            text
        )

        text = re.sub(
            r"\s+",
            " ",
            text
        )

        return text.strip()

    def tokens(
        self,
        text: str
    ) -> List[str]:
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were",
            "be", "been", "being", "to", "of", "in", "on",
            "for", "and", "or", "as", "at", "by", "from",
            "with", "that", "this", "it", "has", "have",
            "had", "can", "could", "will", "would", "should",
            "may", "might", "into", "about"
        }

        return [
            token
            for token in self.normalize_text(text).split()
            if len(token) > 2
            and token not in stop_words
        ]

    def entity_like_terms(
        self,
        claim: str
    ) -> List[str]:
        """
        Lightweight entity matching.

        ClaimProcessor remains the authoritative entity
        extraction module.
        """

        result = []

        for token in claim.split():
            cleaned = re.sub(
                r"[^A-Za-z0-9]",
                "",
                token
            )

            if not cleaned:
                continue

            if (
                token[:1].isupper()
                or any(
                    char.isdigit()
                    for char in cleaned
                )
            ):
                result.append(
                    self.normalize_text(
                        cleaned
                    )
                )

        return sorted(
            set(
                item
                for item in result
                if item
            )
        )

    def years(
        self,
        text: str
    ) -> List[int]:
        matches = re.findall(
            r"\b(?:19|20|21)\d{2}\b",
            text
        )

        return sorted(
            set(
                int(year)
                for year in matches
            )
        )

    # =====================================================
    # Output
    # =====================================================

    def print_result(
        self,
        result: VerificationResult
    ):
        print()
        print("=" * 60)
        print("TruthLens Verification Result")
        print("=" * 60)

        print(
            f"Claim      : {result.claim}"
        )

        print(
            f"Verdict    : {result.verdict}"
        )

        print(
            f"Confidence : {result.confidence:.4f}"
        )

        print(
            f"LLM Relation : {result.llm_relation}"
        )

        print()
        print("Deterministic Signals")
        print("-" * 60)

        for name, value in (
            result.deterministic_signals.items()
        ):
            print(
                f"{name:<25}: {value:.4f}"
            )

        print()
        print("Retrieved Topics")
        print("-" * 60)

        for topic in result.retrieved_topics:
            print(
                f"- {topic}"
            )

        print()
        print("Explanation")
        print("-" * 60)
        print(
            result.explanation
        )
        print()
        print("=" * 60)

    def print_json(
        self,
        result: VerificationResult
    ):
        print(
            json.dumps(
                result.to_dict(),
                indent=4,
                ensure_ascii=False
            )
        )


if __name__ == "__main__":

    from claim_processing.claim_processor import (
        ClaimProcessor
    )

    from retrieval.hybrid_retrieval import (
        HybridRetriever
    )

    print()
    print("=" * 60)
    print("TruthLens Verification Test")
    print("=" * 60)

    processor = ClaimProcessor()

    retriever = HybridRetriever()

    retriever.build_faiss_index()

    retriever.build_bm25_index()

    verifier = Verifier()

    print()
    print("=" * 60)
    print("Enter a claim to verify.")
    print("Type 'exit' to stop.")
    print("=" * 60)

    while True:

        claim = input(
            "\nEnter Claim (or 'exit'): "
        ).strip()

        if claim.lower() == "exit":
            break

        if not claim:
            continue


        retrieval_result = (
            retriever.retrieve(
                claim
            )
        )

        result = verifier.verify(
            claim,
            retrieval_result
        )

        verifier.print_result(
            result
        )
