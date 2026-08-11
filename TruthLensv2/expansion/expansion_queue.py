"""
TruthLens V2

Knowledge Base Expansion Queue

Purpose:
    Stores claims/topics that could not be verified because
    sufficient information was not available in the current
    Knowledge Base.

The queue is connected to:
    - Topic Validator

The queue will later connect to:
    - Knowledge Expander
    - Knowledge Base Builder

Important:

    INVALID topics are discarded and NEVER enter the KB.

    RETRY topics remain in the queue and can be checked again
    during a future expansion cycle.

    VALIDATED topics have passed external validation and are
    ready for Knowledge Base expansion.
"""

import json
import os
from datetime import datetime

from expansion.topic_validator import TopicValidator


class ExpansionQueue:

    # =====================================================
    # Initialization
    # =====================================================

    def __init__(
        self,
        queue_file="data/expansion_queue.json",
        topic_validator=None
    ):

        self.queue_file = queue_file

        self._ensure_storage()

        self.queue = self._load_queue()

        # -------------------------------------------------
        # Existing Topic Validator
        # -------------------------------------------------

        self.topic_validator = (
            topic_validator
            if topic_validator is not None
            else TopicValidator()
        )


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

                data = json.load(
                    file
                )

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

        now = (
            datetime.utcnow()
            .isoformat()
        )

        item = {

            "topic": topic,

            "status": "PENDING",

            "created_at": now,

            "updated_at": now,

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
        Return all topics waiting for validation.
        """

        return [

            item

            for item in self.queue

            if item.get(
                "status"
            ) == "PENDING"

        ]


    # =====================================================
    # Get Validated Topics
    # =====================================================

    def get_validated_topics(
        self
    ):

        """
        Return topics that passed external validation
        and are waiting for Knowledge Base expansion.
        """

        return [

            item

            for item in self.queue

            if item.get(
                "status"
            ) == "VALIDATED"

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
            VALIDATED
            COMPLETED
            DISCARDED
            RETRY
        """

        valid_statuses = {

            "PENDING",
            "PROCESSING",
            "VALIDATED",
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
            - insufficient evidence requiring another cycle

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
    # Validate Pending Topic
    # =====================================================

    def validate_topic(
        self,
        topic
    ):

        """
        Validate one queued topic using TopicValidator V3.

        Flow:

            PENDING
                ↓
            PROCESSING
                ↓
            TopicValidator
                ↓
        ┌───────┼────────┐
        ↓       ↓        ↓
      VALID   INVALID   RETRY
        ↓       ↓        ↓
    VALIDATED DISCARDED RETRY
        """

        # -------------------------------------------------
        # Find Queue Item
        # -------------------------------------------------

        normalized_topic = (
            self._normalize_topic(
                topic
            )
        )

        queue_item = None

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

                queue_item = item
                break

        if queue_item is None:

            return {
                "topic": topic,
                "status": "INVALID",
                "reason":
                    "Topic does not exist in queue."
            }

        # -------------------------------------------------
        # Mark Processing
        # -------------------------------------------------

        queue_item["status"] = "PROCESSING"

        queue_item["updated_at"] = (
            datetime.utcnow()
            .isoformat()
        )

        self._save_queue()

        # -------------------------------------------------
        # Run Topic Validator
        # -------------------------------------------------

        try:

            validation_result = (
                self.topic_validator.validate_topic(
                    topic
                )
            )

        except Exception as error:

            # ---------------------------------------------
            # Temporary failure
            # ---------------------------------------------

            queue_item["retry_count"] = (
                queue_item.get(
                    "retry_count",
                    0
                ) + 1
            )

            queue_item["status"] = "RETRY"

            queue_item["updated_at"] = (
                datetime.utcnow()
                .isoformat()
            )

            queue_item[
                "validation_error"
            ] = str(error)

            self._save_queue()

            return {
                "topic": topic,
                "status": "RETRY",
                "reason":
                    "Topic validation failed.",
                "error": str(error)
            }

        # -------------------------------------------------
        # Read Validator Status
        # -------------------------------------------------

        validation_status = str(
            validation_result.get(
                "status",
                "RETRY"
            )
        ).upper()

        # =================================================
        # VALID
        # =================================================

        if validation_status == "VALID":

            queue_item["status"] = "VALIDATED"

            queue_item["updated_at"] = (
                datetime.utcnow()
                .isoformat()
            )

            queue_item[
                "validation"
            ] = validation_result

            self._save_queue()

            return validation_result

        # =================================================
        # INVALID
        # =================================================

        if validation_status == "INVALID":

            # -------------------------------------------------
            # IMPORTANT:
            #
            # Invalid topics are permanently marked DISCARDED.
            #
            # They must NEVER be passed to Knowledge Expander.
            # -------------------------------------------------

            queue_item["status"] = "DISCARDED"

            queue_item["updated_at"] = (
                datetime.utcnow()
                .isoformat()
            )

            queue_item[
                "validation"
            ] = validation_result

            self._save_queue()

            return validation_result

        # =================================================
        # RETRY
        # =================================================

        # Anything else from validator is treated as
        # temporary / insufficient evidence.

        queue_item["retry_count"] = (
            queue_item.get(
                "retry_count",
                0
            ) + 1
        )

        queue_item["status"] = "RETRY"

        queue_item["updated_at"] = (
            datetime.utcnow()
            .isoformat()
        )

        queue_item[
            "validation"
        ] = validation_result

        self._save_queue()

        return validation_result


    # =====================================================
    # Process Pending Topics
    # =====================================================

    def process_pending_topics(
        self
    ):

        """
        Validate every PENDING topic.

        This method is designed for the future
        6-hour automation.

        It does NOT perform Knowledge Base expansion.

        It only performs:

            Queue
              ↓
            Validator
              ↓
        VALID / INVALID / RETRY

        Returns a list of validation results.
        """

        pending_topics = (
            self.get_pending_topics()
        )

        results = []

        for item in pending_topics:

            topic = item.get(
                "topic",
                ""
            )

            if not topic:

                continue

            result = (
                self.validate_topic(
                    topic
                )
            )

            results.append(
                result
            )

        return results


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

    print(
        "TruthLens Expansion Queue + "
        "Topic Validator Test"
    )

    print("=" * 60)

    queue = ExpansionQueue()

    # -----------------------------------------------------
    # Test Topic
    # -----------------------------------------------------

    topic = (
        "SpaceX reported a loss of $541 million."
    )

    # -----------------------------------------------------
    # Add Topic
    # -----------------------------------------------------

    item = queue.add_topic(
        topic
    )

    print()

    print(
        "Queue Item:"
    )

    print(
        item
    )

    # -----------------------------------------------------
    # Duplicate Test
    # -----------------------------------------------------

    duplicate = queue.add_topic(
        "  SpaceX reported a loss of $541 million.  "
    )

    print()

    print(
        "Duplicate Result:"
    )

    print(
        duplicate
    )

    print()

    print(
        f"Queue Size: {queue.size()}"
    )

    # -----------------------------------------------------
    # Pending Topics
    # -----------------------------------------------------

    print()

    print(
        "Pending Topics:"
    )

    for pending in (
        queue.get_pending_topics()
    ):

        print(
            f"- {pending['topic']}"
        )

    # -----------------------------------------------------
    # Validator Test
    # -----------------------------------------------------

    print()

    print(
        "Running Topic Validator..."
    )

    result = (
        queue.validate_topic(
            topic
        )
    )

    # -----------------------------------------------------
    # Validation Result
    # -----------------------------------------------------

    print()

    print(
        "Validation Result:"
    )

    print(
        f"Topic      : "
        f"{result.get('topic', topic)}"
    )

    print(
        f"Status     : "
        f"{result.get('status', '')}"
    )

    print(
        f"Relation   : "
        f"{result.get('llm_relation', 'NEUTRAL')}"
    )

    print(
        f"Confidence : "
        f"{result.get('confidence', 0.0):.4f}"
    )

    print(
        f"Reason     : "
        f"{result.get('reason', '')}"
    )

    # -----------------------------------------------------
    # Queue State After Validation
    # -----------------------------------------------------

    print()

    print(
        "Queue State After Validation:"
    )

    for item in queue.get_all_topics():

        print(
            item
        )

    # -----------------------------------------------------
    # Validated Topics
    # -----------------------------------------------------

    print()

    print(
        "Validated Topics:"
    )

    for item in queue.get_validated_topics():

        print(
            f"- {item['topic']}"
        )

    print()

    print("=" * 60)

    print(
        "Expansion Queue Test Complete"
    )

    print("=" * 60)