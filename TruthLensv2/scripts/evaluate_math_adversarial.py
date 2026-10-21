"""Run the manually labelled, offline math-verification evaluation."""

import argparse
import json
from pathlib import Path

if __package__ in (None, ""):
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from math_verifier import verify_math_answer
from math_verifier.interpreter import InterpretationError


class _OfflineInterpreter:
    model_calls = 0

    def interpret(self, question):
        raise InterpretationError(
            "The manually labelled evaluation does not call a model."
        )


def evaluate_cases(cases):
    results = []
    failures = 0
    for case in cases:
        try:
            result = verify_math_answer(
                case["question"],
                case["answer"],
                interpreter=_OfflineInterpreter(),
            )
            results.append(
                {
                    "id": case["id"],
                    "expected_verdict": case["expected_verdict"],
                    "verdict": result.verdict,
                    "correct_verdict": (
                        result.verdict == case["expected_verdict"]
                    ),
                    "expression": result.extracted_expression,
                    "computed_result": result.computed_result,
                    "final_answer": result.original_answer,
                    "verification_status": result.verification_status,
                    "latency_ms": result.latency_ms,
                }
            )
        except Exception as error:
            failures += 1
            results.append(
                {
                    "id": case["id"],
                    "expected_verdict": case["expected_verdict"],
                    "verdict": "EXECUTION_FAILURE",
                    "correct_verdict": False,
                    "failure": type(error).__name__ + ": " + str(error),
                }
            )

    total = len(results)
    correct = sum(item["correct_verdict"] for item in results)
    incorrect_expected = [
        item
        for item in results
        if item["expected_verdict"] == "INCORRECT"
        and item["verdict"] != "EXECUTION_FAILURE"
    ]
    other_expected = [
        item
        for item in results
        if item["expected_verdict"] != "INCORRECT"
        and item["verdict"] != "EXECUTION_FAILURE"
    ]
    true_positive = sum(
        item["verdict"] == "INCORRECT" for item in incorrect_expected
    )
    false_negative = len(incorrect_expected) - true_positive
    false_positive = sum(
        item["verdict"] == "INCORRECT" for item in other_expected
    )
    precision = (
        true_positive / (true_positive + false_positive)
        if true_positive + false_positive
        else 0.0
    )
    recall = (
        true_positive / (true_positive + false_negative)
        if true_positive + false_negative
        else 0.0
    )
    return {
        "cases": total,
        "correct_verdicts": correct,
        "verdict_accuracy": correct / total if total else 0.0,
        "unverified_cases": sum(
            item["verdict"] == "UNABLE_TO_VERIFY" for item in results
        ),
        "execution_failures": failures,
        "incorrect_detection_precision": precision,
        "incorrect_detection_recall": recall,
        "incorrect_detection_f1": (
            2 * precision * recall / (precision + recall)
            if precision + recall
            else 0.0
        ),
        "results": results,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixture",
        default=str(
            Path(__file__).resolve().parents[1]
            / "tests"
            / "fixtures"
            / "math_adversarial.json"
        ),
        help="Path to manually labelled cases in JSON format.",
    )
    parser.add_argument(
        "--output",
        help="Optional JSON file for detailed results and aggregate metrics.",
    )
    args = parser.parse_args()

    cases = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
    report = evaluate_cases(cases)
    rendered = json.dumps(report, indent=2)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered + "\n", encoding="utf-8")
        print("Detailed evaluation saved to", output)
    print(rendered)


if __name__ == "__main__":
    main()
