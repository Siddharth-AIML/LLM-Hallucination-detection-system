"""Opt-in GSM8K benchmark; streams the chosen official split."""

import argparse
import csv
import json
import logging
import os
import re
import sys
import time
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
    evaluated = [
        row
        for row in rows
        if row["failure"] == "" and row["ground_truth"] is not None
    ]
    true_positive = sum(
        row["baseline_incorrect"] and row["detected_incorrect"]
        for row in evaluated
    )
    false_positive = sum(
        not row["baseline_incorrect"] and row["detected_incorrect"]
        for row in evaluated
    )
    false_negative = sum(
        row["baseline_incorrect"] and not row["detected_incorrect"]
        for row in evaluated
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
    successful = [row for row in rows if row["failure"] == ""]
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
        "baseline_answer_extraction_failures": sum(
            row.get("baseline_extraction_failed", False) for row in successful
        ),
        "verifier_answer_extraction_failures": sum(
            row.get("verifier_extraction_failed", False) for row in successful
        ),
        "model_calls": sum(row.get("model_calls", 0) for row in rows),
        "baseline_model_calls": sum(
            row.get("baseline_model_calls", 0) for row in rows
        ),
        "verification_model_calls": sum(
            row.get("verification_model_calls", 0) for row in successful
        ),
        "mean_latency_ms": (
            sum(row.get("latency_ms", 0.0) for row in successful)
            / len(successful)
            if successful
            else 0.0
        ),
        "mean_baseline_latency_ms": (
            sum(row.get("baseline_latency_ms", 0.0) for row in successful)
            / len(successful)
            if successful
            else 0.0
        ),
        "mean_verification_latency_ms": (
            sum(row.get("verification_latency_ms", 0.0) for row in successful)
            / len(successful)
            if successful
            else 0.0
        ),
        "abstention_rate": (
            sum(row["verdict"] == "UNABLE_TO_VERIFY" for row in evaluated)
            / len(evaluated)
            if evaluated
            else 0.0
        ),
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

    client = Groq(api_key=api_key, timeout=30.0, max_retries=0)
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
            "baseline_extraction_failed": False,
            "verifier_extraction_failed": False,
            "model_calls": 0,
            "latency_ms": 0.0,
            "baseline_model_calls": 0,
            "verification_model_calls": 0,
            "baseline_latency_ms": 0.0,
            "verification_latency_ms": 0.0,
            "failure": "",
        }
        try:
            baseline_started = time.perf_counter()
            record["baseline_model_calls"] = 1
            record["model_calls"] = 1
            llm_answer = _ask_groq(client, model, question)
            baseline_latency = round(
                (time.perf_counter() - baseline_started) * 1000, 2
            )
            record["llm_answer"] = llm_answer
            baseline = _numeric_answer(llm_answer)
            baseline_correct = (
                baseline is not None
                and expected is not None
                and baseline == expected
            )
            record.update(
                {
                    "baseline_correct": baseline_correct,
                    "baseline_incorrect": (
                        expected is not None and not baseline_correct
                    ),
                    "baseline_extraction_failed": baseline is None,
                    "baseline_latency_ms": baseline_latency,
                }
            )
            result = verify_math_answer(question, llm_answer)
            corrected_answer = (
                result.computed_result
                if result.verdict == "INCORRECT"
                and result.computed_result is not None
                else (baseline if baseline is not None else "")
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
                    "baseline_extraction_failed": baseline is None,
                    "verifier_extraction_failed": (
                        result.original_answer is None
                    ),
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
                    "model_calls": 1 + result.model_calls,
                    "latency_ms": result.latency_ms,
                    "baseline_model_calls": 1,
                    "verification_model_calls": result.model_calls,
                    "baseline_latency_ms": baseline_latency,
                    "verification_latency_ms": result.latency_ms,
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
        "after_verification_correct", "baseline_extraction_failed",
        "verifier_extraction_failed", "model_calls", "latency_ms",
        "baseline_model_calls", "verification_model_calls",
        "baseline_latency_ms", "verification_latency_ms", "failure",
    ]
    with output.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    summary = {
        "dataset": "openai/gsm8k",
        "configuration": "main",
        "split": split,
        "model": model,
        "limit": limit,
        "streaming": True,
        "test_split_policy": (
            "evaluation only; do not tune verifier or model on test results"
        ),
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
