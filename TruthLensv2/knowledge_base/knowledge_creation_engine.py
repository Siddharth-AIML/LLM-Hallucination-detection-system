"""
=========================================================
TruthLens V2

Knowledge Creation Engine

Converts raw documents into structured Topics.

Pipeline

Raw Documents
      ↓
Cleaning
      ↓
Metadata Extraction
      ↓
Entity Extraction
      ↓
Keyword Extraction
      ↓
Year Extraction
      ↓
Document Embeddings
      ↓
Topic Matching
      ↓
Topic Creation
      ↓
Topic Validation
      ↓
Knowledge Base

Author:
Siddharth Metkari
=========================================================
"""

import json
import uuid
from collections import Counter
from typing import List
from services.llm_service import LLMService

import numpy as np

import spacy

from keybert import KeyBERT

from sklearn.metrics.pairwise import cosine_similarity

from sentence_transformers import SentenceTransformer

from document_processing.document_processor import (
    Document
)

from knowledge_base.topic_schema import (
    Topic,
    Evidence,
    Source
)

from knowledge_base.topic_validator import (
    TopicValidator
)

from knowledge_base.knowledge_manager import (
    KnowledgeManager
)


class KnowledgeCreationEngine:

    """
    Main AI Engine responsible for creating and
    updating the Topic Knowledge Base.
    """

    def __init__(

        self,

        knowledge_manager: KnowledgeManager

    ):

        print("Loading Knowledge Creation Engine...")

        self.kb = knowledge_manager

        self.validator = TopicValidator()

        self.llm = LLMService()

        print("Loading spaCy...")

        self.nlp = spacy.load(
            "en_core_web_sm"
        )

        print("Loading KeyBERT...")

        self.keyword_model = KeyBERT()

        print("Loading MiniLM...")

        self.embedding_model = SentenceTransformer(
            "sentence-transformers/all-MiniLM-L6-v2"
        )

        print("Knowledge Creation Engine Ready.\n")

    # =====================================================
    # Clean Documents
    # =====================================================

    def clean_documents(

        self,

        documents: List[Document]

    ) -> List[Document]:

        cleaned = []

        for doc in documents:

            doc.title = doc.title.strip()

            doc.content = doc.content.strip()

            if len(doc.content) < 50:

                continue

            cleaned.append(doc)

        return cleaned
    

        # =====================================================
    # Aggregate Documents
    # =====================================================

    def aggregate_documents(

        self,

        documents: List[Document]

    ):

        full_text = ""

        for doc in documents:

            full_text += doc.title

            full_text += "\n"

            full_text += doc.content

            full_text += "\n"

        return full_text
    
        # =====================================================
    # Extract Entities
    # =====================================================

    def extract_entities(

        self,

        text: str

    ) -> List[str]:

        doc = self.nlp(text)

        entities = []

        allowed = {

            "PERSON",

            "ORG",

            "GPE",

            "LOC",

            "PRODUCT",

            "EVENT"

        }

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

        text: str,

        top_n: int = 15

    ):

        keywords = self.keyword_model.extract_keywords(

            text,

            top_n=top_n,

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

        text: str

    ):

        import re

        years = re.findall(

            r"\b(19\d{2}|20\d{2}|21\d{2})\b",

            text

        )

        years = sorted(

            list(

                set(

                    map(

                        int,

                        years

                    )

                )

            )

        )

        return years
    
        # =====================================================
    # Generate Embedding
    # =====================================================

    def generate_embedding(

        self,

        text: str

    ):

        embedding = self.embedding_model.encode(

            text,

            convert_to_numpy=True

        )

        return embedding.tolist()
    
        # =====================================================
    # Aggregate Existing Topic Text
    # =====================================================

    def topic_to_text(
        self,
        topic: Topic
    ) -> str:

        """
        Converts Topic object into one text block
        for semantic comparison.
        """

        text = topic.topic_name + " "

        text += topic.summary + " "

        text += " ".join(topic.entities) + " "

        text += " ".join(topic.keywords)

        return text
    
        # =====================================================
    # Semantic Similarity
    # =====================================================

    def semantic_similarity(

        self,

        embedding1,

        embedding2

    ):

        score = cosine_similarity(

            [embedding1],

            [embedding2]

        )[0][0]

        return float(score)
    
        # =====================================================
    # Entity Similarity
    # =====================================================

    def entity_similarity(

        self,

        entities1,

        entities2

    ):

        if len(entities1) == 0:

            return 0.0

        intersection = len(

            set(entities1)

            &

            set(entities2)

        )

        union = len(

            set(entities1)

            |

            set(entities2)

        )

        return intersection / union
    

        # =====================================================
    # Keyword Similarity
    # =====================================================

    def keyword_similarity(

        self,

        keywords1,

        keywords2

    ):

        if len(keywords1) == 0:

            return 0.0

        intersection = len(

            set(keywords1)

            &

            set(keywords2)

        )

        union = len(

            set(keywords1)

            |

            set(keywords2)

        )

        return intersection / union
    

        # =====================================================
    # Year Similarity
    # =====================================================

    def year_similarity(

        self,

        years1,

        years2

    ):

        if len(years1) == 0:

            return 0.5

        if len(years2) == 0:

            return 0.5

        intersection = len(

            set(years1)

            &

            set(years2)

        )

        union = len(

            set(years1)

            |

            set(years2)

        )

        return intersection / union
    
        # =====================================================
    # Topic Confidence
    # =====================================================

    def topic_confidence(

        self,

        semantic,

        entity,

        keyword,

        year,

        reliability

    ):

        score = (

            semantic * 0.40 +

            entity * 0.20 +

            keyword * 0.20 +

            year * 0.10 +

            reliability * 0.10

        )

        return round(score,3)
    

        # =====================================================
    # Find Existing Topic
    # =====================================================

    def find_existing_topic(

        self,

        text,

        entities,

        keywords,

        years

    ):

        embedding = self.embedding_model.encode(

            text,

            convert_to_numpy=True

        )

        best_topic = None

        best_score = 0

        for topic in self.kb.topics:

            topic_text = self.topic_to_text(topic)

            topic_embedding = topic.topic_embedding

            semantic_score = self.semantic_similarity(

                embedding,

                topic_embedding

            )

            entity_score = self.entity_similarity(

                entities,

                topic.entities

            )

            keyword_score = self.keyword_similarity(

                keywords,

                topic.keywords

            )

            year_score = self.year_similarity(

                years,

                topic.years

            )

            reliability_score = topic.source_reliability

            confidence_score = self.topic_confidence(

                semantic_score,

                entity_score,

                keyword_score,

                year_score,

                reliability_score

            )

            if confidence_score > best_score:

                best_score = confidence_score

                best_topic = topic


        return best_topic, best_score
    #part3 starts here
     # =====================================================
    # Build Source Objects
    # =====================================================

    def build_sources(
        self,
        documents: List[Document]
    ) -> List[Source]:
        """
        Creates Source objects from processed documents.
        """

        sources = []

        for doc in documents:

            source = Source(

                publisher=doc.publisher,

                title=doc.title,

                url=doc.url,

                published_date=doc.published_date,

                reliability_score=0.90

            )

            sources.append(source)

        return sources


    # =====================================================
    # Build Evidence Objects
    # =====================================================

    def build_evidence(
        self,
        documents: List[Document]
    ) -> List[Evidence]:
        """
        Converts document sentences into Evidence objects.
        """

        evidences = []

        for doc in documents:

            doc_object = self.nlp(doc.content)

            for sent in doc_object.sents:

                sentence = sent.text.strip()

                if len(sentence) < 40:
                    continue

                evidence = Evidence(

                    text=sentence,

                    source=doc.publisher,

                    url=doc.url,

                    published_date=doc.published_date,

                    retrieval_score=0.0

                )

                evidences.append(evidence)

        return evidences


    # =====================================================
    # Generate Topic Metadata using Gemini
    # =====================================================

    def generate_topic_metadata(
        self,
        documents: List[Document]
    ):
        """
        Calls Gemini through LLMService and returns
        structured topic metadata.
        """

        metadata = self.llm.generate_topic_metadata(
            documents
        )

        return metadata
    
        # =====================================================
    # Create Topic Object
    # =====================================================

    def create_topic(

        self,

        documents: List[Document]

    ) -> Topic:

        """
        Creates a Topic object from a group of
        processed documents.
        """

        # ---------------------------------------------
        # Clean Documents
        # ---------------------------------------------

        documents = self.clean_documents(
            documents
        )

        # ---------------------------------------------
        # Merge all documents
        # ---------------------------------------------

        full_text = self.aggregate_documents(
            documents
        )

        # ---------------------------------------------
        # Extract Metadata
        # ---------------------------------------------

        entities = self.extract_entities(
            full_text
        )

        keywords = self.extract_keywords(
            full_text
        )

        years = self.extract_years(
            full_text
        )

        # ---------------------------------------------
        # Generate Topic Embedding
        # ---------------------------------------------

        embedding = self.generate_embedding(
            full_text
        )

        # ---------------------------------------------
        # LLM Metadata
        # ---------------------------------------------

        metadata = self.generate_topic_metadata(
            documents
        )

        # ---------------------------------------------
        # Evidence & Sources
        # ---------------------------------------------

        evidences = self.build_evidence(
            documents
        )

        sources = self.build_sources(
            documents
        )

        # ---------------------------------------------
        # Calculate Source Reliability
        # ---------------------------------------------

        if len(sources) > 0:

            reliability = sum(

                source.reliability_score

                for source in sources

            ) / len(sources)

        else:

            reliability = 0.0

        # ---------------------------------------------
        # Create Topic
        # ---------------------------------------------

        topic = Topic(

            topic_id=str(uuid.uuid4()),

            topic_name=metadata["topic_name"],

            topic_category=metadata["topic_category"],

            summary=metadata["summary"],

            years=years,

            entities=entities,

            keywords=keywords,

            semantic_tags=metadata["semantic_tags"],

            evidence=evidences,

            sources=sources,

            topic_embedding=embedding,

            source_reliability=reliability,

            evidence_count=len(evidences),

            trusted_source_count=len(

                [

                    s

                    for s in sources

                    if s.reliability_score >= 0.80

                ]

            ),

            average_retrieval_confidence=0.0,

            summary_confidence=metadata["confidence"]

        )

        return topic
    
        # =====================================================
    # Merge Existing Topic
    # =====================================================

    def merge_topic(

        self,

        existing_topic: Topic,

        new_topic: Topic

    ) -> Topic:

        """
        Merges newly created topic information
        into an existing topic.
        """

        # ---------------------------------------------
        # Merge Evidence
        # ---------------------------------------------

        for evidence in new_topic.evidence:

            existing_topic.add_evidence(
                evidence
            )

        # ---------------------------------------------
        # Merge Sources
        # ---------------------------------------------

        for source in new_topic.sources:

            existing_topic.add_source(
                source
            )

        # ---------------------------------------------
        # Merge Entities
        # ---------------------------------------------

        existing_topic.entities = sorted(

            list(

                set(

                    existing_topic.entities +

                    new_topic.entities

                )

            )

        )

        # ---------------------------------------------
        # Merge Keywords
        # ---------------------------------------------

        existing_topic.keywords = sorted(

            list(

                set(

                    existing_topic.keywords +

                    new_topic.keywords

                )

            )

        )

        # ---------------------------------------------
        # Merge Semantic Tags
        # ---------------------------------------------

        existing_topic.semantic_tags = sorted(

            list(

                set(

                    existing_topic.semantic_tags +

                    new_topic.semantic_tags

                )

            )

        )

        # ---------------------------------------------
        # Merge Years
        # ---------------------------------------------

        existing_topic.years = sorted(

            list(

                set(

                    existing_topic.years +

                    new_topic.years

                )

            )

        )

        # ---------------------------------------------
        # Update Summary
        # ---------------------------------------------

        if len(new_topic.summary) > len(existing_topic.summary):

            existing_topic.summary = new_topic.summary

            existing_topic.summary_confidence = (

                new_topic.summary_confidence

            )

        # ---------------------------------------------
        # Update Reliability
        # ---------------------------------------------

        existing_topic.source_reliability = max(

            existing_topic.source_reliability,

            new_topic.source_reliability

        )

        # ---------------------------------------------
        # Update Embedding
        # ---------------------------------------------

        existing_topic.update_embedding(

            new_topic.topic_embedding

        )

        # ---------------------------------------------
        # Update Counts
        # ---------------------------------------------

        existing_topic.evidence_count = len(

            existing_topic.evidence

        )

        existing_topic.trusted_source_count = len(

            [

                s

                for s in existing_topic.sources

                if s.reliability_score >= 0.80

            ]

        )

        existing_topic.update_timestamp()

        return existing_topic
    
        # =====================================================
    # Build / Update Topic
    # =====================================================

    def build_topic(

        self,

        documents: List[Document]

    ) -> Topic:

        """
        Creates a new Topic or merges into an
        existing Topic if it already exists.
        """

        # ---------------------------------------------
        # Create Candidate Topic
        # ---------------------------------------------

        candidate_topic = self.create_topic(

            documents

        )

        # ---------------------------------------------
        # Check Existing Topic
        # ---------------------------------------------

        existing_topic, confidence = self.find_existing_topic(

            candidate_topic.summary,

            candidate_topic.entities,

            candidate_topic.keywords,

            candidate_topic.years

        )

        # ---------------------------------------------
        # Merge Threshold
        # ---------------------------------------------

        MERGE_THRESHOLD = 0.75

        if (

            existing_topic is not None

            and

            confidence >= MERGE_THRESHOLD

        ):

            print(

                f"Merging with existing topic "

                f"({existing_topic.topic_name}) "

                f"[Confidence={confidence:.3f}]"

            )

            merged_topic = self.merge_topic(

                existing_topic,

                candidate_topic

            )

            return merged_topic

        print(

            f"Creating New Topic "

            f"[Confidence={confidence:.3f}]"

        )

        return candidate_topic


    # =====================================================
    # Validate Topic
    # =====================================================

    def validate_topic(

        self,

        topic: Topic

    ):

        """
        Runs Topic Validator.
        """

        report = self.validator.validate(

            topic

        )

        self.validator.print_report(

            report

        )

        return report
        # =====================================================
    # Save Topic
    # =====================================================

    def save_topic(

        self,

        topic: Topic

    ) -> bool:

        """
        Validates the Topic and stores it
        inside the Knowledge Base.
        """

        # ---------------------------------------------
        # Validate Topic
        # ---------------------------------------------

        report = self.validate_topic(

            topic

        )

        if not report["is_valid"]:

            print(

                "\nTopic validation failed."

            )

            return False

        # ---------------------------------------------
        # Check Existing Topic
        # ---------------------------------------------

        existing = self.kb.find_by_id(

            topic.topic_id

        )

        # ---------------------------------------------
        # Update Existing Topic
        # ---------------------------------------------

        if existing is not None:

            print(

                "Updating existing topic..."

            )

            self.kb.update_topic(

                topic

            )

            print(

                "Topic updated successfully."

            )

            return True

        # ---------------------------------------------
        # Add New Topic
        # ---------------------------------------------

        print(

            "Adding new topic..."

        )

        self.kb.add_topic(

            topic

        )

        print(

            "Topic added successfully."

        )

        return True
    
        # =====================================================
    # Process Documents
    # =====================================================

    def process_documents(

        self,

        documents: List[Document]

    ) -> Topic | None:

        """
        Complete Knowledge Creation Pipeline.

        Documents
            ↓
        Build Topic
            ↓
        Validate Topic
            ↓
        Save Topic
            ↓
        Return Topic
        """

        # ---------------------------------------------
        # Empty Document Check
        # ---------------------------------------------

        if len(documents) == 0:

            print(

                "No documents received."

            )

            return None

        # ---------------------------------------------
        # Build Topic
        # ---------------------------------------------

        topic = self.build_topic(

            documents

        )

        # ---------------------------------------------
        # Save Topic
        # ---------------------------------------------

        success = self.save_topic(

            topic

        )

        if not success:

            print(

                "Topic could not be stored."

            )

            return None

        print(

            "\nKnowledge Base Updated Successfully."

        )

        return topic


    # =====================================================
    # Process Multiple Topic Groups
    # =====================================================

    def process_topic_groups(

        self,

        topic_groups: List[List[Document]]

    ):

        """
        Processes multiple groups of documents.

        Example

        Group 1
        ↓
        Fusion Reactor

        Group 2
        ↓
        India AI

        Group 3
        ↓
        Solar Storm
        """

        created_topics = []

        for i, group in enumerate(topic_groups):

            print(

                f"\nProcessing Topic Group {i+1}"

            )

            topic = self.process_documents(

                group

            )

            if topic is not None:

                created_topics.append(

                    topic

                )

        return created_topics
    
        # =====================================================
    # Knowledge Base Statistics
    # =====================================================

    def knowledge_base_statistics(

        self

    ):

        """
        Displays statistics of the Knowledge Base.
        """

        total_topics = self.kb.topic_count()

        total_evidence = sum(

            len(topic.evidence)

            for topic in self.kb.get_all_topics()

        )

        total_sources = sum(

            len(topic.sources)

            for topic in self.kb.get_all_topics()

        )

        print("\n==============================")

        print("Knowledge Base Statistics")

        print("==============================")

        print(

            f"Topics              : {total_topics}"

        )

        print(

            f"Evidence            : {total_evidence}"

        )

        print(

            f"Sources             : {total_sources}"

        )

        print("==============================\n")


    # =====================================================
    # Search Topic
    # =====================================================

    def search_topic(

        self,

        topic_name: str

    ) -> Topic | None:

        """
        Searches for a Topic by its name.
        """

        topic = self.kb.find_by_name(

            topic_name

        )

        if topic is None:

            print(

                "Topic not found."

            )

            return None

        return topic


    # =====================================================
    # List All Topics
    # =====================================================

    def list_topics(

        self

    ):

        """
        Prints all Topics stored inside the
        Knowledge Base.
        """

        print("\n========== Topics ==========\n")

        for i, topic in enumerate(

            self.kb.get_all_topics(),

            start=1

        ):

            print(

                f"{i}. {topic.topic_name}"

            )

        print("\n============================\n")


    # =====================================================
    # Build Knowledge Base
    # =====================================================

    def build_knowledge_base(

        self,

        topic_groups: List[List[Document]]

    ):

        """
        Complete pipeline for building the
        Knowledge Base.
        """

        print(

            "\nBuilding Knowledge Base...\n"

        )

        topics = self.process_topic_groups(

            topic_groups

        )

        print(

            "\nKnowledge Base Build Complete."

        )

        print(

            f"Topics Created : {len(topics)}"

        )

        self.knowledge_base_statistics()

        return topics