"""
=========================================================
TruthLens V2

Claim Processor + Rich Claim Extraction

Existing Processing Pipeline

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
ProcessedClaim


Rich Claim Extraction Pipeline

LLM Answer
   ↓
Sentence Segmentation
   ↓
Factual Claim Detection
   ↓
Claim Candidate Generation
   ↓
Coreference Resolution
   ↓
Decontextualization
   ↓
Claimify-style Refinement
   ↓
Atomic Claim Extraction
   ↓
Claim Filtering
   ↓
Claim Quality Scoring
   ↓
ExtractedClaim objects

IMPORTANT:

The existing ProcessedClaim structure and
ClaimProcessor API are preserved for compatibility
with HybridRetriever and Verifier.

=========================================================
"""

import json
import os
import re
from dataclasses import dataclass, field
from typing import List, Optional

import spacy
from keybert import KeyBERT
from sentence_transformers import SentenceTransformer


# =========================================================
# Existing Claim Schema
# DO NOT CHANGE THIS CONTRACT
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
# NEW Rich Claim Schema
# =========================================================

@dataclass
class ExtractedClaim:

    """
    Represents one independent, self-contained factual claim
    produced by the Rich Claim Extraction layer.

    This object is NOT passed directly to the Retriever.

    resolved_text is passed to the existing
    ClaimProcessor.process_claim() method.
    """

    claim_id: str

    original_text: str

    resolved_text: str

    source_sentence: str

    claim_type: str = "FACTUAL"

    entities: List[str] = field(
        default_factory=list
    )

    years: List[int] = field(
        default_factory=list
    )

    is_atomic: bool = True

    confidence: float = 0.0


# =========================================================
# Claim Processor
# =========================================================

class ClaimProcessor:

    """
    Existing deterministic claim processor.

    IMPORTANT:

    This class preserves the original API.

    process_claim(str)
        ↓
    ProcessedClaim
    """

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

            keyphrase_ngram_range=(1, 2)

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

        """
        EXISTING API.

        DO NOT change the return type.

        HybridRetriever depends on this returning
        exactly one ProcessedClaim.
        """

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

# =========================================================
# Rich Claim Extraction Layer
# =========================================================

from services.llm_service import LLMService


