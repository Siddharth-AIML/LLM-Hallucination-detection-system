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


if __name__ == "__main__":
    unittest.main()
