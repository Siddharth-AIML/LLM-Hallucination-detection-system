"""
TruthLens V2

End-to-End Claim Verification Pipeline

Pipeline:

LLM Answer
    ↓
Rich Claim Extraction
    ↓
Independent Claims
    ↓
Hybrid Retrieval
    ↓
Verification
    ↓
Independent Verification Results
"""

from claim_processing.claim_processor import (
    RichClaimExtractor
)

from retrieval.hybrid_retrieval import (
    HybridRetriever
)

from verification.verifier import (
    Verifier,
    VerificationResult
)


class TruthLensPipeline:

    def __init__(self):

        print()
        print("=" * 60)
        print("Loading TruthLens Pipeline...")
        print("=" * 60)

        # -----------------------------------------
        # Claim Extraction
        # -----------------------------------------

        self.claim_extractor = (
            RichClaimExtractor()
        )

        # -----------------------------------------
        # Evidence Retrieval
        # -----------------------------------------

        self.retriever = (
            HybridRetriever()
        )

        self.retriever.build_faiss_index()

        self.retriever.build_bm25_index()

        # -----------------------------------------
        # Verification
        # -----------------------------------------

        self.verifier = (
            Verifier()
        )

        print()
        print("TruthLens Pipeline Ready.")
        print()


    # =====================================================
    # Process Answer
    # =====================================================

    def process_answer(
        self,
        answer: str
    ):

        """
        Process one complete LLM answer.

        Every extracted claim is processed
        independently.

        No aggregate verdict is produced.
        """

        # -----------------------------------------
        # Step 1
        # Claim Extraction
        # -----------------------------------------

        claims = (
            self.claim_extractor.extract_claims(
                answer
            )
        )

        if not claims:

            print(
                "No factual claims were extracted."
            )

            return []


        results = []


        # -----------------------------------------
        # Step 2
        # Process Each Claim Independently
        # -----------------------------------------

        for claim_number, extracted_claim in enumerate(
            claims,
            start=1
        ):

            print()
            print("=" * 60)
            print(
                f"Processing Claim {claim_number}"
            )
            print("=" * 60)

            claim_text = (
                extracted_claim.resolved_text
            )

            print(
                f"Claim : {claim_text}"
            )

            # -------------------------------------
            # Step 3
            # Hybrid Retrieval
            # -------------------------------------

            retrieval_result = (
                self.retriever.retrieve(
                    claim_text
                )
            )

            # -------------------------------------
            # Step 4
            # Verification
            # -------------------------------------

            verification_result = (
                self.verifier.verify(
                    claim_text,
                    retrieval_result
                )
            )

            results.append(
                {
                    "claim_id": (
                        extracted_claim.claim_id
                    ),
                    "extracted_claim": (
                        extracted_claim
                    ),
                    "retrieval_result": (
                        retrieval_result
                    ),
                    "verification_result": (
                        verification_result
                    )
                }
            )

            # -------------------------------------
            # Step 5
            # Print Individual Result
            # -------------------------------------

            self.verifier.print_result(
                verification_result
            )

        return results


    # =====================================================
    # Print Complete Pipeline Results
    # =====================================================

    def print_results(
        self,
        results
    ):

        print()
        print("=" * 60)
        print("TruthLens Final Results")
        print("=" * 60)

        for index, item in enumerate(
            results,
            start=1
        ):

            verification = (
                item["verification_result"]
            )

            print()

            print(
                f"Claim {index}:"
            )

            print(
                f"{verification.claim}"
            )

            print(
                f"Verdict    : "
                f"{verification.verdict}"
            )

            print(
                f"Confidence : "
                f"{verification.confidence:.4f}"
            )

            print(
                "-" * 60
            )


# =========================================================
# Standalone Test
# =========================================================

if __name__ == "__main__":

    pipeline = TruthLensPipeline()

    print()
    print("=" * 60)
    print("TruthLens End-to-End Test")
    print("=" * 60)

    while True:

        answer = input(
            "\nEnter Answer (or 'exit'): "
        ).strip()

        if answer.lower() == "exit":

            break

        if not answer:

            continue

        results = (
            pipeline.process_answer(
                answer
            )
        )

        pipeline.print_results(
            results
        )