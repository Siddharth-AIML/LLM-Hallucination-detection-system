"""
=========================================================
TruthLens V2

Topic Schema

This file defines the complete structure of every Topic
stored inside the Knowledge Base.

Every module in TruthLens V2 will use this schema.

Author : Siddharth Metkari
=========================================================
"""

from dataclasses import dataclass, field, asdict
from typing import List
from datetime import datetime


# =========================================================
# Source Schema
# =========================================================

@dataclass
class Source:
    """
    Stores information about every source from which
    evidence was collected.
    """

    publisher: str
    title: str
    url: str
    published_date: str

    reliability_score: float = 0.0


# =========================================================
# Evidence Schema
# =========================================================

@dataclass
class Evidence:
    """
    Stores every evidence sentence together with
    its metadata.
    """

    text: str

    source: str

    url: str

    published_date: str

    retrieval_score: float = 0.0


# =========================================================
# Topic Schema
# =========================================================

@dataclass
class Topic:
    """
    Represents one Topic inside the Knowledge Base.
    """

    # =====================================================
    # Basic Information
    # =====================================================

    topic_id: str

    topic_name: str

    topic_category: str

    summary: str


    # =====================================================
    # Metadata
    # =====================================================

    years: List[int] = field(default_factory=list)

    entities: List[str] = field(default_factory=list)

    keywords: List[str] = field(default_factory=list)

    semantic_tags: List[str] = field(default_factory=list)


    # =====================================================
    # Evidence & Sources
    # =====================================================

    evidence: List[Evidence] = field(default_factory=list)

    sources: List[Source] = field(default_factory=list)


    # =====================================================
    # Embedding
    # =====================================================

    topic_embedding: List[float] = field(default_factory=list)


    # =====================================================
    # Knowledge Quality
    # =====================================================

    source_reliability: float = 0.0

    evidence_count: int = 0

    trusted_source_count: int = 0

    average_retrieval_confidence: float = 0.0

    summary_confidence: float = 0.0


    # =====================================================
    # Status
    # =====================================================

    status: str = "ACTIVE"


    # =====================================================
    # Version Control
    # =====================================================

    version: int = 1

    created_at: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )

    last_updated: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )


    # =====================================================
    # Analytics
    # =====================================================

    retrieval_count: int = 0

    verification_count: int = 0

    last_verified: str = ""


    # =====================================================
    # Utility Methods
    # =====================================================

    def update_timestamp(self):
        """
        Updates last modified time.
        """
        self.last_updated = datetime.now().isoformat()


    def increment_version(self):
        """
        Increments topic version after update.
        """
        self.version += 1
        self.update_timestamp()


    def add_evidence(self, evidence: Evidence):
        """
        Adds new evidence if not already present.
        """

        existing = [e.text for e in self.evidence]

        if evidence.text not in existing:

            self.evidence.append(evidence)

            self.evidence_count = len(self.evidence)

            self.update_timestamp()


    def add_source(self, source: Source):
        """
        Adds new source.
        """

        urls = [s.url for s in self.sources]

        if source.url not in urls:

            self.sources.append(source)

            self.trusted_source_count = len(
                [
                    s for s in self.sources
                    if s.reliability_score >= 0.80
                ]
            )

            self.update_timestamp()


    def update_embedding(self, embedding):
        """
        Stores latest topic embedding.
        """

        self.topic_embedding = embedding

        self.update_timestamp()


    def increment_retrieval(self):
        """
        Updates retrieval analytics.
        """

        self.retrieval_count += 1


    def increment_verification(self):
        """
        Updates verification analytics.
        """

        self.verification_count += 1

        self.last_verified = datetime.now().isoformat()


    def to_dict(self):
        """
        Converts Topic object to dictionary.
        """

        return asdict(self)