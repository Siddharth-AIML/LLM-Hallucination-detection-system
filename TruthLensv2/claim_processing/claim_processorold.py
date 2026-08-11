"""
=========================================================
TruthLens V2

Claim Processor

Processes a user claim before retrieval.

Pipeline

Claim
   ↓
Normalization
   ↓
Entity Extraction
   ↓
Keyword Extraction
   ↓
Year Extraction
   ↓
Embedding Generation
   ↓
Structured Claim Object

=========================================================
"""

import re
from dataclasses import dataclass
from typing import List

import spacy
from keybert import KeyBERT
from sentence_transformers import SentenceTransformer


# =========================================================
# Claim Schema
# =========================================================

@dataclass
class ProcessedClaim:

    original_claim: str

    normalized_claim: str

    entities: List[str]

    keywords: List[str]

    years: List[int]

    embedding: List[float]


# =========================================================
# Claim Processor
# =========================================================

class ClaimProcessor:

    def __init__(self):

        print("Loading Claim Processor...")

        self.nlp = spacy.load(
            "en_core_web_sm"
        )

        self.keyword_model = KeyBERT()

        self.embedding_model = SentenceTransformer(
            "sentence-transformers/all-MiniLM-L6-v2"
        )

        print("Claim Processor Ready.\n")

    # =====================================================
    # Normalize Claim
    # =====================================================

    def normalize_claim(

        self,

        claim: str

    ) -> str:

        claim = claim.strip()

        claim = re.sub(

            r"\s+",

            " ",

            claim

        )

        return claim

    # =====================================================
    # Extract Entities
    # =====================================================

    def extract_entities(

        self,

        claim: str

    ) -> List[str]:

        doc = self.nlp(claim)

        allowed = {

            "PERSON",

            "ORG",

            "GPE",

            "LOC",

            "PRODUCT",

            "EVENT"

        }

        entities = []

        for ent in doc.ents:

            if ent.label_ in allowed:

                entities.append(

                    ent.text.strip()

                )

        return sorted(

            list(

                set(entities)

            )

        )

    # =====================================================
    # Extract Keywords
    # =====================================================

    def extract_keywords(

        self,

        claim: str

    ) -> List[str]:

        keywords = self.keyword_model.extract_keywords(

            claim,

            top_n=8,

            stop_words="english",

            keyphrase_ngram_range=(1,2)

        )

        return [

            word

            for word,

            score

            in keywords

        ]

    # =====================================================
    # Extract Years
    # =====================================================

    def extract_years(

        self,

        claim: str

    ) -> List[int]:

        years = re.findall(

            r"\b(19\d{2}|20\d{2}|21\d{2})\b",

            claim

        )

        return sorted(

            list(

                set(

                    map(

                        int,

                        years

                    )

                )

            )

        )

    # =====================================================
    # Generate Embedding
    # =====================================================

    def generate_embedding(

        self,

        claim: str

    ) -> List[float]:

        embedding = self.embedding_model.encode(

            claim,

            convert_to_numpy=True

        )

        return embedding.tolist()

    # =====================================================
    # Process Claim
    # =====================================================

    def process_claim(

        self,

        claim: str

    ) -> ProcessedClaim:

        normalized = self.normalize_claim(

            claim

        )

        entities = self.extract_entities(

            normalized

        )

        keywords = self.extract_keywords(

            normalized

        )

        years = self.extract_years(

            normalized

        )

        embedding = self.generate_embedding(

            normalized

        )

        processed = ProcessedClaim(

            original_claim=claim,

            normalized_claim=normalized,

            entities=entities,

            keywords=keywords,

            years=years,

            embedding=embedding

        )

        return processed

    # =====================================================
    # Print Processed Claim
    # =====================================================

    def print_claim(

        self,

        processed: ProcessedClaim

    ):

        print("\n==============================")

        print("Processed Claim")

        print("==============================")

        print(

            "Original :",

            processed.original_claim

        )

        print(

            "Normalized :",

            processed.normalized_claim

        )

        print(

            "Entities :",

            processed.entities

        )

        print(

            "Keywords :",

            processed.keywords

        )

        print(

            "Years :",

            processed.years

        )

        print(

            "Embedding Dimension :",

            len(processed.embedding)

        )

        print("==============================\n")


