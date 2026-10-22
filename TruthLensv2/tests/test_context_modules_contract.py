"""
Context module orchestration tests using fake module implementations.
These check argument routing, independent execution, partial failure behavior,
and error handling without depending on Groq availability or model variability.
"""

from types import SimpleNamespace

BASE = {
    "question": "What database did I specify?",
    "answer": "You specified MongoDB.",
    "context": "The project database is MongoDB.",
    "conversation_history": "Earlier: use MongoDB for persistence.",
    "instructions": "Use only supplied context and history.",
}

class FakeAuditor:
    def __init__(self, behavior="ok"):
        self.behavior = behavior
        self.calls = []
    def audit(self, **kwargs):
        self.calls.append(kwargs)
        if self.behavior == "raise":
            raise RuntimeError("auditor simulated failure")
        if self.behavior == "value_error":
            raise ValueError("bad audit input")
        return {"status": "no_actionable_failure_detected", "findings": []}

class FakeMemory:
    def __init__(self, behavior="ok"):
        self.behavior = behavior
        self.calls = []
    def analyze(self, **kwargs):
        self.calls.append(kwargs)
        if self.behavior == "raise":
            raise RuntimeError("memory simulated failure")
        return {"status": "consistent", "findings": []}

def test_context_audit_routes_all_fields(client, api_module, monkeypatch):
    fake = FakeAuditor()
    monkeypatch.setattr(api_module, "contextual_auditor", fake)
    response = client.post("/verify/context", json=BASE)
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert fake.calls == [{
        "question": BASE["question"],
        "answer": BASE["answer"],
        "context": BASE["context"],
        "conversation_history": BASE["conversation_history"],
        "instructions": BASE["instructions"],
    }]

def test_memory_analysis_routes_history_question_answer_instructions(client, api_module, monkeypatch):
    fake = FakeMemory()
    monkeypatch.setattr(api_module, "context_memory_analyzer", fake)
    response = client.post("/verify/context/memory", json=BASE)
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    call = fake.calls[0]
    assert call["conversation_history"] == BASE["conversation_history"]
    assert call["current_question"] == BASE["question"]
    assert call["answer"] == BASE["answer"]
    assert call["instructions"] == BASE["instructions"]

def test_full_workflow_returns_completed_when_both_modules_succeed(client, api_module, monkeypatch):
    audit, memory = FakeAuditor(), FakeMemory()
    monkeypatch.setattr(api_module, "contextual_auditor", audit)
    monkeypatch.setattr(api_module, "context_memory_analyzer", memory)
    response = client.post("/verify/context/full", json=BASE)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["contextual_audit"] is not None
    assert body["memory_analysis"] is not None
    assert body["errors"] == {}
    assert len(audit.calls) == len(memory.calls) == 1

def test_full_workflow_survives_contextual_auditor_failure(client, api_module, monkeypatch):
    monkeypatch.setattr(api_module, "contextual_auditor", FakeAuditor("raise"))
    monkeypatch.setattr(api_module, "context_memory_analyzer", FakeMemory())
    response = client.post("/verify/context/full", json=BASE)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "partially_completed"
    assert body["contextual_audit"] is None
    assert body["memory_analysis"] is not None
    assert "contextual_audit" in body["errors"]

def test_full_workflow_survives_memory_failure(client, api_module, monkeypatch):
    monkeypatch.setattr(api_module, "contextual_auditor", FakeAuditor())
    monkeypatch.setattr(api_module, "context_memory_analyzer", FakeMemory("raise"))
    response = client.post("/verify/context/full", json=BASE)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "partially_completed"
    assert body["contextual_audit"] is not None
    assert body["memory_analysis"] is None
    assert "memory_analysis" in body["errors"]

def test_full_workflow_fails_cleanly_if_both_modules_fail(client, api_module, monkeypatch):
    monkeypatch.setattr(api_module, "contextual_auditor", FakeAuditor("raise"))
    monkeypatch.setattr(api_module, "context_memory_analyzer", FakeMemory("raise"))
    response = client.post("/verify/context/full", json=BASE)
    assert response.status_code == 502
    assert "Both reliability analyses failed" in str(response.json())

def test_single_context_endpoint_maps_unexpected_error_to_502(client, api_module, monkeypatch):
    monkeypatch.setattr(api_module, "contextual_auditor", FakeAuditor("raise"))
    response = client.post("/verify/context", json=BASE)
    assert response.status_code == 502
    assert "Contextual audit failed" in response.json()["detail"]

def test_single_memory_endpoint_maps_unexpected_error_to_502(client, api_module, monkeypatch):
    monkeypatch.setattr(api_module, "context_memory_analyzer", FakeMemory("raise"))
    response = client.post("/verify/context/memory", json=BASE)
    assert response.status_code == 502
    assert "Context memory analysis failed" in response.json()["detail"]
