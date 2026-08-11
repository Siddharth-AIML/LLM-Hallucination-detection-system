"""
TruthLens V2
Knowledge Expansion Scheduler

Purpose:
    Run the complete Knowledge Base expansion cycle automatically.

Flow:

    PENDING
        |
        v
    ExpansionQueue.process_pending_topics()
        |
        v
    TopicValidator
        |
        +---- VALID ----> VALIDATED
        |
        +---- INVALID --> DISCARDED
        |
        +---- RETRY ----> RETRY
        |
        v
    KnowledgeExpansionManager.process_validated_topics()
        |
        v
    KnowledgeCreationEngine
        |
        v
    KnowledgeManager
        |
        v
    knowledge_base.json

RETRY behavior:

    RETRY topics are eligible for another validation cycle.
    At the beginning of a later cycle:

        RETRY
          |
          +---- retry_count < MAX_VALIDATION_RETRIES
          |          |
          |          v
          |       PENDING
          |          |
          |          v
          |    TopicValidator
          |
          +---- retry_count >= MAX_VALIDATION_RETRIES
                     |
                     v
                 DISCARDED

Scheduling:
    - Normal mode: run one expansion cycle every 6 hours.
    - --once mode: run exactly one cycle immediately.

Important:
    - This file is an ORCHESTRATOR only.
    - It does not duplicate validation logic.
    - It does not duplicate KB creation logic.
    - It uses the existing ExpansionQueue and
      KnowledgeExpansionManager components.
    - Core logic of TopicValidator and
      KnowledgeExpansionManager is not changed here.
"""

import argparse
import time
from datetime import datetime

from expansion.expansion_queue import ExpansionQueue
from expansion.knowledge_expansion_manager import (
    KnowledgeExpansionManager
)


# =========================================================
# Configuration
# =========================================================

SIX_HOURS_SECONDS = 6 * 60 * 60

# Maximum number of validation attempts for a topic.
#
# retry_count represents completed retry transitions.
# A topic with retry_count < this value gets another
# validation opportunity.
MAX_VALIDATION_RETRIES = 3


