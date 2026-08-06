"""
=========================================================
TruthLens V2

Hybrid Retrieval Engine

Performs Hybrid Retrieval using

1. Semantic Search (FAISS)
2. Keyword Search (BM25)

Input

ProcessedClaim

Output

RetrievedEvidence

If sufficient evidence is unavailable,
returns INSUFFICIENT_INFORMATION and
queues the topic for future knowledge expansion.

Author:
Siddharth Metkari
=========================================================
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any

import faiss
import numpy as np

from rank_bm25 import BM25Okapi

from sentence_transformers import SentenceTransformer

from claim_processing.claim_processor import (
    ProcessedClaim
)

from knowledge_base.topic_schema import (
    Topic,
    Evidence
)


# =========================================================
# Paths
# =========================================================

ROOT_DIR = Path(__file__).resolve().parent.parent

KNOWLEDGE_BASE_PATH = (
    ROOT_DIR
    / "data"
    / "knowledge_base.json"
)


# =========================================================
# Retrieval Status
# =========================================================

SUCCESS = "SUCCESS"

INSUFFICIENT_INFORMATION = (
    "INSUFFICIENT_INFORMATION"
)


# =========================================================
# Retrieved Evidence Schema
# =========================================================

@dataclass
class RetrievedEvidence:

    topic: Topic

    semantic_score: float

    keyword_score: float

    hybrid_score: float

    matched_text: str

    evidence: List[Evidence]

    source_type: str = "knowledge_base"


# =========================================================
# Hybrid Retriever
# =========================================================

class HybridRetriever:

    """
    Retrieves relevant evidence from the
    Knowledge Base using Hybrid Retrieval.

    Hybrid Retrieval =
        Semantic Search
        +
        BM25 Keyword Search
    """

    def __init__(

        self,

        embedding_model_name: str = (
            "sentence-transformers/all-MiniLM-L6-v2"
        )

    ):

        print()

        print(
            "Loading Hybrid Retriever..."
        )

        # -----------------------------------------
        # Embedding Model
        # -----------------------------------------

        self.embedding_model = (
            SentenceTransformer(
                embedding_model_name
            )
        )

        # -----------------------------------------
        # Knowledge Base
        # -----------------------------------------

        self.topics: List[Topic] = []

        # -----------------------------------------
        # Search Documents
        # -----------------------------------------

        self.search_documents: List[str] = []

        self.topic_lookup: Dict[int, Topic] = {}

        # -----------------------------------------
        # BM25
        # -----------------------------------------

        self.tokenized_documents = []

        self.bm25 = None

        # -----------------------------------------
        # FAISS
        # -----------------------------------------

        self.document_embeddings = None

        self.faiss_index = None

        # -----------------------------------------
        # Load Everything
        # -----------------------------------------

        self.load_knowledge_base()

        self.prepare_search_corpus()

        print(
            "Hybrid Retriever Ready.\n"
        )

    # =====================================================
    # Load Knowledge Base
    # =====================================================

    def load_knowledge_base(

        self

    ):

        print(
            "Loading Knowledge Base..."
        )

        if not KNOWLEDGE_BASE_PATH.exists():

            raise FileNotFoundError(

                f"Knowledge Base not found:\n"

                f"{KNOWLEDGE_BASE_PATH}"

            )

        with open(

            KNOWLEDGE_BASE_PATH,

            "r",

            encoding="utf-8"

        ) as file:

            data = json.load(file)

        self.topics.clear()

        for topic_data in data:

            topic = Topic.from_dict(

                topic_data

            )

            self.topics.append(

                topic

            )

        print(

            f"Loaded "

            f"{len(self.topics)} "

            f"topics."

        )

    # =====================================================
    # Prepare Search Corpus
    # =====================================================

    def prepare_search_corpus(

        self

    ):

        """
        Converts every Topic into one
        searchable document.

        The searchable document contains

        Topic Name

        Summary

        Semantic Tags

        Important Claims

        Evidence

        This single text will later be used
        for both

        FAISS

        and

        BM25.
        """

        print(

            "Preparing Search Corpus..."

        )

        self.search_documents.clear()

        self.topic_lookup.clear()

        for index, topic in enumerate(

            self.topics

        ):

            document = ""

            # -------------------------------------
            # Topic Name
            # -------------------------------------

            document += (

                f"Topic\n"

                f"{topic.topic_name}\n\n"

            )

            # -------------------------------------
            # Summary
            # -------------------------------------

            document += (

                f"Summary\n"

                f"{topic.summary}\n\n"

            )

            # -------------------------------------
            # Semantic Tags
            # -------------------------------------

            if topic.semantic_tags:

                document += (

                    "Semantic Tags\n"

                )

                document += (

                    ", ".join(

                        topic.semantic_tags

                    )

                )

                document += "\n\n"

            

            # -------------------------------------
            # Evidence
            # -------------------------------------

            if topic.evidence:

                document += (

                    "Evidence\n"

                )

                for ev in topic.evidence:

                    document += (

                        ev.content

                        + "\n"

                    )

            self.search_documents.append(

                document

            )

            self.topic_lookup[

                index

            ] = topic

        print(

            f"Prepared "

            f"{len(self.search_documents)} "

            f"search documents.\n"

        )

    # =====================================================
    # Build FAISS Index
    # =====================================================

    def build_faiss_index(

        self

    ):

        """
        Builds FAISS Semantic Index.
        """

        print(

            "Building FAISS Index..."

        )

        embeddings = self.embedding_model.encode(

            self.search_documents,

            convert_to_numpy=True,

            show_progress_bar=True

        )

        embeddings = embeddings.astype(

            np.float32

        )

        self.document_embeddings = embeddings

        dimension = embeddings.shape[1]

        self.faiss_index = faiss.IndexFlatIP(

            dimension

        )

        faiss.normalize_L2(

            embeddings

        )

        self.faiss_index.add(

            embeddings

        )

        print(

            f"Indexed "

            f"{self.faiss_index.ntotal} "

            f"documents.\n"

        )

    # =====================================================
    # Build BM25 Index
    # =====================================================

    def build_bm25_index(

        self

    ):

        """
        Builds BM25 Keyword Index.
        """

        print(

            "Building BM25 Index..."

        )

        self.tokenized_documents = [

            document.lower().split()

            for document in self.search_documents

        ]

        self.bm25 = BM25Okapi(

            self.tokenized_documents

        )

        print(

            "BM25 Ready.\n"

        )

    # =====================================================
    # Semantic Search
    # =====================================================

    def semantic_search(

        self,

        processed_claim: ProcessedClaim,

        top_k: int = 10

    ) -> Dict[int, float]:

        """
        Returns

        topic_index -> semantic_score
        """

        if self.faiss_index is None:

            raise RuntimeError(

                "FAISS Index not built."

            )

        query_embedding = np.array(

            processed_claim.embedding,

            dtype=np.float32

        ).reshape(

            1,

            -1

        )

        faiss.normalize_L2(

            query_embedding

        )

        scores, indices = self.faiss_index.search(

            query_embedding,

            top_k

        )

        results = {}

        for score, index in zip(

            scores[0],

            indices[0]

        ):

            if index == -1:

                continue

            results[index] = float(

                score

            )

        return results

    # =====================================================
    # Keyword Search
    # =====================================================

    def keyword_search(

        self,

        processed_claim: ProcessedClaim,

        top_k: int = 10

    ) -> Dict[int, float]:

        """
        Returns

        topic_index -> keyword_score
        """

        if self.bm25 is None:

            raise RuntimeError(

                "BM25 Index not built."

            )

        tokens = (

            processed_claim

            .normalized_claim

            .lower()

            .split()

        )

        scores = self.bm25.get_scores(

            tokens

        )

        ranked = np.argsort(

            scores

        )[::-1]

        results = {}

        for index in ranked[:top_k]:

            results[int(index)] = float(

                scores[index]

            )

        return results

        # =====================================================
    # Hybrid Score Fusion
    # =====================================================

    def hybrid_search(

        self,

        processed_claim: ProcessedClaim,

        top_k: int = 5,

        semantic_weight: float = 0.7,

        keyword_weight: float = 0.3

    ) -> List[RetrievedEvidence]:

        """
        Combines FAISS and BM25 scores.
        """

        semantic_results = self.semantic_search(

            processed_claim,

            top_k=20

        )

        keyword_results = self.keyword_search(

            processed_claim,

            top_k=20

        )

        candidate_indices = set(

            semantic_results.keys()

        ).union(

            keyword_results.keys()

        )

        retrieved_results = []

        for index in candidate_indices:

            semantic_score = semantic_results.get(

                index,

                0.0

            )

            keyword_score = keyword_results.get(

                index,

                0.0

            )

            hybrid_score = (

                semantic_weight * semantic_score

                +

                keyword_weight * keyword_score

            )

            topic = self.topic_lookup[

                index

            ]

            evidence = RetrievedEvidence(

                topic=topic,

                semantic_score=semantic_score,

                keyword_score=keyword_score,

                hybrid_score=hybrid_score,

                matched_text=self.search_documents[

                    index

                ],

                evidence=topic.evidence,

                source_type="knowledge_base"

            )

            retrieved_results.append(

                evidence

            )

        retrieved_results.sort(

            key=lambda x: x.hybrid_score,

            reverse=True

        )

        return retrieved_results[:top_k]

    # =====================================================
    # Check Evidence Sufficiency
    # =====================================================

    def is_sufficient_evidence(

        self,

        results: List[RetrievedEvidence]

    ) -> bool:

        """
        Determines whether enough
        evidence exists for verification.

        This does NOT validate facts.

        It only checks whether retrieval
        produced sufficiently relevant
        evidence.
        """

        if len(results) == 0:

            return False

        best_result = results[0]

        minimum_score = 0.50

        minimum_evidence = 2

        if (

            best_result.hybrid_score

            <

            minimum_score

        ):

            return False

        if (

            len(

                best_result.evidence

            )

            <

            minimum_evidence

        ):

            return False

        return True

    # =====================================================
    # Queue Missing Topic
    # =====================================================

    def queue_missing_topic(

        self,

        processed_claim: ProcessedClaim

    ):

        """
        Placeholder.

        In TruthLens V2 this method will
        later call the Expansion Manager.

        ExpansionManager.queue_topic(...)

        For now we only print the request.
        """

        print()

        print(

            "Knowledge Expansion Required"

        )

        print(

            "Missing Claim :"

        )

        print(

            processed_claim.original_claim

        )

        print()

    # =====================================================
    # Retrieve
    # =====================================================

    def retrieve(

        self,

        processed_claim: ProcessedClaim,

        top_k: int = 5

    ):

        """
        Main Retrieval API.
        """

        results = self.hybrid_search(

            processed_claim,

            top_k

        )

        if self.is_sufficient_evidence(

            results

        ):

            return {

                "status": SUCCESS,

                "results": results

            }

        self.queue_missing_topic(

            processed_claim

        )

        return {

            "status":

            INSUFFICIENT_INFORMATION,

            "results": []

        }

    # =====================================================
    # Print Retrieval Results
    # =====================================================

    def print_results(

        self,

        retrieval_result

    ):

        """
        Pretty prints retrieval results.
        """

        print()

        print("=" * 60)

        print("Hybrid Retrieval Results")

        print("=" * 60)

        status = retrieval_result["status"]

        print(f"Status : {status}")

        print()

        if status == INSUFFICIENT_INFORMATION:

            print(

                "No sufficient evidence was found "

                "inside the Knowledge Base."

            )

            print()

            return

        for rank, result in enumerate(

            retrieval_result["results"],

            start=1

        ):

            print(

                f"[{rank}] {result.topic.topic_name}"

            )

            print(

                f"Hybrid Score   : "

                f"{result.hybrid_score:.4f}"

            )

            print(

                f"Semantic Score : "

                f"{result.semantic_score:.4f}"

            )

            print(

                f"Keyword Score  : "

                f"{result.keyword_score:.4f}"

            )

            print(

                f"Evidence Count : "

                f"{len(result.evidence)}"

            )

            print("-" * 60)

        print()

    # =====================================================
    # Rebuild Retrieval Indexes
    # =====================================================

    def rebuild_indexes(

        self

    ):

        """
        Rebuilds every retrieval index.

        Useful after the Knowledge Base
        has been updated.
        """

        print()

        print(

            "Rebuilding Retrieval Indexes..."

        )

        self.prepare_search_corpus()

        self.build_faiss_index()

        self.build_bm25_index()

        print(

            "Indexes Rebuilt Successfully.\n"

        )


# =========================================================
# Standalone Test
# =========================================================

if __name__ == "__main__":

    from claim_processing.claim_processor import (

        ClaimProcessor

    )

    processor = ClaimProcessor()

    retriever = HybridRetriever()

    retriever.build_faiss_index()

    retriever.build_bm25_index()

    print()

    print("=" * 60)

    print("TruthLens Hybrid Retrieval Test")

    print("=" * 60)

    while True:

        claim = input(

            "\nEnter Claim (or 'exit'): "

        )

        if claim.lower() == "exit":

            break

        processed = processor.process_claim(

            claim

        )

        results = retriever.retrieve(

            processed

        )

        retriever.print_results(

            results

        )
    