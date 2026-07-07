"""
=========================================================
TruthLens V2

Knowledge Manager

Acts as the Database Layer for the Knowledge Base.

Responsible for:

• Loading Topics
• Saving Topics
• Adding Topics
• Updating Topics
• Deleting Topics
• Searching Topics

=========================================================
"""

import json
import uuid
from pathlib import Path
from dataclasses import asdict

from knowledge_base.topic_schema import (
    Topic,
    Source,
    Evidence
)


class KnowledgeManager:

    def __init__(self, kb_path: str):

        self.kb_path = Path(kb_path)

        self.topics = []

        self.load()


    # =====================================================
    # Load Knowledge Base
    # =====================================================

    def load(self):

        if not self.kb_path.exists():

            self.topics = []

            return

        with open(self.kb_path, "r", encoding="utf-8") as f:

            data = json.load(f)

        self.topics = []

        for topic_data in data:

            sources = [
                Source(**s)
                for s in topic_data.get("sources", [])
            ]

            evidences = [
                Evidence(**e)
                for e in topic_data.get("evidence", [])
            ]

            topic = Topic(

                topic_id=topic_data["topic_id"],

                topic_name=topic_data["topic_name"],

                topic_category=topic_data["topic_category"],

                summary=topic_data["summary"],

                years=topic_data.get("years", []),

                entities=topic_data.get("entities", []),

                keywords=topic_data.get("keywords", []),

                semantic_tags=topic_data.get(
                    "semantic_tags", []
                ),

                evidence=evidences,

                sources=sources,

                topic_embedding=topic_data.get(
                    "topic_embedding", []
                ),

                source_reliability=topic_data.get(
                    "source_reliability", 0.0
                ),

                evidence_count=topic_data.get(
                    "evidence_count", 0
                ),

                trusted_source_count=topic_data.get(
                    "trusted_source_count", 0
                ),

                average_retrieval_confidence=topic_data.get(
                    "average_retrieval_confidence", 0.0
                ),

                summary_confidence=topic_data.get(
                    "summary_confidence", 0.0
                ),

                status=topic_data.get(
                    "status", "ACTIVE"
                ),

                version=topic_data.get(
                    "version", 1
                ),

                created_at=topic_data.get(
                    "created_at"
                ),

                last_updated=topic_data.get(
                    "last_updated"
                ),

                retrieval_count=topic_data.get(
                    "retrieval_count", 0
                ),

                verification_count=topic_data.get(
                    "verification_count", 0
                ),

                last_verified=topic_data.get(
                    "last_verified", ""
                )

            )

            self.topics.append(topic)


    # =====================================================
    # Save Knowledge Base
    # =====================================================

    def save(self):

        self.kb_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        with open(
            self.kb_path,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(

                [topic.to_dict() for topic in self.topics],

                f,

                indent=4,

                ensure_ascii=False

            )


    # =====================================================
    # Generate Topic ID
    # =====================================================

    @staticmethod
    def generate_topic_id():

        return str(uuid.uuid4())


    # =====================================================
    # Add Topic
    # =====================================================

    def add_topic(self, topic: Topic):

        if self.find_by_name(topic.topic_name):

            return False

        if not topic.topic_id:

            topic.topic_id = self.generate_topic_id()

        self.topics.append(topic)

        self.save()

        return True


    # =====================================================
    # Find Topic By Name
    # =====================================================

    def find_by_name(self, topic_name):

        for topic in self.topics:

            if topic.topic_name.lower() == topic_name.lower():

                return topic

        return None


    # =====================================================
    # Find Topic By ID
    # =====================================================

    def find_by_id(self, topic_id):

        for topic in self.topics:

            if topic.topic_id == topic_id:

                return topic

        return None


    # =====================================================
    # Delete Topic
    # =====================================================

    def delete_topic(self, topic_id):

        self.topics = [

            topic

            for topic in self.topics

            if topic.topic_id != topic_id

        ]

        self.save()


    # =====================================================
    # Update Topic
    # =====================================================

    def update_topic(self, updated_topic: Topic):

        for i, topic in enumerate(self.topics):

            if topic.topic_id == updated_topic.topic_id:

                updated_topic.increment_version()

                self.topics[i] = updated_topic

                self.save()

                return True

        return False


    # =====================================================
    # Get All Topics
    # =====================================================

    def get_all_topics(self):

        return self.topics


    # =====================================================
    # Number of Topics
    # =====================================================

    def topic_count(self):

        return len(self.topics)