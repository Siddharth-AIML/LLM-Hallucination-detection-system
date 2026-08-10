"""
TruthLens V2

Knowledge Base Expansion Queue

Purpose:
    Stores claims/topics that could not be verified because
    sufficient information was not available in the current
    Knowledge Base.

The queue is intentionally independent from:
    - Claim Processor
    - Hybrid Retriever
    - Verifier
    - Knowledge Base Builder

Those components will be connected later through the
Knowledge Expansion pipeline.
"""

import json
import os
from datetime import datetime


class ExpansionQueue:

    # =====================================================
    # Initialization
    # =====================================================

    def __init__(
        self,
        queue_file="data/expansion_queue.json"
    ):

        self.queue_file = queue_file

        self._ensure_storage()

        self.queue = self._load_queue()


    # =====================================================
    # Storage Initialization
    # =====================================================

    def _ensure_storage(
        self
    ):

        directory = os.path.dirname(
            self.queue_file
        )

        if directory:

            os.makedirs(
                directory,
                exist_ok=True
            )

        if not os.path.exists(
            self.queue_file
        ):

            with open(
                self.queue_file,
                "w",
                encoding="utf-8"
            ) as file:

                json.dump(
                    [],
                    file,
                    indent=4
                )


    # =====================================================
    # Load Queue
    # =====================================================

    def _load_queue(
        self
    ):

        try:

            with open(
                self.queue_file,
                "r",
                encoding="utf-8"
            ) as file:

                data = json.load(file)

                if isinstance(
                    data,
                    list
                ):

                    return data

                return []

        except (
            json.JSONDecodeError,
            OSError
        ):

            return []


    # =====================================================
    # Save Queue
    # =====================================================

    def _save_queue(
        self
    ):

        with open(
            self.queue_file,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                self.queue,
                file,
                indent=4,
                ensure_ascii=False
            )


    # =====================================================
    # Normalize Topic
    # =====================================================

    @staticmethod
    def _normalize_topic(
        topic
    ):

        return " ".join(
            topic.strip().lower().split()
        )


    # =====================================================
    # Add Topic
    # =====================================================

    def add_topic(
        self,
        topic
    ):

        """
        Add a missing topic/claim to the queue.

        Duplicate topics are not added again.

        Returns:
            queue item if added
            existing item if duplicate
            None if input is invalid
        """

        if not isinstance(
            topic,
            str
        ):

            return None

        topic = topic.strip()

        if not topic:

            return None

        normalized_topic = (
            self._normalize_topic(
                topic
            )
        )

        # ---------------------------------------------
        # Duplicate Check
        # ---------------------------------------------

        for item in self.queue:

            existing_topic = (
                self._normalize_topic(
                    item.get(
                        "topic",
                        ""
                    )
                )
            )

            if (
                existing_topic
                == normalized_topic
            ):

                return item


        # ---------------------------------------------
        # Create Queue Item
        # ---------------------------------------------

        item = {

            "topic": topic,

            "status": "PENDING",

            "created_at": (
                datetime.utcnow()
                .isoformat()
            ),

            "updated_at": (
                datetime.utcnow()
                .isoformat()
            ),

            "retry_count": 0

        }

        self.queue.append(
            item
        )

        self._save_queue()

        return item


    # =====================================================
    # Get Pending Topics
    # =====================================================

    def get_pending_topics(
        self
    ):

        """
        Return all topics waiting for expansion.
        """

        return [

            item

            for item in self.queue

            if item.get(
                "status"
            ) == "PENDING"

        ]


    # =====================================================
    # Get All Topics
    # =====================================================

    def get_all_topics(
        self
    ):

        """
        Return all queue items.
        """

        return list(
            self.queue
        )


    # =====================================================
    # Update Status
    # =====================================================

    def update_status(
        self,
        topic,
        status
    ):

        """
        Update the status of a queued topic.

        Supported statuses:

            PENDING
            PROCESSING
            COMPLETED
            DISCARDED
            RETRY
        """

        valid_statuses = {

            "PENDING",
            "PROCESSING",
            "COMPLETED",
            "DISCARDED",
            "RETRY"

        }

        if status not in valid_statuses:

            raise ValueError(
                f"Invalid queue status: {status}"
            )


        normalized_topic = (
            self._normalize_topic(
                topic
            )
        )


        for item in self.queue:

            existing_topic = (
                self._normalize_topic(
                    item.get(
                        "topic",
                        ""
                    )
                )
            )

            if (
                existing_topic
                == normalized_topic
            ):

                item["status"] = status

                item["updated_at"] = (
                    datetime.utcnow()
                    .isoformat()
                )

                self._save_queue()

                return item


        return None


    # =====================================================
    # Increment Retry Count
    # =====================================================

    def increment_retry(
        self,
        topic
    ):

        """
        Increase retry count for a topic.

        Used for temporary failures such as:
            - network failure
            - source retrieval failure
            - temporary API failure

        The topic should NOT be discarded simply because
        an external service temporarily failed.
        """

        normalized_topic = (
            self._normalize_topic(
                topic
            )
        )


        for item in self.queue:

            existing_topic = (
                self._normalize_topic(
                    item.get(
                        "topic",
                        ""
                    )
                )
            )

            if (
                existing_topic
                == normalized_topic
            ):

                item["retry_count"] = (
                    item.get(
                        "retry_count",
                        0
                    ) + 1
                )

                item["status"] = "RETRY"

                item["updated_at"] = (
                    datetime.utcnow()
                    .isoformat()
                )

                self._save_queue()

                return item


        return None


    # =====================================================
    # Remove Topic
    # =====================================================

    def remove_topic(
        self,
        topic
    ):

        """
        Permanently remove a topic from the queue.

        Normally this should be used only after the topic
        has been completed or discarded.
        """

        normalized_topic = (
            self._normalize_topic(
                topic
            )
        )


        original_length = len(
            self.queue
        )


        self.queue = [

            item

            for item in self.queue

            if self._normalize_topic(
                item.get(
                    "topic",
                    ""
                )
            ) != normalized_topic

        ]


        if len(
            self.queue
        ) != original_length:

            self._save_queue()

            return True


        return False


    # =====================================================
    # Clear Completed / Discarded Topics
    # =====================================================

    def cleanup(
        self
    ):

        """
        Remove topics that have already been
        completed or discarded.
        """

        self.queue = [

            item

            for item in self.queue

            if item.get(
                "status"
            ) not in {

                "COMPLETED",
                "DISCARDED"

            }

        ]

        self._save_queue()


    # =====================================================
    # Queue Size
    # =====================================================

    def size(
        self
    ):

        return len(
            self.queue
        )


