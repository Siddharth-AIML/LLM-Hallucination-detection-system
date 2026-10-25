"""
Optional real-model smoke tests. They are skipped unless explicitly enabled.
These tests call configured real services and may incur API usage/cost and
produce nondeterministic semantic outcomes. They check completion/schema,
not whether an LLM's judgement is objectively correct.
"""
import os
import pytest

pytestmark = pytest.mark.live

def enabled():
    return os.getenv("TRUTHLENS_RUN_LIVE", "").strip().lower() in {"1", "true", "yes"}

@pytest.mark.skipif(not enabled(), reason="Set TRUTHLENS_RUN_LIVE=1 to run real configured modules.")
def test_live_context_audit_completes(client):
    response = client.post("/verify/context", json={
        "question": "Which database is specified?",
        "answer": "The project uses MongoDB.",
        "context": "The project database is MongoDB.",
        "conversation_history": "Earlier: use MongoDB.",
        "instructions": "Use only supplied information."
    })
    assert response.status_code == 200, response.text
    body = response.json()
    assert body.get("status") == "completed"
    assert "audit" in body

@pytest.mark.skipif(not enabled(), reason="Set TRUTHLENS_RUN_LIVE=1 to run real configured modules.")
def test_live_context_memory_completes(client):
    response = client.post("/verify/context/memory", json={
        "question": "Which database is specified?",
        "answer": "The project uses MongoDB.",
        "context": "",
        "conversation_history": "Earlier: use MongoDB.",
        "instructions": "Use only supplied information."
    })
    assert response.status_code == 200, response.text
    body = response.json()
    assert body.get("status") == "completed"
    assert "memory_analysis" in body

@pytest.mark.skipif(not enabled(), reason="Set TRUTHLENS_RUN_LIVE=1 to run real configured modules.")
def test_live_factual_pipeline_completes(client):
    response = client.post("/verify", json={"text": "The Earth orbits the Sun."})
    assert response.status_code == 200, response.text
    body = response.json()
    assert "claims" in body
    assert "summary" in body
    assert body["summary"]["total_claims"] == len(body["claims"])

@pytest.mark.skipif(not enabled(), reason="Set TRUTHLENS_RUN_LIVE=1 to run real configured modules.")
def test_live_history_constraint_violation_is_flagged_by_both_analyses(client):
    """Two-sentence / no-bullets rule given only in the conversation history."""
    response = client.post("/verify/context/full", json={
        "question": "Explain what a REST API is.",
        "answer": (
            "REST APIs expose resources over HTTP.\n"
            "- Resources are identified by URLs.\n"
            "- Clients use verbs such as GET and POST."
        ),
        "context": "",
        "conversation_history": (
            "Please keep all answers to at most two sentences "
            "and do not use bullet points."
        ),
        "instructions": ""
    })
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["memory_analysis"]["answer_consistency"]["verdict"] == "CONFLICTED"
    assert body["contextual_audit"]["instruction_consistency"]["verdict"] == "INCONSISTENT"
