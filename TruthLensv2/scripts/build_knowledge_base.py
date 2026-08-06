"""
=========================================================
TruthLens V2

Build Knowledge Base

Creates the complete Topic Knowledge Base
from the downloaded news dataset.

Pipeline

news_dataset.json
        │
        ▼
Load Dataset
        │
        ▼
Group Articles
        │
        ▼
Create Document Objects
        │
        ▼
Knowledge Creation Engine
        │
        ▼
Validate Topics
        │
        ▼
Knowledge Manager
        │
        ▼
knowledge_base.json

Author:
Siddharth Metkari
=========================================================
"""

import json

from pathlib import Path

from collections import defaultdict

from typing import Dict, List

from document_processing.document_processor import (
    Document
)

from knowledge_base.knowledge_creation_engine import (
    KnowledgeCreationEngine
)

from knowledge_base.knowledge_manager import (
    KnowledgeManager
)

from knowledge_base.topic_validator import (
    TopicValidator
)


# =========================================================
# Project Paths
# =========================================================

PROJECT_ROOT = Path(

    __file__

).resolve().parent.parent

DATA_FOLDER = (

    PROJECT_ROOT /

    "data"

)

INPUT_DATASET = (

    DATA_FOLDER /

    "news_dataset.json"

)

OUTPUT_KB = (

    DATA_FOLDER /

    "knowledge_base.json"

)


# =========================================================
# Build Knowledge Base
# =========================================================