class RichClaimExtractor:

    """
    Context-aware factual claim extraction layer.

    Responsibilities:

    1. Sentence segmentation
    2. Factual claim detection
    3. Claim candidate generation
    4. Coreference resolution
    5. Decontextualization
    6. Claimify-style refinement
    7. Atomic claim extraction
    8. Claim filtering
    9. Claim quality scoring

    IMPORTANT:

    This LLM is used ONLY for claim extraction.

    It does NOT verify whether a claim is true or false.
    """

    def __init__(

        self,

        llm_service=None

    ):

        print(

            "Loading Rich Claim Extractor..."

        )

        if llm_service is None:

            self.llm_service = LLMService()

        else:

            self.llm_service = llm_service

        print(

            "Rich Claim Extractor Ready.\n"

        )

    # =====================================================
    # Sentence Segmentation
    # =====================================================

    def segment_sentences(

        self,

        text: str

    ) -> List[str]:

        """
        Splits the answer into sentence units.

        The LLM performs the semantic claim decomposition.
        """

        text = text.strip()

        if not text:

            return []

        doc = spacy.blank(

            "en"

        )

        doc.add_pipe(

            "sentencizer"

        )

        parsed = doc(text)

        sentences = []

        for sentence in parsed.sents:

            value = sentence.text.strip()

            if value:

                sentences.append(

                    value

                )

        return sentences

    # =====================================================
    # LLM Extraction
    # =====================================================

    def _llm_extract(

        self,

        answer: str

    ) -> List[dict]:

        """
        Uses the existing TruthLens Groq LLM service for:

        - factual claim detection
        - coreference resolution
        - decontextualization
        - atomic decomposition
        - Claimify-style refinement

        The LLM is NOT used to determine truth.
        """

        system_prompt = """
You are the Claim Extraction component of TruthLens.

Your job is to transform an LLM-generated answer into
independent, self-contained, factual claims suitable
for downstream fact verification.

You are NOT a fact verifier.

Do NOT determine whether a claim is true or false.

Your task is only to faithfully represent what the
source answer claims.

Rules:

1. Extract factual and verifiable claims.

2. Do not invent information.

3. Do not add outside knowledge.

4. Split compound factual statements into independent
   atomic claims whenever they represent separate
   factual propositions.

5. Resolve pronouns and references using the surrounding
   context.

6. Decontextualize every claim so that it can be understood
   independently.

7. Preserve important context required for verification.

8. Preserve names, organizations, locations, dates,
   quantities, events and relationships.

9. Preserve qualifiers such as:
   approximately, reportedly, allegedly, former,
   proposed, expected, according to, etc.

10. Do not convert uncertainty into certainty.

11. Do not convert opinions into facts.

12. Do not add facts merely because they are implied,
    except when necessary to resolve a reference.

13. Each returned claim must represent ONE atomic
    factual proposition.

14. Claims must remain faithful to the original answer.

15. Every resolved claim must be independently
    understandable without requiring the previous sentence.

16. If "he", "she", "they", "the company", "the organization",
    "this mission", "the project", etc. refer to an entity
    established in the context, replace the reference with
    the actual entity.

17. Do not merge separate factual claims.

Example:

Input:

"Siddharth is an AI/ML engineer and he is also the
founder of YatraNex. The company provides software
for bus operators."

Output:

{
  "claims": [
    {
      "original_text":
        "Siddharth is an AI/ML engineer.",
      "resolved_text":
        "Siddharth is an AI/ML engineer.",
      "source_sentence":
        "Siddharth is an AI/ML engineer and he is also the founder of YatraNex.",
      "claim_type":
        "FACTUAL",
      "is_atomic":
        true,
      "confidence":
        0.95
    },
    {
      "original_text":
        "he is also the founder of YatraNex.",
      "resolved_text":
        "Siddharth is the founder of YatraNex.",
      "source_sentence":
        "Siddharth is an AI/ML engineer and he is also the founder of YatraNex.",
      "claim_type":
        "FACTUAL",
      "is_atomic":
        true,
      "confidence":
        0.95
    },
    {
      "original_text":
        "The company provides software for bus operators.",
      "resolved_text":
        "YatraNex provides software for bus operators.",
      "source_sentence":
        "The company provides software for bus operators.",
      "claim_type":
        "FACTUAL",
      "is_atomic":
        true,
      "confidence":
        0.95
    }
  ]
}

Return ONLY valid JSON.

Required schema:

{
  "claims": [
    {
      "original_text": "...",
      "resolved_text": "...",
      "source_sentence": "...",
      "claim_type": "FACTUAL",
      "is_atomic": true,
      "confidence": 0.0
    }
  ]
}
"""

        user_prompt = (
            "Extract independent factual claims from "
            "the following answer:\n\n"
            + answer
        )

        prompt = (

            system_prompt

            + "\n\n"

            + user_prompt

        )

        response = self.llm_service.client.chat.completions.create(

            model=self.llm_service.model_name,

            temperature=0,

            messages=[

                {

                    "role": "system",

                    "content": system_prompt

                },

                {

                    "role": "user",

                    "content": user_prompt

                }

            ]

        )

        content = response.choices[0].message.content

        if not content:

            return []

        content = content.strip()

        content = content.replace(

            "```json",

            ""

        ).replace(

            "```",

            ""

        ).strip()

        try:

            data = json.loads(

                content

            )

        except json.JSONDecodeError as exc:

            raise RuntimeError(

                "Groq Rich Claim Extractor returned invalid JSON."

            ) from exc

        claims = data.get(

            "claims",

            []

        )

        if not isinstance(

            claims,

            list

        ):

            return []

        return claims

    # =====================================================
    # Claim Validation
    # =====================================================

    def _validate_claim(

        self,

        claim_data: dict

    ) -> bool:

        required = [

            "original_text",

            "resolved_text",

            "source_sentence"

        ]

        for field_name in required:

            value = claim_data.get(

                field_name

            )

            if not isinstance(

                value,

                str

            ):

                return False

            if not value.strip():

                return False

        claim_type = claim_data.get(

            "claim_type",

            "FACTUAL"

        )

        if claim_type != "FACTUAL":

            return False

        is_atomic = claim_data.get(

            "is_atomic",

            True

        )

        if not isinstance(

            is_atomic,

            bool

        ):

            return False

        return True

    # =====================================================
    # Extract Entities
    # =====================================================

    def _extract_claim_entities(

        self,

        claim: str

    ) -> List[str]:

        """
        Lightweight metadata extraction.

        The main ClaimProcessor remains responsible for
        the official retrieval representation.
        """

        nlp = spacy.load(

            "en_core_web_sm"

        )

        allowed = {

            "PERSON",

            "ORG",

            "GPE",

            "LOC",

            "PRODUCT",

            "EVENT"

        }

        entities = []

        doc = nlp(

            claim

        )

        for ent in doc.ents:

            if ent.label_ in allowed:

                value = ent.text.strip()

                if value:

                    entities.append(

                        value

                    )

        return sorted(

            list(

                set(entities)

            )

        )

    # =====================================================
    # Extract Years
    # =====================================================

    def _extract_claim_years(

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

                    int(year)

                    for year in years

                )

            )

        )

    # =====================================================
    # Build Extracted Claims
    # =====================================================

    def _build_claims(

        self,

        claim_data: List[dict]

    ) -> List[ExtractedClaim]:

        extracted = []

        claim_number = 1

        for item in claim_data:

            if not self._validate_claim(

                item

            ):

                continue

            resolved_text = item[

                "resolved_text"

            ].strip()

            original_text = item[

                "original_text"

            ].strip()

            source_sentence = item[

                "source_sentence"

            ].strip()

            confidence = item.get(

                "confidence",

                0.0

            )

            try:

                confidence = float(

                    confidence

                )

            except (

                TypeError,

                ValueError

            ):

                confidence = 0.0

            confidence = max(

                0.0,

                min(

                    1.0,

                    confidence

                )

            )

            claim = ExtractedClaim(

                claim_id=(

                    f"claim_{claim_number}"

                ),

                original_text=original_text,

                resolved_text=resolved_text,

                source_sentence=source_sentence,

                claim_type="FACTUAL",

                entities=(

                    self._extract_claim_entities(

                        resolved_text

                    )

                ),

                years=(

                    self._extract_claim_years(

                        resolved_text

                    )

                ),

                is_atomic=bool(

                    item.get(

                        "is_atomic",

                        True

                    )

                ),

                confidence=confidence

            )

            extracted.append(

                claim

            )

            claim_number += 1

        return extracted

    # =====================================================
    # Extract Claims
    # =====================================================

    def extract_claims(

        self,

        answer: str

    ) -> List[ExtractedClaim]:

        """
        Main API of the Rich Claim Extraction layer.
        """

        if not answer or not answer.strip():

            return []

        claim_data = self._llm_extract(

            answer

        )

        claims = self._build_claims(

            claim_data

        )

        return claims

    # =====================================================
    # Print Extracted Claims
    # =====================================================

    def print_claims(

        self,

        claims: List[ExtractedClaim]

    ):

        print()

        print("=" * 60)

        print("Rich Claim Extraction Results")

        print("=" * 60)

        if not claims:

            print(

                "No factual claims extracted."

            )

            print()

            return

        for claim in claims:

            print()

            print(

                f"Claim ID      : "

                f"{claim.claim_id}"

            )

            print(

                f"Original      : "

                f"{claim.original_text}"

            )

            print(

                f"Resolved      : "

                f"{claim.resolved_text}"

            )

            print(

                f"Source        : "

                f"{claim.source_sentence}"

            )

            print(

                f"Type          : "

                f"{claim.claim_type}"

            )

            print(

                f"Entities      : "

                f"{claim.entities}"

            )

            print(

                f"Years         : "

                f"{claim.years}"

            )

            print(

                f"Atomic        : "

                f"{claim.is_atomic}"

            )

            print(

                f"Confidence    : "

                f"{claim.confidence:.4f}"

            )

            print("-" * 60)

        print()


# =========================================================
# Standalone Rich Claim Extraction Test
# =========================================================

if __name__ == "__main__":

    print()

    print("=" * 60)

    print("TruthLens Rich Claim Extraction Test")

    print("=" * 60)

    extractor = RichClaimExtractor()

    answer = input(

        "\nEnter Answer (or 'exit'): "

    )

    if answer.lower() != "exit":

        claims = extractor.extract_claims(

            answer

        )

        extractor.print_claims(

            claims

        )