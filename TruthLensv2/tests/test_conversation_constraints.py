"""
Tests for constraints the user stated in the conversation history.

Everything here uses a fake LLM client or fake analyzers, so the tests are
deterministic. They check what the code sends to the model and how it routes
results; they do not prove the model's judgement is correct (see the optional
live test for that).
"""

import json
from types import SimpleNamespace

import pytest

HISTORY = (
    "Please keep all answers to at most two sentences "
    "and do not use bullet points."
)
QUESTION = "Explain what a REST API is."
BAD_ANSWER = (
    "REST APIs expose resources over HTTP.\n"
    "- Resources are identified by URLs.\n"
    "- Clients use verbs such as GET and POST."
)
GOOD_ANSWER = "REST APIs expose resources over HTTP. Clients use verbs such as GET and POST."

BASE = {
    "question": QUESTION,
    "answer": BAD_ANSWER,
    "context": "",
    "conversation_history": HISTORY,
    "instructions": "",
}

CONFLICT = {
    "memory_statement": "Keep answers to at most two sentences, no bullet points.",
    "answer_excerpt": "- Resources are identified by URLs.",
    "reason": "The answer uses bullet points and has three sentences.",
}


def audit_json(instruction="CONSISTENT", memory="SUPPORTED"):
    return {
        "context_faithfulness": {"verdict": "NOT_ASSESSABLE", "findings": []},
        "conversation_alignment": {"verdict": "ALIGNED", "reason": "On topic."},
        "context_memory": {"verdict": memory, "reason": "No problem found."},
        "instruction_consistency": {"verdict": instruction, "reason": "Looks fine."},
        "limitations": [],
    }


def memory_json(verdict, conflicts=None):
    return {
        "status": "completed",
        "memory_items": [{
            "category": "CONSTRAINT",
            "statement": CONFLICT["memory_statement"],
            "evidence": "at most two sentences",
            "status": "ACTIVE",
            "supersedes": "",
        }],
        "answer_consistency": {
            "verdict": verdict,
            "reason": "Checked against the history." if verdict != "CONFLICTED" else CONFLICT["reason"],
            "conflicts": conflicts or [],
        },
        "limitations": [],
    }


