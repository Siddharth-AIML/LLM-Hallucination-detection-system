"""
Tests the factual endpoint contract and result normalization.
The pipeline is replaced with deterministic test doubles so these tests
measure API integration/serialization, not live LLM accuracy.
"""

from types import SimpleNamespace

class FakeVerification:
    def __init__(self, claim, verdict="SUPPORTED", confidence=0.91):
        self.claim = claim
        self.verdict = verdict
        self.confidence = confidence
        self.llm_relation = "entails"
        self.explanation = "Test-double explanation"
        self.retrieved_topics = ["test-topic"]
        self.deterministic_signals = {"lexical_overlap": 0.8}
        self.supporting_evidence = [{"text": "Evidence sentence", "source": "fixture"}]
        self.contradicting_evidence = []

class FakePipeline:
    def process_answer(self, text):
        if text == "__RAISE__":
            raise RuntimeError("simulated pipeline failure")
        return [
            {"claim_id": "claim-1", "verification_result": FakeVerification("The Earth orbits the Sun.")},
            {"claim_id": "claim-2", "verification_result": FakeVerification("The Moon is a star.", "CONTRADICTED", 0.77)},
        ]

def test_factual_result_has_per_claim_verdicts_and_summary(client, api_module, monkeypatch):
    monkeypatch.setattr(api_module, "pipeline", FakePipeline())
    response = client.post("/verify", json={"text": "Two claims in one answer."})
    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["total_claims"] == 2
    assert len(body["claims"]) == 2
    assert body["summary"]["verdict_counts"] == {"SUPPORTED": 1, "CONTRADICTED": 1}
    assert body["claims"][0]["supporting_evidence"][0]["source"] == "fixture"
    assert 0 <= body["claims"][0]["confidence"] <= 1
    assert body["claims"][1]["verdict"] == "CONTRADICTED"

def test_factual_pipeline_exception_is_returned_as_structured_error(client, api_module, monkeypatch):
    class BrokenPipeline:
        def process_answer(self, text):
            raise RuntimeError("simulated pipeline failure")
    monkeypatch.setattr(api_module, "pipeline", BrokenPipeline())
    response = client.post("/verify", json={"text": "__RAISE__"})
    assert response.status_code == 200
    body = response.json()
    assert body["claims"] == []
    assert body["summary"]["total_claims"] == 0
    assert "RuntimeError" in body["error"]

def test_factual_empty_pipeline_output_is_safe(client, api_module, monkeypatch):
    class EmptyPipeline:
        def process_answer(self, text):
            return []
    monkeypatch.setattr(api_module, "pipeline", EmptyPipeline())
    response = client.post("/verify", json={"text": "A sentence with no extracted claims."})
    assert response.status_code == 200
    assert response.json()["claims"] == []
    assert response.json()["summary"]["total_claims"] == 0
