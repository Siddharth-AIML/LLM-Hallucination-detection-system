import unittest

from scripts.benchmark_gsm8k import _metrics, _numeric_answer


class Gsm8kBenchmarkTests(unittest.TestCase):
    def test_numeric_answer_extraction(self):
        self.assertEqual(_numeric_answer("Reasoning. #### 1,234"), 1234.0)
        self.assertEqual(_numeric_answer("The answer is 7 apples."), 7.0)

    def test_detection_metrics_and_accuracy(self):
        rows = [
            {
                "baseline_correct": False,
                "baseline_incorrect": True,
                "detected_incorrect": True,
                "after_verification_correct": True,
                "verdict": "INCORRECT",
                "failure": "",
                "ground_truth": 7,
            },
            {
                "baseline_correct": True,
                "baseline_incorrect": False,
                "detected_incorrect": False,
                "after_verification_correct": True,
                "verdict": "VERIFIED",
                "failure": "",
                "ground_truth": 4,
            },
            {
                "baseline_correct": False,
                "baseline_incorrect": False,
                "detected_incorrect": False,
                "after_verification_correct": False,
                "verdict": "",
                "failure": "TimeoutError",
                "ground_truth": 2,
            },
        ]

        metrics = _metrics(rows)

        self.assertEqual(metrics["evaluated_samples"], 2)
        self.assertEqual(metrics["baseline_accuracy"], 0.5)
        self.assertEqual(metrics["accuracy_after_verification"], 1.0)
        self.assertEqual(metrics["incorrect_answer_detection_f1"], 1.0)
        self.assertEqual(metrics["execution_failures"], 1)

    def test_detection_metrics_exclude_execution_failures_and_report_coverage(self):
        rows = [
            {
                "baseline_correct": False,
                "baseline_incorrect": True,
                "detected_incorrect": True,
                "after_verification_correct": True,
                "verdict": "INCORRECT",
                "failure": "",
                "ground_truth": 7,
                "baseline_extraction_failed": True,
                "verifier_extraction_failed": False,
                "model_calls": 1,
                "latency_ms": 25.0,
            },
            {
                "baseline_correct": False,
                "baseline_incorrect": True,
                "detected_incorrect": False,
                "after_verification_correct": False,
                "verdict": "UNABLE_TO_VERIFY",
                "failure": "",
                "ground_truth": 4,
                "baseline_extraction_failed": False,
                "verifier_extraction_failed": True,
                "model_calls": 0,
                "latency_ms": 15.0,
            },
            {
                "baseline_correct": False,
                "baseline_incorrect": True,
                "detected_incorrect": True,
                "after_verification_correct": False,
                "verdict": "INCORRECT",
                "failure": "TimeoutError",
                "ground_truth": 5,
                "baseline_extraction_failed": False,
                "verifier_extraction_failed": False,
                "model_calls": 0,
                "latency_ms": 0.0,
            },
        ]
        metrics = _metrics(rows)
        self.assertEqual(metrics["evaluated_samples"], 2)
        self.assertEqual(metrics["detection_counts"]["true_positive"], 1)
        self.assertEqual(metrics["detection_counts"]["false_negative"], 1)
        self.assertEqual(metrics["unverified_cases"], 1)
        self.assertEqual(metrics["execution_failures"], 1)
        self.assertEqual(metrics["baseline_answer_extraction_failures"], 1)
        self.assertEqual(metrics["verifier_answer_extraction_failures"], 1)
        self.assertEqual(metrics["model_calls"], 1)
        self.assertEqual(metrics["mean_latency_ms"], 20.0)


if __name__ == "__main__":
    unittest.main()
