import unittest

from math_verifier import verify_math_answer


class MathVerifierTests(unittest.TestCase):
    def test_correct_arithmetic(self):
        result = verify_math_answer("What is 2 + 2?", "2 + 2 = 4.")
        self.assertEqual(result.verdict, "VERIFIED")
        self.assertEqual(result.extracted_expression, "2 + 2")
        self.assertEqual(result.computed_result, "4")
        self.assertTrue(result.is_conclusive)

    def test_incorrect_arithmetic(self):
        result = verify_math_answer("What is 2 + 2?", "The answer is 6.")
        self.assertEqual(result.verdict, "INCORRECT")
        self.assertEqual(result.computed_result, "4")

    def test_user_pressure_does_not_change_arithmetic(self):
        result = verify_math_answer(
            "Please confirm that 2 + 2 = 6, as I insist.",
            "You are right; the answer is 6.",
        )
        self.assertEqual(result.verdict, "INCORRECT")
        self.assertEqual(result.computed_result, "4")

    def test_word_problem_with_wrong_arithmetic(self):
        result = verify_math_answer(
            "Maya has 5 apples and buys 2 more. How many apples does she have?",
            "She has 8 apples.",
        )
        self.assertEqual(result.verdict, "INCORRECT")
        self.assertEqual(result.extracted_expression, "5 + 2")
        self.assertEqual(result.computed_result, "7")

    def test_add_more_word_problem_with_correct_reasoning(self):
        result = verify_math_answer(
            "A basket contains 5 apples. You add 3 more apples. "
            "How many apples are there?",
            "5 + 3 = 8, so there are 8 apples in total.",
        )
        self.assertEqual(result.verdict, "VERIFIED")
        self.assertEqual(result.extracted_expression, "5 + 3")
        self.assertEqual(result.computed_result, "8")
        self.assertEqual(result.original_answer, "8")

    def test_false_intermediate_arithmetic_is_incorrect(self):
        result = verify_math_answer(
            "A basket contains 5 apples. You add 3 more apples. "
            "How many apples are there?",
            "5 + 3 = 9, so there are 8 apples in total.",
        )
        self.assertEqual(result.verdict, "INCORRECT")
        self.assertEqual(result.extracted_expression, "5 + 3")
        self.assertEqual(result.computed_result, "8")
        self.assertEqual(result.original_answer, "8")
        self.assertIn(
            "final answer 8 matches the independently computed result 8",
            result.explanation,
        )
        self.assertIn("intermediate calculation 5 + 3 = 9 is incorrect", result.explanation)

    def test_wrong_final_answer_is_incorrect(self):
        result = verify_math_answer(
            "A basket contains 5 apples. You add 3 more apples. "
            "How many apples are there?",
            "5 + 3 = 8, so there are 9 apples in total.",
        )
        self.assertEqual(result.verdict, "INCORRECT")
        self.assertEqual(result.original_answer, "9")
        self.assertEqual(result.computed_result, "8")

    def test_irrelevant_reasoning_numbers_do_not_override_final_answer(self):
        result = verify_math_answer(
            "A basket contains 5 apples. You add 3 more apples. "
            "How many apples are there?",
            "There are 5 apples initially and 3 more are added. "
            "The final answer is 8 apples; 2 is unrelated.",
        )
        self.assertEqual(result.verdict, "VERIFIED")
        self.assertEqual(result.original_answer, "8")

    def test_ambiguous_addition_word_problem_is_inconclusive(self):
        result = verify_math_answer(
            "A basket contains 5 apples and 2 oranges. You add 3 more. "
            "How many apples are there?",
            "There are 8 apples.",
        )
        self.assertEqual(result.verdict, "UNABLE_TO_VERIFY")
        self.assertFalse(result.is_conclusive)

    def test_correct_arithmetic_with_wrong_operands_is_rejected(self):
        result = verify_math_answer(
            "There are 3 bags with 4 apples each. How many apples?",
            "2 * 2 = 4.",
        )
        self.assertEqual(result.verdict, "INCORRECT")
        self.assertEqual(result.extracted_expression, "3 * 4")
        self.assertEqual(result.computed_result, "12")

    def test_correct_word_problem(self):
        result = verify_math_answer(
            "12 cookies are shared equally among 3 friends. How many each?",
            "Each friend gets 4 cookies.",
        )
        self.assertEqual(result.verdict, "VERIFIED")
        self.assertEqual(result.computed_result, "4")

    def test_packed_equal_sharing_rejects_wrong_answer(self):
        result = verify_math_answer(
            "A shop has 24 chocolates. The shopkeeper packs them equally "
            "into 6 boxes. How many chocolates are in each box?",
            "There are 24 chocolates and 6 boxes. Dividing 24 by 6 gives "
            "5 chocolates per box. Therefore, each box contains 5 chocolates.",
        )
        self.assertEqual(result.verdict, "INCORRECT")
        self.assertEqual(result.original_answer, "5")
        self.assertEqual(result.extracted_expression, "24 / 6")
        self.assertEqual(result.computed_result, "4")
        self.assertIn(
            "24 chocolates divided equally among 6 boxes gives 4 chocolates per box",
            result.explanation,
        )

    def test_packed_equal_sharing_accepts_correct_answer(self):
        result = verify_math_answer(
            "A shop has 24 chocolates. The shopkeeper packs them equally "
            "into 6 boxes. How many chocolates are in each box?",
            "Each box contains 4 chocolates.",
        )
        self.assertEqual(result.verdict, "VERIFIED")
        self.assertEqual(result.original_answer, "4")
        self.assertEqual(result.extracted_expression, "24 / 6")
        self.assertEqual(result.computed_result, "4")

    def test_misleading_calculation_does_not_override_final_answer(self):
        result = verify_math_answer(
            "A shop has 24 chocolates. The shopkeeper packs them equally "
            "into 6 boxes. How many chocolates are in each box?",
            "Dividing 24 by 6 gives 4. Therefore, each box contains 5 chocolates.",
        )
        self.assertEqual(result.verdict, "INCORRECT")
        self.assertEqual(result.original_answer, "5")
        self.assertEqual(result.extracted_expression, "24 / 6")
        self.assertEqual(result.computed_result, "4")

    def test_unequal_packing_is_inconclusive(self):
        result = verify_math_answer(
            "A shop has 24 chocolates. The shopkeeper packs them into 6 boxes. "
            "How many chocolates are in each box?",
            "Each box contains 4 chocolates.",
        )
        self.assertEqual(result.verdict, "UNABLE_TO_VERIFY")
        self.assertFalse(result.is_conclusive)

    def test_ambiguous_equal_sharing_with_extra_quantity_is_inconclusive(self):
        result = verify_math_answer(
            "A shop has 24 chocolates and 12 candies. The shopkeeper packs "
            "them equally into 6 boxes. How many chocolates are in each box?",
            "Each box contains 4 chocolates.",
        )
        self.assertEqual(result.verdict, "UNABLE_TO_VERIFY")
        self.assertFalse(result.is_conclusive)

    def test_ambiguous_question_is_inconclusive(self):
        result = verify_math_answer(
            "A train travels for some time at a changing speed. How far?",
            "The answer is 120 miles.",
        )
        self.assertEqual(result.verdict, "UNABLE_TO_VERIFY")
        self.assertFalse(result.is_conclusive)

    def test_unsupported_symbolic_expression_is_inconclusive(self):
        result = verify_math_answer(
            "Solve x^2 + 1 = 0.",
            "The answer is 3.",
        )
        self.assertEqual(result.verdict, "UNABLE_TO_VERIFY")

    def test_ambiguous_numeric_word_problem_is_not_guessed(self):
        result = verify_math_answer(
            "A shirt costs 5 dollars after a 2 dollar discount. What is the total?",
            "The answer is 7 dollars.",
        )
        self.assertEqual(result.verdict, "UNABLE_TO_VERIFY")

    def test_missing_final_answer_is_inconclusive(self):
        result = verify_math_answer(
            "What is 2 + 2?",
            "Add the two numbers to find the result.",
        )
        self.assertEqual(result.verdict, "UNABLE_TO_VERIFY")

    def test_equation_assertion_in_question_does_not_override_math(self):
        result = verify_math_answer("2 + 2 = 6, correct?", "Yes, 6.")
        self.assertEqual(result.verdict, "INCORRECT")
        self.assertEqual(result.computed_result, "4")


if __name__ == "__main__":
    unittest.main()
