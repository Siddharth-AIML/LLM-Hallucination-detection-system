"""Boundary tests: no LLM calls should be required for these cases."""

import pytest

BASE = {
    "question": "What database does this project use?",
    "answer": "The project uses MongoDB.",
    "context": "",
    "conversation_history": "",
    "instructions": "",
}

@pytest.mark.parametrize("field,value", [
    ("question", ""),
    ("question", "   "),
    ("answer", ""),
    ("answer", " \n\t "),
])
def test_contextual_endpoints_reject_blank_required_fields(client, field, value):
    payload = {**BASE, field: value}
    for endpoint in ("/verify/context", "/verify/context/memory", "/verify/context/full"):
        response = client.post(endpoint, json=payload)
        assert response.status_code == 422, (endpoint, response.status_code, response.text)

@pytest.mark.parametrize("field,limit", [
    ("question", 4000),
    ("answer", 12000),
    ("context", 16000),
    ("conversation_history", 16000),
    ("instructions", 6000),
])
def test_contextual_endpoints_reject_oversized_fields(client, field, limit):
    payload = {**BASE, field: "x" * (limit + 1)}
    response = client.post("/verify/context", json=payload)
    assert response.status_code == 422, (field, response.status_code, response.text)

def test_factual_blank_text_returns_structured_empty_result(client):
    response = client.post("/verify", json={"text": "   "})
    assert response.status_code == 200
    body = response.json()
    assert body.get("claims") == []
    assert body.get("summary", {}).get("total_claims") == 0
    assert body.get("error")

def test_factual_missing_text_field_is_rejected(client):
    response = client.post("/verify", json={})
    assert response.status_code == 422

def test_factual_non_string_text_is_rejected(client):
    response = client.post("/verify", json={"text": {"unexpected": "object"}})
    assert response.status_code == 422

def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json().get("status") == "ok"
