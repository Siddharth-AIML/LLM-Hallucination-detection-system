"""
=========================================================
TruthLens V2

Topic Validator

Validates Topics before they are stored inside the
Knowledge Base.

Author : Siddharth Metkari
=========================================================
"""

from typing import Dict

from knowledge_base.topic_schema import Topic


class TopicValidator:

    """
    Validates Topic objects before insertion into
    the Knowledge Base.
    """

    def __init__(self):

        self.MIN_TOPIC_NAME_LENGTH = 3

        self.MIN_SUMMARY_LENGTH = 30

        self.MIN_EVIDENCE_COUNT = 3

        self.MIN_ENTITY_COUNT = 2

        self.MIN_KEYWORD_COUNT = 3

        self.MIN_SOURCE_RELIABILITY = 0.60

        self.MIN_EMBEDDING_DIMENSION = 384


    # =====================================================
    # Main Validation Function
    # =====================================================

    def validate(self, topic: Topic) -> Dict:

        report = {

            "is_valid": True,

            "errors": [],

            "warnings": []

        }

        self._validate_topic_name(topic, report)

        self._validate_summary(topic, report)

        self._validate_entities(topic, report)

        self._validate_keywords(topic, report)

        self._validate_evidence(topic, report)

        self._validate_sources(topic, report)

        self._validate_embedding(topic, report)

        self._validate_years(topic, report)

        self._validate_duplicates(topic, report)

        if len(report["errors"]) > 0:

            report["is_valid"] = False

        return report


    # =====================================================
    # Topic Name
    # =====================================================

    def _validate_topic_name(

        self,

        topic: Topic,

        report: Dict

    ):

        if len(topic.topic_name.strip()) < self.MIN_TOPIC_NAME_LENGTH:

            report["errors"].append(

                "Topic name is too short."

            )


    # =====================================================
    # Summary
    # =====================================================

    def _validate_summary(

        self,

        topic: Topic,

        report: Dict

    ):

        if len(topic.summary.strip()) < self.MIN_SUMMARY_LENGTH:

            report["errors"].append(

                "Summary is too short."

            )


    # =====================================================
    # Entities
    # =====================================================

    def _validate_entities(

        self,

        topic: Topic,

        report: Dict

    ):

        if len(topic.entities) < self.MIN_ENTITY_COUNT:

            report["warnings"].append(

                "Very few entities detected."

            )


    # =====================================================
    # Keywords
    # =====================================================

    def _validate_keywords(

        self,

        topic: Topic,

        report: Dict

    ):

        if len(topic.keywords) < self.MIN_KEYWORD_COUNT:

            report["warnings"].append(

                "Very few keywords detected."

            )


    # =====================================================
    # Evidence
    # =====================================================

    def _validate_evidence(

        self,

        topic: Topic,

        report: Dict

    ):

        if len(topic.evidence) < self.MIN_EVIDENCE_COUNT:

            report["errors"].append(

                "Not enough evidence."

            )


    # =====================================================
    # Sources
    # =====================================================

    def _validate_sources(

        self,

        topic: Topic,

        report: Dict

    ):

        if len(topic.sources) == 0:

            report["errors"].append(

                "No sources available."

            )

            return

        reliable = [

            source

            for source in topic.sources

            if source.reliability_score >=

            self.MIN_SOURCE_RELIABILITY

        ]

        if len(reliable) == 0:

            report["errors"].append(

                "No trusted sources found."

            )


    # =====================================================
    # Embedding
    # =====================================================

    def _validate_embedding(

        self,

        topic: Topic,

        report: Dict

    ):

        if len(topic.topic_embedding) != self.MIN_EMBEDDING_DIMENSION:

            report["errors"].append(

                "Embedding dimension mismatch."

            )


    # =====================================================
    # Years
    # =====================================================

    def _validate_years(

        self,

        topic: Topic,

        report: Dict

    ):

        if len(topic.years) == 0:

            report["warnings"].append(

                "No year information found."

            )


    # =====================================================
    # Duplicate Values
    # =====================================================

    def _validate_duplicates(

        self,

        topic: Topic,

        report: Dict

    ):

        if len(topic.entities) != len(set(topic.entities)):

            report["warnings"].append(

                "Duplicate entities found."

            )

        if len(topic.keywords) != len(set(topic.keywords)):

            report["warnings"].append(

                "Duplicate keywords found."

            )

        evidence_text = [

            e.text

            for e in topic.evidence

        ]

        if len(evidence_text) != len(set(evidence_text)):

            report["warnings"].append(

                "Duplicate evidence found."

            )


    # =====================================================
    # Print Validation Report
    # =====================================================

    def print_report(

        self,

        report: Dict

    ):

        print("\n========== Topic Validation ==========")

        print(

            "Status :",

            "PASSED" if report["is_valid"]

            else "FAILED"

        )

        if report["errors"]:

            print("\nErrors:")

            for e in report["errors"]:

                print("•", e)

        if report["warnings"]:

            print("\nWarnings:")

            for w in report["warnings"]:

                print("•", w)

        print("======================================\n")