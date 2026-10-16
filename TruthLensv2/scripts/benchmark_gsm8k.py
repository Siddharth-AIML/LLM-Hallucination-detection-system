"""Opt-in GSM8K benchmark; streams the chosen official split."""

import argparse
import csv
import json
import logging
import os
import re
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from math_verifier import verify_math_answer


LOGGER = logging.getLogger("gsm8k_benchmark")


def _numeric_answer(text):
    marker = "####"
    if marker in text:
        text = text.rsplit(marker, 1)[1]
    else:
        for pattern in (
            r"\b(?:final answer|answer|result|total)\s*(?:is|:|=)\s*"
            r"\$?\s*(-?\d[\d,]*(?:\.\d+)?)",
            r"=\s*\$?\s*(-?\d[\d,]*(?:\.\d+)?)\s*[.!?]?\s*$",
            r"(?<![\w.])\$?\s*(-?\d[\d,]*(?:\.\d+)?)\s*%?"
            r"(?:\s+[A-Za-z][A-Za-z-]*){0,3}\s*[.!?]?\s*$",
        ):
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                text = matches[-1]
                break
    text = text.strip().replace(",", "").replace("$", "")
    try:
        return float(text)
    except ValueError:
        return None


def _ask_groq(client, model, question):
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "Solve the math word problem. Explain briefly and end "
                    "with the final numeric answer."
                ),
            },
            {"role": "user", "content": question},
        ],
        temperature=0,
    )
    return response.choices[0].message.content or ""


def _metrics(rows):
    true_positive = sum(
        row["baseline_incorrect"] and row["detected_incorrect"] for row in rows
    )
    false_positive = sum(
        not row["baseline_incorrect"] and row["detected_incorrect"]
        for row in rows
    )
    false_negative = sum(
        row["baseline_incorrect"] and not row["detected_incorrect"]
        for row in rows
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
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall
        else 0.0
    )
    evaluated = [
        row
        for row in rows
        if row["failure"] == "" and row["ground_truth"] is not None
    ]
    return {
        "samples": len(rows),
        "evaluated_samples": len(evaluated),
        "baseline_accuracy": (
            sum(row["baseline_correct"] for row in evaluated) / len(evaluated)
            if evaluated
            else 0.0
        ),
        "accuracy_after_verification": (
            sum(row["after_verification_correct"] for row in evaluated)
            / len(evaluated)
            if evaluated
            else 0.0
        ),
        "incorrect_answer_detection_precision": precision,
        "incorrect_answer_detection_recall": recall,
        "incorrect_answer_detection_f1": f1,
        "unverified_cases": sum(
            row["verdict"] == "UNABLE_TO_VERIFY" for row in evaluated
        ),
        "execution_failures": sum(bool(row["failure"]) for row in rows),
        "detection_counts": {
            "true_positive": true_positive,
            "false_positive": false_positive,
            "false_negative": false_negative,
        },
    }


def run_benchmark(split, limit, model, output):
    try:
        from datasets import load_dataset
        from groq import Groq
    except ImportError as error:
        raise RuntimeError(
            "Benchmark dependencies are missing. Install "
            "'datasets' and 'groq' before running this script."
        ) from error

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("Set GROQ_API_KEY to run the LLM benchmark.")

    client = Groq(api_key=api_key)
    dataset = load_dataset(
        "openai/gsm8k", "main", split=split, streaming=True
    )
    records = []
    for index, sample in enumerate(dataset):
        if limit is not None and index >= limit:
            break
        question = sample["question"]
        expected = _numeric_answer(sample["answer"])
        record = {
            "index": index,
            "question": question,
            "ground_truth": expected,
            "llm_answer": "",
            "verdict": "",
            "computed_result": "",
            "expression": "",
            "verification_status": "",
            "explanation": "",
            "corrected_answer": "",
            "baseline_correct": False,
            "baseline_incorrect": False,
            "detected_incorrect": False,
            "after_verification_correct": False,
            "failure": "",
        }
        try:
            llm_answer = _ask_groq(client, model, question)
            result = verify_math_answer(question, llm_answer)
            baseline = _numeric_answer(result.original_answer or "")
            baseline_correct = (
                baseline is not None
                and expected is not None
                and baseline == expected
            )
            corrected_answer = (
                result.computed_result
                if result.verdict == "INCORRECT"
                else (result.original_answer or "")
            )
            after = _numeric_answer(corrected_answer)
            record.update(
                {
                    "llm_answer": llm_answer,
                    "verdict": result.verdict,
                    "computed_result": result.computed_result or "",
                    "expression": result.extracted_expression or "",
                    "verification_status": result.verification_status,
                    "explanation": result.explanation,
                    "corrected_answer": corrected_answer,
                    "baseline_correct": baseline_correct,
                    "baseline_incorrect": (
                        expected is not None
                        and not baseline_correct
                    ),
                    "detected_incorrect": result.verdict == "INCORRECT",
                    "after_verification_correct": (
                        after is not None
                        and expected is not None
                        and after == expected
                    ),
                }
            )
        except Exception as error:
            LOGGER.exception("Benchmark sample %d failed", index)
            record["failure"] = type(error).__name__ + ": " + str(error)
        records.append(record)

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(records[0]) if records else [
        "index", "question", "ground_truth", "llm_answer", "verdict",
        "computed_result", "corrected_answer", "baseline_correct",
        "expression", "verification_status", "explanation",
        "baseline_incorrect", "detected_incorrect",
        "after_verification_correct", "failure",
    ]
    with output.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    summary = {
        "dataset": "openai/gsm8k",
        "split": split,
        "model": model,
        "limit": limit,
        "metrics": _metrics(records),
    }
    summary_path = output.with_suffix(".summary.json")
    summary_path.write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    return summary, summary_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=("train", "test"), default="test")
    parser.add_argument(
        "--limit", type=int, default=100,
        help="Maximum streaming examples (default: 100; use 0 for no limit).",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("GROQ_MODEL_NAME", "openai/gpt-oss-120b"),
        help="Groq model name; defaults to GROQ_MODEL_NAME or TruthLens' model.",
    )
    parser.add_argument(
        "--output", default="gsm8k_results.csv",
        help="CSV path for per-example benchmark details.",
    )
    args = parser.parse_args()
    if args.limit < 0:
        parser.error("--limit must be zero or a positive integer")
    limit = args.limit or None
    summary, summary_path = run_benchmark(
        args.split, limit, args.model, args.output
    )
    print(json.dumps(summary, indent=2))
    print("Detailed results:", args.output)
    print("Summary:", summary_path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
