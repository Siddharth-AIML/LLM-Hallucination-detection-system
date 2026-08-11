"""
TruthLens V2
Knowledge Expansion Manager

Purpose:
    Take topics that have already passed TopicValidator and
    expand them into the Knowledge Base using the existing
    KnowledgeCreationEngine complete pipeline.

Architecture:

    Expansion Queue
          |
          v
       VALIDATED
          |
          v
    Knowledge Expansion Manager
          |
          v
    Build Documents
          |
          v
    KnowledgeCreationEngine.process_documents()
          |
          v
       build_topic()
          |
          +----------------------+
          |                      |
          v                      v
    Existing Topic          New Topic
          |                      |
       merge_topic()         create_topic()
          |                      |
          +----------+-----------+
                     |
                     v
              save_topic()
                     |
                     v
              KnowledgeManager
                     |
                     v
                    KB

Important:
    - TopicValidator is NOT called again for VALIDATED topics.
    - The validation result and its sources are taken from the queue.
    - KnowledgeCreationEngine.process_documents() is used instead
      of calling create_topic() directly, so existing-topic matching,
      merging, topic validation, and KB persistence remain inside
      the existing engine.
    - INVALID topics must never reach this manager.
"""

from pathlib import Path
from typing import Dict, List, Optional

from document_processing.document_processor import Document
from knowledge_base.knowledge_creation_engine import (
    KnowledgeCreationEngine
)
from knowledge_base.knowledge_manager import (
    KnowledgeManager
)
from expansion.expansion_queue import (
    ExpansionQueue
)


# =========================================================
# Project Paths
# =========================================================

PROJECT_ROOT = (
    Path(__file__).resolve().parent.parent
)

DATA_FOLDER = PROJECT_ROOT / "data"

QUEUE_FILE = DATA_FOLDER / "expansion_queue.json"

KNOWLEDGE_BASE_FILE = (
    DATA_FOLDER / "knowledge_base.json"
)


# =========================================================
# Knowledge Expansion Manager
# =========================================================