class BuildKnowledgeBase:

    """
    Creates the complete Topic
    Knowledge Base.
    """

    def __init__(self):

        self.dataset = []

        self.grouped_articles = {}

        self.created_topics = []

        self.manager = KnowledgeManager(

            str(

                OUTPUT_KB

            )

        )

        self.engine = KnowledgeCreationEngine(

            self.manager

        )

        self.validator = TopicValidator()

        print(

            "\nKnowledge Base Builder Initialized."

        )


    # =====================================================
    # Load Dataset
    # =====================================================

    def load_dataset(

        self

    ) -> List[Dict]:

        """
        Loads the normalized
        news dataset.
        """

        if not INPUT_DATASET.exists():

            raise FileNotFoundError(

                f"{INPUT_DATASET} not found."

            )

        with open(

            INPUT_DATASET,

            "r",

            encoding="utf-8"

        ) as file:

            self.dataset = json.load(

                file

            )

        print(

            f"Loaded {len(self.dataset)} articles."

        )

        return self.dataset

    # =====================================================
    # Group Articles By Topic
    # =====================================================

    def group_articles(

        self

    ) -> Dict[str, List[Dict]]:

        """
        Groups all downloaded articles
        according to their topic.
        """

        grouped = defaultdict(

            list

        )

        for article in self.dataset:

            topic = article.get(

                "topic",

                ""

            ).strip()

            if not topic:

                continue

            grouped[topic].append(

                article

            )

        self.grouped_articles = dict(

            grouped

        )

        print(

            f"\nFound {len(self.grouped_articles)} topics."

        )

        return self.grouped_articles


    # =====================================================
    # Print Group Statistics
    # =====================================================

    def print_group_statistics(

        self

    ):

        """
        Displays the number of articles
        available for every topic.
        """

        print(

            "\n===================================="

        )

        print(

            "Topic Statistics"

        )

        print(

            "===================================="

        )

        total = 0

        for topic, articles in self.grouped_articles.items():

            count = len(

                articles

            )

            total += count

            print(

                f"{topic} : {count} article(s)"

            )

        print(

            "------------------------------------"

        )

        print(

            f"Total Articles : {total}"

        )

        print(

            "====================================\n"

        )


    # =====================================================
    # Convert Articles To Document Objects
    # =====================================================

    def create_documents(

        self,

        articles: List[Dict]

    ) -> List[Document]:

        """
        Converts normalized articles into
        Document objects.
        """

        documents = []

        for article in articles:

            document = Document(

                title=article.get(

                    "title",

                    ""

                ),

                content=article.get(

                    "content",

                    ""

                ),

                publisher=article.get(

                    "publisher",

                    ""

                ),

                url=article.get(

                    "url",

                    ""

                ),

                published_date=article.get(

                    "published_date",

                    ""

                )

            )

            documents.append(

                document

            )

        return documents


    # =====================================================
    # Prepare Documents
    # =====================================================

    def prepare_documents(

        self

    ) -> Dict[str, List[Document]]:

        """
        Converts every topic group
        into Document objects.
        """

        prepared_documents = {}

        for topic, articles in self.grouped_articles.items():

            prepared_documents[topic] = (

                self.create_documents(

                    articles

                )

            )

        print(

            f"\nPrepared {len(prepared_documents)} document groups."

        )

        return prepared_documents

    # =====================================================
    # Generate Topics
    # =====================================================

    def generate_topics(

        self,

        prepared_documents: Dict[str, List[Document]]

    ):

        """
        Creates one Topic object
        for every grouped topic.
        """

        self.created_topics = []

        print(

            "\n===================================="

        )

        print(

            "Generating Topics"

        )

        print(

            "===================================="

        )

        for topic_name, documents in prepared_documents.items():

            print(

                f"\nCreating Topic : {topic_name}"

            )

            try:

                topic = self.engine.create_topic(

                    documents

                )

                if topic is not None:

                    self.created_topics.append(

                        topic

                    )

                    print(

                        "✓ Topic Created"

                    )

                else:

                    print(

                        "✗ Topic Creation Failed"

                    )

            except Exception as e:

                print(

                    f"Error creating '{topic_name}'"

                )

                print(

                    e

                )

        print(

            "\n===================================="

        )

        print(

            f"Generated Topics : {len(self.created_topics)}"

        )

        print(

            "===================================="

        )

        return self.created_topics


    # =====================================================
    # Validate Topics
    # =====================================================

    def validate_topics(

        self

    ):

        """
        Validates every generated Topic.
        """

        valid_topics = []

        print(

            "\n===================================="

        )

        print(

            "Validating Topics"

        )

        print(

            "===================================="

        )

        for topic in self.created_topics:

            report = self.validator.validate(

                topic

            )

            self.validator.print_report(

                report

            )

            if report["is_valid"]:

                valid_topics.append(

                    topic

                )

            else:

                print(

                    f"Rejected : {topic.topic_name}"

                )

        self.created_topics = valid_topics

        print(

            f"\nValid Topics : {len(valid_topics)}"

        )

        return valid_topics


    # =====================================================
    # Save Knowledge Base
    # =====================================================

    def save_knowledge_base(

        self

    ):

        """
        Saves Topics into
        knowledge_base.json.
        """

        print(

            "\n===================================="

        )

        print(

            "Saving Knowledge Base"

        )

        print(

            "===================================="

        )

        added = 0

        updated = 0

        for topic in self.created_topics:

            existing = self.manager.find_by_name(

                topic.topic_name

            )

            if existing is None:

                self.manager.add_topic(

                    topic

                )

                added += 1

                print(

                    f"Added : {topic.topic_name}"

                )

            else:

                topic.topic_id = existing.topic_id

                self.manager.update_topic(

                    topic

                )

                updated += 1

                print(

                    f"Updated : {topic.topic_name}"

                )

        print(

            "\n===================================="

        )

        print(

            f"Added Topics   : {added}"

        )

        print(

            f"Updated Topics : {updated}"

        )

        print(

            f"Total Topics   : {self.manager.topic_count()}"

        )

        print(

            "===================================="

        )

        return self.manager.get_all_topics()

    # =====================================================
    # Build Complete Knowledge Base
    # =====================================================

    def build(

        self

    ):

        """
        Executes the complete Knowledge
        Base creation pipeline.
        """

        print(

            "\n========================================"

        )

        print(

            "TruthLens V2 Knowledge Base Creation Started"

        )

        print(

            "========================================"

        )

        # ---------------------------------------------
        # Load Dataset
        # ---------------------------------------------

        self.load_dataset()

        # ---------------------------------------------
        # Group Articles
        # ---------------------------------------------

        self.group_articles()

        self.print_group_statistics()

        # ---------------------------------------------
        # Convert to Documents
        # ---------------------------------------------

        prepared_documents = self.prepare_documents()

        # ---------------------------------------------
        # Generate Topics
        # ---------------------------------------------

        self.generate_topics(

            prepared_documents

        )

        # ---------------------------------------------
        # Validate Topics
        # ---------------------------------------------

        self.validate_topics()

        # ---------------------------------------------
        # Save Knowledge Base
        # ---------------------------------------------

        self.save_knowledge_base()

        print(

            "\n========================================"

        )

        print(

            "Knowledge Base Created Successfully"

        )

        print(

            "========================================"

        )

        print(

            f"\nKnowledge Base Location : {OUTPUT_KB}"

        )

        print(

            f"Total Topics : {self.manager.topic_count()}"

        )

        print()

        return self.manager.get_all_topics()


# =========================================================
# Main
# =========================================================

if __name__ == "__main__":

    try:

        builder = BuildKnowledgeBase()

        builder.build()

    except KeyboardInterrupt:

        print(

            "\nKnowledge Base creation interrupted."

        )

    except Exception as e:

        print(

            "\nFatal Error"

        )

        print(

            e

        )