# =========================================================
# Standalone Test
# =========================================================

if __name__ == "__main__":

    print()
    print("=" * 60)
    print("TruthLens Expansion Queue Test")
    print("=" * 60)


    queue = ExpansionQueue()


    # ---------------------------------------------
    # Test 1: Add Topic
    # ---------------------------------------------

    topic = (
        "SpaceX reported a loss of $541 million."
    )

    item = queue.add_topic(
        topic
    )

    print()
    print("Added Topic:")
    print(
        item
    )


    # ---------------------------------------------
    # Test 2: Duplicate Topic
    # ---------------------------------------------

    duplicate = queue.add_topic(
        "  SpaceX reported a loss of $541 million.  "
    )

    print()
    print("Duplicate Result:")
    print(
        duplicate
    )

    print()
    print(
        f"Queue Size: {queue.size()}"
    )


    # ---------------------------------------------
    # Test 3: Pending Topics
    # ---------------------------------------------

    print()
    print("Pending Topics:")

    for pending in (
        queue.get_pending_topics()
    ):

        print(
            f"- {pending['topic']}"
        )


    # ---------------------------------------------
    # Test 4: Processing
    # ---------------------------------------------

    queue.update_status(
        topic,
        "PROCESSING"
    )

    print()
    print(
        "Status changed to PROCESSING."
    )


    # ---------------------------------------------
    # Test 5: Temporary Failure
    # ---------------------------------------------

    queue.increment_retry(
        topic
    )

    print()
    print(
        "Temporary failure simulated."
    )


    # ---------------------------------------------
    # Test 6: Discard
    # ---------------------------------------------

    queue.update_status(
        topic,
        "DISCARDED"
    )

    print()
    print(
        "Topic marked as DISCARDED."
    )


    print()
    print("=" * 60)
    print("Expansion Queue Test Complete")
    print("=" * 60)