class ExpansionScheduler:

    """
    Orchestrates the complete KB expansion cycle.

    One cycle:

        1. Re-activate eligible RETRY topics.
        2. Load PENDING topics.
        3. Validate them through ExpansionQueue/TopicValidator.
        4. Process VALIDATED topics through
           KnowledgeExpansionManager.
        5. Leave INVALID topics discarded.
        6. Leave RETRY topics for a future cycle.
    """

    def __init__(
        self,
        interval_seconds=SIX_HOURS_SECONDS
    ):
        self.interval_seconds = interval_seconds

        # Use the same queue file and KB paths that the
        # existing expansion components already use.
        self.queue = ExpansionQueue()

        self.manager = KnowledgeExpansionManager(
            queue=self.queue
        )

        self.cycle_count = 0

    # =====================================================
    # Retry Handling
    # =====================================================

    def _prepare_retry_topics(self):
        """
        Make eligible RETRY topics available to the normal
        PENDING -> TopicValidator pipeline.

        Important:
            We do not call TopicValidator directly here.

            RETRY -> PENDING
                     |
                     v
            queue.process_pending_topics()
                     |
                     v
               TopicValidator

        Topics that have reached the maximum validation
        retry limit are discarded and can never enter the KB.
        """

        all_topics = self.queue.get_all_topics()

        retry_topics = [
            item
            for item in all_topics
            if str(
                item.get("status", "")
            ).upper() == "RETRY"
        ]

        reactivated = []
        discarded = []

        for item in retry_topics:

            topic = str(
                item.get("topic", "")
            ).strip()

            if not topic:
                continue

            try:
                retry_count = int(
                    item.get(
                        "retry_count",
                        0
                    )
                )
            except (
                TypeError,
                ValueError
            ):
                retry_count = 0

            # -------------------------------------------------
            # Maximum retry protection
            # -------------------------------------------------

            if retry_count >= MAX_VALIDATION_RETRIES:

                try:

                    updated = self.queue.update_status(
                        topic,
                        "DISCARDED"
                    )

                    if updated is not None:
                        discarded.append(topic)

                except Exception as error:

                    print()
                    print(
                        f"Could not discard retry topic "
                        f"'{topic}': {error}"
                    )

                continue

            # -------------------------------------------------
            # Retry again
            # -------------------------------------------------

            try:

                updated = self.queue.update_status(
                    topic,
                    "PENDING"
                )

                if updated is not None:
                    reactivated.append(topic)

            except Exception as error:

                print()
                print(
                    f"Could not reactivate retry topic "
                    f"'{topic}': {error}"
                )

        if reactivated:

            print()
            print(
                "Retry topics reactivated for validation:"
            )

            for topic in reactivated:

                print(
                    f"  - {topic}"
                )

        if discarded:

            print()
            print(
                "Retry topics discarded after reaching "
                "maximum validation retries:"
            )

            for topic in discarded:

                print(
                    f"  - {topic}"
                )

        return {
            "reactivated": reactivated,
            "discarded": discarded
        }

    # =====================================================
    # Run One Expansion Cycle
    # =====================================================

    def run_cycle(self):
        """
        Execute one complete KB expansion cycle.

        Returns:
            Dictionary containing validation and expansion
            results.
        """

        self.cycle_count += 1

        started_at = datetime.now().isoformat(
            timespec="seconds"
        )

        print()
        print("=" * 70)
        print(
            f"TruthLens KB Expansion Cycle #{self.cycle_count}"
        )
        print("=" * 70)
        print(
            f"Started : {started_at}"
        )
        print()

        # -------------------------------------------------
        # Step 0: Reactivate eligible RETRY topics
        # -------------------------------------------------

        print("-" * 70)
        print("STEP 0 : Preparing RETRY topics")
        print("-" * 70)

        retry_preparation = (
            self._prepare_retry_topics()
        )

        # -------------------------------------------------
        # Step 1: Read current queue
        # -------------------------------------------------

        all_topics = self.queue.get_all_topics()

        pending_before = [
            item
            for item in all_topics
            if str(
                item.get("status", "")
            ).upper() == "PENDING"
        ]

        validated_before = [
            item
            for item in all_topics
            if str(
                item.get("status", "")
            ).upper() == "VALIDATED"
        ]

        retry_before = [
            item
            for item in all_topics
            if str(
                item.get("status", "")
            ).upper() == "RETRY"
        ]

        print()
        print(
            f"Pending topics before validation : "
            f"{len(pending_before)}"
        )

        print(
            f"Validated topics waiting for expansion : "
            f"{len(validated_before)}"
        )

        print(
            f"Retry topics : "
            f"{len(retry_before)}"
        )

        # -------------------------------------------------
        # Step 2: Validate PENDING topics
        # -------------------------------------------------

        validation_results = []

        if pending_before:

            print()
            print("-" * 70)
            print("STEP 1 : Validating PENDING topics")
            print("-" * 70)

            try:

                validation_results = (
                    self.queue.process_pending_topics()
                )

            except Exception as error:

                print()
                print(
                    "Validation stage failed:"
                )
                print(error)

        else:

            print()
            print(
                "No PENDING topics require validation."
            )

        # -------------------------------------------------
        # Step 3: Expand VALIDATED topics
        # -------------------------------------------------

        print()
        print("-" * 70)
        print("STEP 2 : Expanding VALIDATED topics")
        print("-" * 70)

        expansion_results = []

        try:

            expansion_results = (
                self.manager.process_validated_topics()
            )

        except Exception as error:

            print()
            print(
                "Knowledge expansion stage failed:"
            )
            print(error)

        # -------------------------------------------------
        # Step 4: Final queue state
        # -------------------------------------------------

        final_topics = self.queue.get_all_topics()

        pending_after = [
            item
            for item in final_topics
            if str(
                item.get("status", "")
            ).upper() == "PENDING"
        ]

        validated_after = [
            item
            for item in final_topics
            if str(
                item.get("status", "")
            ).upper() == "VALIDATED"
        ]

        completed_after = [
            item
            for item in final_topics
            if str(
                item.get("status", "")
            ).upper() == "COMPLETED"
        ]

        discarded_after = [
            item
            for item in final_topics
            if str(
                item.get("status", "")
            ).upper() == "DISCARDED"
        ]

        retry_after = [
            item
            for item in final_topics
            if str(
                item.get("status", "")
            ).upper() == "RETRY"
        ]

        print()
        print("=" * 70)
        print("EXPANSION CYCLE SUMMARY")
        print("=" * 70)

        print(
            f"Retry topics reactivated : "
            f"{len(retry_preparation['reactivated'])}"
        )

        print(
            f"Retry topics discarded   : "
            f"{len(retry_preparation['discarded'])}"
        )

        print(
            f"Validation results : "
            f"{len(validation_results)}"
        )

        print(
            f"Expansion results  : "
            f"{len(expansion_results)}"
        )

        print()
        print(
            f"PENDING    : {len(pending_after)}"
        )

        print(
            f"VALIDATED  : {len(validated_after)}"
        )

        print(
            f"COMPLETED  : {len(completed_after)}"
        )

        print(
            f"DISCARDED  : {len(discarded_after)}"
        )

        print(
            f"RETRY      : {len(retry_after)}"
        )

        print("=" * 70)

        return {
            "cycle": self.cycle_count,
            "started_at": started_at,
            "validation_results": validation_results,
            "expansion_results": expansion_results,
            "retry_preparation": retry_preparation,
            "queue": {
                "pending": len(pending_after),
                "validated": len(validated_after),
                "completed": len(completed_after),
                "discarded": len(discarded_after),
                "retry": len(retry_after),
            }
        }

    # =====================================================
    # Run Once
    # =====================================================

    def run_once(self):
        """
        Run exactly one expansion cycle.

        Useful for development and testing.
        """

        return self.run_cycle()

    # =====================================================
    # Run Forever
    # =====================================================

    def run_forever(self):
        """
        Run an expansion cycle every 6 hours.

        The process remains alive and wakes up every
        SIX_HOURS_SECONDS.
        """

        print()
        print("=" * 70)
        print("TruthLens KB Expansion Scheduler")
        print("=" * 70)
        print(
            "Mode : Every 6 hours"
        )
        print(
            "Interval : 21600 seconds"
        )
        print()
        print(
            "Press Ctrl+C to stop the scheduler."
        )
        print("=" * 70)

        # Run immediately when the scheduler starts.
        self.run_cycle()

        while True:

            print()
            print(
                "Next KB expansion cycle in 6 hours."
            )
            print(
                "Waiting..."
            )

            try:

                time.sleep(
                    self.interval_seconds
                )

            except KeyboardInterrupt:

                print()
                print(
                    "Scheduler stopped by user."
                )
                break

            self.run_cycle()


# =========================================================
# Command Line Interface
# =========================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "TruthLens V2 automatic Knowledge Base "
            "expansion scheduler."
        )
    )

    parser.add_argument(
        "--once",
        action="store_true",
        help=(
            "Run one expansion cycle immediately "
            "and exit."
        )
    )

    args = parser.parse_args()

    scheduler = ExpansionScheduler()

    if args.once:

        scheduler.run_once()

    else:

        try:

            scheduler.run_forever()

        except KeyboardInterrupt:

            print()
            print(
                "TruthLens KB Expansion Scheduler stopped."
            )


# =========================================================
# Module Entry Point
# =========================================================

if __name__ == "__main__":
    main()