class KnowledgeExpansionManager:

    MAX_RETRIES = 3

    # IMPORTANT:
    # KnowledgeCreationEngine.clean_documents() requires
    # content length >= 50, so this manager uses the same
    # threshold before passing documents to the engine.
    MIN_DOCUMENT_CONTENT_LENGTH = 50

    VALIDATED_STATUS = "VALIDATED"
    PROCESSING_STATUS = "PROCESSING"
    COMPLETED_STATUS = "COMPLETED"
    RETRY_STATUS = "RETRY"
    DISCARDED_STATUS = "DISCARDED"

    # -----------------------------------------------------
    # Initialization
    # -----------------------------------------------------

    def __init__(
        self,
        queue_file: str = str(QUEUE_FILE),
        knowledge_base_file: str = str(KNOWLEDGE_BASE_FILE),
        queue: Optional[ExpansionQueue] = None,
        manager: Optional[KnowledgeManager] = None,
        engine: Optional[KnowledgeCreationEngine] = None
    ):
        self.queue_file = queue_file
        self.knowledge_base_file = knowledge_base_file

        self.queue = (
            queue
            if queue is not None
            else ExpansionQueue(queue_file)
        )

        self.manager = (
            manager
            if manager is not None
            else KnowledgeManager(
                knowledge_base_file
            )
        )

        self.engine = (
            engine
            if engine is not None
            else KnowledgeCreationEngine(
                self.manager
            )
        )

        self.last_results: List[Dict] = []

        print(
            "\nKnowledge Expansion Manager Initialized."
        )

    # =====================================================
    # Queue Helpers
    # =====================================================

    def queue_topic(self, topic: str):
        """
        Add a new topic to the expansion queue.

        New topics enter as PENDING and must be validated
        by ExpansionQueue/TopicValidator before expansion.
        """

        if not isinstance(topic, str):
            return None

        topic = topic.strip()

        if not topic:
            return None

        item = self.queue.add_topic(topic)

        print(
            f"\nExpansion Queue Topic : {topic}"
        )

        if item is not None:
            print(
                f"Queue Status          : "
                f"{item.get('status', 'UNKNOWN')}"
            )

        return item

    def get_validated_topics(self):
        """
        Return topics that have already passed validation.
        """

        return self.queue.get_validated_topics()

    def get_pending_topics(self):
        """
        Return topics that still require validation.

        This manager does not validate them.
        """

        return self.queue.get_pending_topics()

    def _update_queue_status(
        self,
        topic: str,
        status: str
    ):
        return self.queue.update_status(
            topic,
            status
        )

    # =====================================================
    # Source -> Document
    # =====================================================

    @classmethod
    def _source_to_document(
        cls,
        source: Dict,
        topic: str
    ) -> Optional[Document]:
        """
        Convert a validated TopicValidator source into
        the Document schema used by KnowledgeCreationEngine.
        """

        if not isinstance(source, dict):
            return None

        title = str(
            source.get("title", "") or ""
        ).strip()

        publisher = str(
            source.get(
                "publisher",
                source.get("provider", "")
            ) or ""
        ).strip()

        url = str(
            source.get(
                "link",
                source.get("url", "")
            ) or ""
        ).strip()

        published_date = str(
            source.get(
                "published_date",
                source.get("date", "")
            ) or ""
        ).strip()

        content = str(
            source.get("content", "") or ""
        ).strip()

        if len(content) < cls.MIN_DOCUMENT_CONTENT_LENGTH:
            content = str(
                source.get("description", "") or ""
            ).strip()

        if not content:
            content = title

        if not title:
            title = topic

        if not publisher:
            publisher = "External Source"

        # The Source schema used by the Knowledge Creation
        # Engine requires a usable URL.
        if not url:
            return None

        # The KnowledgeCreationEngine later removes documents
        # whose content is shorter than 50 characters.
        if len(content) < cls.MIN_DOCUMENT_CONTENT_LENGTH:
            return None

        return Document(
            title=title,
            content=content,
            publisher=publisher,
            url=url,
            published_date=published_date
        )

    # =====================================================
    # Build Documents
    # =====================================================

    def build_documents(
        self,
        topic: str,
        validation_result: Dict
    ) -> List[Document]:
        """
        Build Documents only from the sources already collected
        and validated by TopicValidator.

        No external search happens here.
        """

        sources = validation_result.get(
            "sources",
            []
        )

        documents = []
        seen_urls = set()

        for source in sources:

            document = self._source_to_document(
                source,
                topic
            )

            if document is None:
                continue

            normalized_url = (
                document.url.strip().lower()
            )

            if normalized_url in seen_urls:
                continue

            seen_urls.add(
                normalized_url
            )

            documents.append(document)

        return documents

    # =====================================================
    # Expand One VALIDATED Topic
    # =====================================================

    def expand_topic(
        self,
        queue_item: Dict
    ) -> Dict:
        """
        Expand one VALIDATED queue item.

        IMPORTANT:
            This does not call TopicValidator.

        It uses the validation result already stored in the
        queue item and passes the resulting Documents to
        KnowledgeCreationEngine.process_documents().
        """

        if not isinstance(queue_item, dict):

            return {
                "status": "FAILED",
                "reason": "Invalid queue item."
            }

        topic = str(
            queue_item.get("topic", "")
        ).strip()

        if not topic:

            return {
                "status": "FAILED",
                "reason": "Queue item contains an empty topic."
            }

        queue_status = str(
            queue_item.get("status", "")
        ).upper()

        if queue_status != self.VALIDATED_STATUS:

            return {
                "status": "SKIPPED",
                "topic": topic,
                "reason": (
                    "Only VALIDATED topics can enter "
                    "Knowledge Base expansion."
                )
            }

        print()
        print("=" * 60)
        print("Knowledge Expansion")
        print("=" * 60)

        print(
            f"Topic  : {topic}"
        )

        print(
            "Status : VALIDATED"
        )

        # -------------------------------------------------
        # Use stored validation result
        # -------------------------------------------------

        validation = queue_item.get(
            "validation"
        )

        if not isinstance(validation, dict):

            return self._handle_retry(
                topic,
                (
                    "VALIDATED topic has no stored "
                    "validation result."
                )
            )

        validation_status = str(
            validation.get(
                "status",
                ""
            )
        ).upper()

        if validation_status != "VALID":

            try:
                self._update_queue_status(
                    topic,
                    self.DISCARDED_STATUS
                )
            except Exception:
                pass

            return {
                "status": "DISCARDED",
                "topic": topic,
                "reason": (
                    "Queue status is VALIDATED but stored "
                    "validation result is not VALID."
                ),
                "validation": validation
            }

        print(
            f"Validation : {validation_status}"
        )

        print(
            f"Confidence : "
            f"{validation.get('confidence', 0.0):.4f}"
        )

        print(
            f"Sources    : "
            f"{validation.get('source_count', 0)}"
        )

        # -------------------------------------------------
        # Mark PROCESSING
        # -------------------------------------------------

        try:

            self._update_queue_status(
                topic,
                self.PROCESSING_STATUS
            )

        except Exception as error:

            return {
                "status": "FAILED",
                "topic": topic,
                "reason": (
                    "Unable to mark topic as PROCESSING: "
                    f"{error}"
                )
            }

        # -------------------------------------------------
        # Build Documents
        # -------------------------------------------------

        print(
            "Step 1 : Building validated source documents..."
        )

        documents = self.build_documents(
            topic,
            validation
        )

        print(
            f"Step 1 : Documents built = "
            f"{len(documents)}"
        )

        if not documents:

            return self._handle_retry(
                topic,
                (
                    "Validation succeeded, but no usable "
                    "documents were available for KB creation."
                ),
                validation
            )

        # -------------------------------------------------
        # KnowledgeCreationEngine
        # -------------------------------------------------

        print(
            "Step 2 : Calling Knowledge Creation Engine..."
        )

        try:

            # IMPORTANT:
            # Use process_documents(), not create_topic().
            #
            # process_documents() performs:
            #   build_topic()
            #       -> create_topic()
            #       -> existing-topic matching
            #       -> merge/create
            #   save_topic()
            #       -> TopicValidator
            #       -> KnowledgeManager
            #
            created_topic = (
                self.engine.process_documents(
                    documents
                )
            )

        except Exception as error:

            print(
                f"Step 2 ERROR : {error}"
            )

            return self._handle_retry(
                topic,
                (
                    "Knowledge Creation Engine failed: "
                    f"{error}"
                ),
                validation
            )

        if created_topic is None:

            return self._handle_retry(
                topic,
                (
                    "Knowledge Creation Engine did not "
                    "store a topic."
                ),
                validation
            )

        print(
            "Step 2 : Knowledge Creation Engine completed."
        )

        # -------------------------------------------------
        # IMPORTANT:
        #
        # process_documents() already calls:
        #
        #   save_topic()
        #       -> validate_topic()
        #       -> KnowledgeManager.add_topic/update_topic
        #
        # Therefore the Expansion Manager MUST NOT call
        # KnowledgeManager.save again here.
        # -------------------------------------------------

        try:

            self._update_queue_status(
                topic,
                self.COMPLETED_STATUS
            )

        except Exception as error:

            print(
                f"Queue completion warning : {error}"
            )

        print(
            "Step 3 : Knowledge Base updated."
        )

        print(
            "Queue Status : COMPLETED"
        )

        print("=" * 60)

        return {
            "status": "SUCCESS",
            "topic": topic,
            "validation": validation,
            "document_count": len(documents),
            "created_topic": created_topic
        }

    # =====================================================
    # Retry Handler
    # =====================================================

    def _handle_retry(
        self,
        topic: str,
        reason: str,
        validation: Optional[Dict] = None
    ) -> Dict:
        """
        Retry temporary KB-expansion failures.

        When the maximum retry count is reached, the topic
        is discarded and will not enter the KB.
        """

        queue_item = None

        for item in self.queue.get_all_topics():

            existing_topic = str(
                item.get("topic", "")
            ).strip().lower()

            if existing_topic == topic.strip().lower():

                queue_item = item
                break

        retry_count = 0

        if queue_item is not None:

            try:

                retry_count = int(
                    queue_item.get(
                        "retry_count",
                        0
                    )
                )

            except (
                TypeError,
                ValueError
            ):

                retry_count = 0

        if retry_count < self.MAX_RETRIES:

            try:

                updated = self.queue.increment_retry(
                    topic
                )

            except Exception:

                updated = None

            new_retry_count = (
                updated.get(
                    "retry_count",
                    retry_count + 1
                )
                if updated
                else retry_count + 1
            )

            result = {
                "status": "RETRY",
                "topic": topic,
                "retry_count": new_retry_count,
                "reason": reason
            }

            if validation is not None:
                result["validation"] = validation

            print(
                f"Expansion Retry : "
                f"{new_retry_count}/{self.MAX_RETRIES}"
            )

            print(
                f"Reason : {reason}"
            )

            return result

        try:

            self._update_queue_status(
                topic,
                self.DISCARDED_STATUS
            )

        except Exception:
            pass

        result = {
            "status": "DISCARDED",
            "topic": topic,
            "retry_count": retry_count,
            "reason": (
                "Maximum retry limit reached. "
                f"{reason}"
            )
        }

        if validation is not None:
            result["validation"] = validation

        print(
            "Expansion Discarded."
        )

        print(
            f"Reason : {result['reason']}"
        )

        return result

    # =====================================================
    # Process VALIDATED Topics
    # =====================================================

    def process_validated_topics(
        self,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        Process only VALIDATED topics.

        Validation has already happened in the queue stage.
        """

        validated = (
            self.get_validated_topics()
        )

        if limit is not None:

            validated = validated[
                :max(0, limit)
            ]

        print()
        print("=" * 60)
        print("Knowledge Expansion Manager")
        print("=" * 60)

        print(
            f"Validated Topics : {len(validated)}"
        )

        print()

        results = []

        for index, item in enumerate(
            validated,
            start=1
        ):

            print(
                f"Processing {index}/{len(validated)}"
            )

            try:

                result = self.expand_topic(
                    item
                )

            except Exception as error:

                topic = str(
                    item.get(
                        "topic",
                        ""
                    )
                ).strip()

                result = self._handle_retry(
                    topic,
                    (
                        "Unexpected expansion error: "
                        f"{error}"
                    ),
                    item.get("validation")
                )

            results.append(result)

        self.last_results = results

        print()
        print("=" * 60)
        print("Expansion Summary")
        print("=" * 60)

        print(
            "Successful : "
            + str(
                sum(
                    1
                    for result in results
                    if result.get("status") == "SUCCESS"
                )
            )
        )

        print(
            "Retry      : "
            + str(
                sum(
                    1
                    for result in results
                    if result.get("status") == "RETRY"
                )
            )
        )

        print(
            "Discarded  : "
            + str(
                sum(
                    1
                    for result in results
                    if result.get("status") == "DISCARDED"
                )
            )
        )

        print(
            "Skipped    : "
            + str(
                sum(
                    1
                    for result in results
                    if result.get("status") == "SKIPPED"
                )
            )
        )

        print("=" * 60)

        return results

    # =====================================================
    # Pending Topics
    # =====================================================

    def process_pending_topics(self):
        """
        Informational helper.

        PENDING topics belong to the validation stage.
        """

        pending = self.get_pending_topics()

        print()
        print(
            f"Pending Topics : {len(pending)}"
        )

        print(
            "Pending topics require TopicValidator "
            "before KB expansion."
        )

        return pending

    # =====================================================
    # Process One Topic
    # =====================================================

    def process_topic(
        self,
        topic: str
    ) -> Dict:
        """
        Process one topic only if it is already VALIDATED.
        """

        normalized = " ".join(
            str(topic).strip().lower().split()
        )

        for item in self.queue.get_all_topics():

            existing = " ".join(
                str(
                    item.get("topic", "")
                ).strip().lower().split()
            )

            if existing == normalized:

                return self.expand_topic(item)

        return {
            "status": "NOT_FOUND",
            "topic": topic,
            "reason":
                "Topic was not found in the expansion queue."
        }

    # =====================================================
    # Print Queue
    # =====================================================

    def print_queue(self):
        """
        Display the current expansion queue.
        """

        items = self.queue.get_all_topics()

        print()
        print("=" * 60)
        print("Expansion Queue")
        print("=" * 60)

        if not items:

            print(
                "Queue is empty."
            )

            print("=" * 60)

            return

        for index, item in enumerate(
            items,
            start=1
        ):

            print()
            print(
                f"[{index}] "
                f"{item.get('topic', '')}"
            )

            print(
                f"Status      : "
                f"{item.get('status', '')}"
            )

            print(
                f"Retry Count : "
                f"{item.get('retry_count', 0)}"
            )

            validation = item.get(
                "validation"
            )

            if validation:

                print(
                    f"Validation  : "
                    f"{validation.get('status', '')}"
                )

                print(
                    f"Confidence  : "
                    f"{validation.get('confidence', 0.0)}"
                )

        print()
        print("=" * 60)


# =========================================================
# Standalone Test
# =========================================================

if __name__ == "__main__":

    print()
    print("=" * 60)
    print(
        "TruthLens V2 Knowledge Expansion Manager Test"
    )
    print("=" * 60)

    manager = KnowledgeExpansionManager()

    manager.print_queue()

    validated = (
        manager.get_validated_topics()
    )

    print()
    print(
        f"Validated Topics : {len(validated)}"
    )

    if validated:

        print()
        print(
            "Starting VALIDATED-topic expansion..."
        )

        manager.process_validated_topics()

    else:

        pending = (
            manager.get_pending_topics()
        )

        print(
            f"Pending Topics   : {len(pending)}"
        )

        if pending:

            print(
                "\nThese topics still need validation."
            )

            print(
                "Run the Expansion Queue validation "
                "stage first."
            )

        else:

            print(
                "\nNo VALIDATED topics available "
                "for Knowledge Base expansion."
            )
