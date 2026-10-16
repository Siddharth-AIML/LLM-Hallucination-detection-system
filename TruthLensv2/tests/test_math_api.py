import importlib
import sys
import types
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient


class MathApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pipeline_stub = types.ModuleType("pipeline")
        pipeline_stub.TruthLensPipeline = lambda: object()
        with patch.dict(sys.modules, {"pipeline": pipeline_stub}):
            sys.modules.pop("api", None)
            cls.api = importlib.import_module("api")
        cls.client = TestClient(cls.api.app)

    def test_valid_request(self):
        response = self.client.post(
            "/verify/math",
            json={"question": "What is 2 + 2?", "answer": "4"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["verdict"], "VERIFIED")
        self.assertEqual(response.json()["computed_result"], "4")

    def test_blank_question_is_rejected(self):
        response = self.client.post(
            "/verify/math",
            json={"question": "   ", "answer": "4"},
        )
        self.assertEqual(response.status_code, 422)

    def test_inconclusive_question_is_returned(self):
        response = self.client.post(
            "/verify/math",
            json={
                "question": "How far did the train travel?",
                "answer": "120 miles",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["verdict"], "UNABLE_TO_VERIFY")
        self.assertFalse(response.json()["is_conclusive"])

    def test_existing_factual_route_remains_available(self):
        self.api.pipeline = types.SimpleNamespace(
            process_answer=lambda text: []
        )
        response = self.client.post("/verify", json={"text": "A factual claim."})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["input_text"], "A factual claim.")
        self.assertEqual(response.json()["claims"], [])

    def test_existing_demo_ui_is_still_served(self):
        page = self.client.get("/")
        script = self.client.get("/script.js")
        self.assertEqual(page.status_code, 200)
        self.assertIn("Math verification", page.text)
        self.assertEqual(script.status_code, 200)
        self.assertIn("async function verifyMath()", script.text)


if __name__ == "__main__":
    unittest.main()
