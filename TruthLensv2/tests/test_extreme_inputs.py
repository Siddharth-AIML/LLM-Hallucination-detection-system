"""Extreme-input tests for request boundaries and resilient handling."""

import pytest

BASE = {
    "question": "Explain the project.",
    "answer": "The project uses a modular architecture.",
    "context": "",
    "conversation_history": "",
    "instructions": "",
}

@pytest.mark.parametrize("payload", [
    {**BASE, "question": "x" * 4001},
    {**BASE, "answer": "x" * 12001},
    {**BASE, "context": "x" * 16001},
    {**BASE, "conversation_history": "x" * 16001},
    {**BASE, "instructions": "x" * 6001},
])
def test_oversized_context_payloads_are_rejected_before_model_call(client, payload):
    response = client.post("/verify/context/full", json=payload)
    assert response.status_code == 422

def test_unicode_and_multiline_text_is_accepted_by_request_validation(client, api_module, monkeypatch):
    class UnicodeSafeAuditor:
        def audit(self, **kwargs):
            assert "🧪" in kwargs["answer"]
            assert "\n" in kwargs["answer"]
            return {"status": "no_actionable_failure_detected"}
    monkeypatch.setattr(api_module, "contextual_auditor", UnicodeSafeAuditor())
    response = client.post("/verify/context", json={
        **BASE, "answer": "Line one.\nLine two. 🧪 中文 हिन्दी"
    })
    assert response.status_code == 200

def test_missing_optional_context_fields_use_defaults(client, api_module, monkeypatch):
    class MinimalAuditor:
        def audit(self, **kwargs):
            assert kwargs["context"] == ""
            assert kwargs["conversation_history"] == ""
            assert kwargs["instructions"] == ""
            return {"status": "no_actionable_failure_detected"}
    monkeypatch.setattr(api_module, "contextual_auditor", MinimalAuditor())
    response = client.post("/verify/context", json={
        "question": "What was said?",
        "answer": "No prior details were supplied."
    })
    assert response.status_code == 200
