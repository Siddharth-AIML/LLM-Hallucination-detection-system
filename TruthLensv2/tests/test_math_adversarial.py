import json
import unittest
from pathlib import Path
from unittest.mock import patch

from math_verifier import verify_math_answer
from math_verifier.interpreter import InterpretationError
from scripts.evaluate_math_adversarial import evaluate_cases


FIXTURE = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "math_adversarial.json"
)


class OfflineInterpreter:
    model_calls = 0

    def interpret(self, _question):
        if not _question:
            raise AssertionError("Questions passed to the interpreter are nonblank.")
        raise InterpretationError("Structured interpretation disabled in test.")


class AdversarialMathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def setUp(self):
        self.no_model = patch(
            "math_verifier.verifier.StructuredQuestionInterpreter",
            OfflineInterpreter,
        )
        self.no_model.start()
        self.addCleanup(self.no_model.stop)

    def test_manually_labelled_adversarial_cases(self):
        report = evaluate_cases(self.cases)
        self.assertEqual(report["execution_failures"], 0)
        self.assertEqual(report["correct_verdicts"], report["cases"])
        self.assertGreater(report["unverified_cases"], 0)

    def test_rejected_false_equation_does_not_count_as_endorsed(self):
        result = verify_math_answer(
            "A basket contains 5 apples. You add 3 more apples. "
            "How many apples are there?",
            'The claim "5 + 3 = 9" is wrong. The final answer is 8 apples.',
        )
        self.assertEqual(result.verdict, "VERIFIED")
        self.assertGreater(
            result.verification_coverage["assertions_excluded"], 0
        )

    def test_negated_claim_does_not_exclude_a_later_equation(self):
        result = verify_math_answer(
            "A basket contains 5 apples. You add 3 more apples. "
            "How many apples are there?",
            "This answer is not correct. 5 + 3 = 9, but the final answer is 8.",
        )
        self.assertEqual(result.verdict, "INCORRECT")
        self.assertEqual(result.original_answer, "8")


if __name__ == "__main__":
    unittest.main()