class ScriptedClient:
    """Fake Groq client that returns queued JSON strings and records prompts."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.prompts = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.prompts.append(kwargs["messages"][0]["content"])
        reply = self.replies.pop(0)
        content = reply if isinstance(reply, str) else json.dumps(reply)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
        )


class ScriptedMemory:
    """Fake ContextMemoryAnalyzer that returns queued results."""

    def __init__(self, results):
        self.results = list(results)
        self.calls = []

    def analyze(self, **kwargs):
        self.calls.append(kwargs)
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


@pytest.fixture()
def auditor_module():
    from contextual_audit import contextual_auditor
    return contextual_auditor


# ---------------------------------------------------------------
# 1. Prompt contract
# ---------------------------------------------------------------

def test_audit_prompt_treats_history_constraints_as_active_instructions(
    auditor_module, monkeypatch
):
    fake = ScriptedClient([audit_json(instruction="INCONSISTENT")])
    monkeypatch.setattr(auditor_module, "client", fake)

    result = auditor_module.ContextualAuditor().audit(
        question=QUESTION,
        answer=BAD_ANSWER,
        conversation_history=HISTORY,
        instructions="",
    )

    prompt = fake.prompts[0]
    lowered = " ".join(prompt.lower().split())

    # The history reaches the model even though the instructions field is empty.
    assert HISTORY in prompt
    assert "[No separate instructions supplied]" in prompt

    # The model is told that history constraints are active instructions.
    assert "constraints the user stated in conversation history" in lowered
    assert "are active instructions" in lowered
    assert "even if the active instructions field is empty" in lowered

    # A violation must be INCONSISTENT, using the existing label set.
    assert "must be inconsistent" in lowered
    assert "CONSISTENT, INCONSISTENT, or NOT_ASSESSABLE" in prompt
    assert "FOLLOWED" not in prompt and "VIOLATED" not in prompt

    # The model's verdict is returned untouched.
    assert result["instruction_consistency"]["verdict"] == "INCONSISTENT"


# ---------------------------------------------------------------
# 2. Mitigation acts on memory-analyzer conflicts
# ---------------------------------------------------------------

def mitigation_json():
    return {
        "refined_prompt": "Explain what a REST API is in at most two sentences, without bullet points.",
        "suggested_answer": GOOD_ANSWER,
        "changes": ["Removed bullets and shortened to two sentences."],
        "limitations": [],
    }


def test_mitigate_corrects_when_only_memory_analyzer_reports_conflict(
    client, api_module, auditor_module, monkeypatch
):
    # The auditor passes both the original and the corrected answer.
    llm = ScriptedClient([audit_json(), mitigation_json(), audit_json()])
    monkeypatch.setattr(auditor_module, "client", llm)
    monkeypatch.setattr(api_module, "contextual_auditor", auditor_module.ContextualAuditor())

    memory = ScriptedMemory([
        memory_json("CONFLICTED", [CONFLICT]),
        memory_json("CONSISTENT"),
    ])
    monkeypatch.setattr(api_module, "context_memory_analyzer", memory)

    response = client.post("/verify/context/mitigate", json=BASE)

    assert response.status_code == 200, response.text
    body = response.json()

    assert body["status"] == "reverified_no_actionable_failure_detected"
    assert body["suggested_answer"] == GOOD_ANSWER
    assert body["refined_prompt"]

    # Only the memory analyzer found a problem.
    assert [f["dimension"] for f in body["failures"]] == ["memory_analysis.answer_consistency"]
    assert body["failures"][0]["conflicts"] == [CONFLICT]

    # The conflicting constraint was passed into the mitigation prompt.
    mitigation_prompt = llm.prompts[1]
    assert CONFLICT["memory_statement"] in mitigation_prompt
    assert CONFLICT["answer_excerpt"] in mitigation_prompt

    # Both analyzers re-checked the suggested answer.
    assert len(memory.calls) == 2
    assert memory.calls[0]["answer"] == BAD_ANSWER
    assert memory.calls[1]["answer"] == GOOD_ANSWER
    assert llm.prompts[2].count(GOOD_ANSWER) >= 1
    assert body["re_verification"] is not None
    assert body["re_verification_memory"]["answer_consistency"]["verdict"] == "CONSISTENT"
    assert body["remaining_failures"] == []


def test_mitigate_reports_remaining_memory_conflict_after_correction(
    client, api_module, auditor_module, monkeypatch
):
    llm = ScriptedClient([audit_json(), mitigation_json(), audit_json()])
    monkeypatch.setattr(auditor_module, "client", llm)
    monkeypatch.setattr(api_module, "contextual_auditor", auditor_module.ContextualAuditor())

    memory = ScriptedMemory([
        memory_json("CONFLICTED", [CONFLICT]),
        memory_json("PARTIALLY_CONSISTENT", [CONFLICT]),
    ])
    monkeypatch.setattr(api_module, "context_memory_analyzer", memory)

    body = client.post("/verify/context/mitigate", json=BASE).json()

    assert body["status"] == "reverified_with_remaining_issues"
    assert [f["dimension"] for f in body["remaining_failures"]] == [
        "memory_analysis.answer_consistency"
    ]
    assert body["remaining_failures"][0]["verdict"] == "PARTIALLY_CONSISTENT"


def test_mitigate_ignores_partially_consistent_without_listed_conflicts(
    client, api_module, auditor_module, monkeypatch
):
    llm = ScriptedClient([audit_json()])
    monkeypatch.setattr(auditor_module, "client", llm)
    monkeypatch.setattr(api_module, "contextual_auditor", auditor_module.ContextualAuditor())
    monkeypatch.setattr(
        api_module, "context_memory_analyzer",
        ScriptedMemory([memory_json("PARTIALLY_CONSISTENT", [])]),
    )

    body = client.post("/verify/context/mitigate", json=BASE).json()

    assert body["status"] == "no_actionable_failure_detected"
    assert body["suggested_answer"] is None
    assert len(llm.prompts) == 1


def test_mitigate_survives_memory_analyzer_failure_and_says_so(
    client, api_module, auditor_module, monkeypatch
):
    monkeypatch.setattr(auditor_module, "client", ScriptedClient([audit_json()]))
    monkeypatch.setattr(api_module, "contextual_auditor", auditor_module.ContextualAuditor())
    monkeypatch.setattr(
        api_module, "context_memory_analyzer",
        ScriptedMemory([RuntimeError("memory model down")]),
    )

    response = client.post("/verify/context/mitigate", json=BASE)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "no_actionable_failure_detected"
    assert "memory model down" in body["memory_analysis_error"]
    assert "could not be completed" in body["message"]


# ---------------------------------------------------------------
# 3. Disagreements in /verify/context/full
# ---------------------------------------------------------------

class FixedAuditor:
    def __init__(self, result):
        self.result = result

    def audit(self, **kwargs):
        return self.result


class FixedMemory:
    def __init__(self, result):
        self.result = result

    def analyze(self, **kwargs):
        return self.result


def run_full(client, api_module, monkeypatch, audit, memory):
    monkeypatch.setattr(api_module, "contextual_auditor", FixedAuditor(audit))
    monkeypatch.setattr(api_module, "context_memory_analyzer", FixedMemory(memory))
    response = client.post("/verify/context/full", json=BASE)
    assert response.status_code == 200, response.text
    return response.json()


def test_full_reports_disagreement_without_changing_either_verdict(
    client, api_module, monkeypatch
):
    audit = audit_json(instruction="CONSISTENT", memory="SUPPORTED")
    memory = memory_json("CONFLICTED", [CONFLICT])

    body = run_full(client, api_module, monkeypatch, audit, memory)

    assert [d["dimension"] for d in body["disagreements"]] == [
        "instruction_consistency",
        "context_memory",
    ]
    first = body["disagreements"][0]
    assert first["audit_verdict"] == "CONSISTENT"
    assert first["audit_reason"] == "Looks fine."
    assert first["memory_verdict"] == "CONFLICTED"
    assert first["conflicts"] == [CONFLICT]

    # Neither analysis was overwritten.
    assert body["contextual_audit"]["instruction_consistency"]["verdict"] == "CONSISTENT"
    assert body["contextual_audit"]["context_memory"]["verdict"] == "SUPPORTED"
    assert body["memory_analysis"]["answer_consistency"]["verdict"] == "CONFLICTED"


def test_full_reports_only_the_dimension_that_passed(client, api_module, monkeypatch):
    audit = audit_json(instruction="INCONSISTENT", memory="SUPPORTED")
    body = run_full(client, api_module, monkeypatch, audit, memory_json("CONFLICTED", [CONFLICT]))

    assert [d["dimension"] for d in body["disagreements"]] == ["context_memory"]


@pytest.mark.parametrize("memory_verdict", ["CONSISTENT", "PARTIALLY_CONSISTENT", "NOT_ASSESSABLE"])
def test_full_has_no_disagreement_unless_memory_says_conflicted(
    client, api_module, monkeypatch, memory_verdict
):
    body = run_full(client, api_module, monkeypatch, audit_json(), memory_json(memory_verdict))
    assert body["disagreements"] == []


def test_full_has_no_disagreement_when_audit_also_fails(client, api_module, monkeypatch):
    audit = audit_json(instruction="INCONSISTENT", memory="CONTRADICTED")
    body = run_full(client, api_module, monkeypatch, audit, memory_json("CONFLICTED", [CONFLICT]))
    assert body["disagreements"] == []


def test_full_has_empty_disagreements_when_an_analysis_is_missing(
    client, api_module, monkeypatch
):
    class Broken:
        def audit(self, **kwargs):
            raise RuntimeError("down")

    monkeypatch.setattr(api_module, "contextual_auditor", Broken())
    monkeypatch.setattr(
        api_module, "context_memory_analyzer",
        FixedMemory(memory_json("CONFLICTED", [CONFLICT])),
    )

    body = client.post("/verify/context/full", json=BASE).json()

    assert body["status"] == "partially_completed"
    assert body["disagreements"] == []
