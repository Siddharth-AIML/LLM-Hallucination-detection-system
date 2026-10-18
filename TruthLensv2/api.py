
"""
TruthLens V2 - Unified Reliability and Mitigation API

Endpoints:
    POST /verify
    POST /verify/math
    POST /verify/context
    POST /verify/context/memory
    POST /verify/context/full
    POST /verify/context/mitigate
    GET  /health

Run from the TruthLensv2 directory:
    python -m uvicorn api:app --reload --host 127.0.0.1 --port 8000
"""

import asyncio
import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from contextual_audit.contextual_auditor import ContextualAuditor
from contextual_audit.context_memory import ContextMemoryAnalyzer
from math_verifier import verify_math_answer
from pipeline import TruthLensPipeline

logger = logging.getLogger(__name__)

app = FastAPI(title="TruthLens V2 Reliability and Mitigation API")


# ------------------------------------------------------------
# CORS
# ------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "null",
    ],
    allow_origin_regex=r"chrome-extension://.*",
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------
# REQUEST MODELS
# ------------------------------------------------------------

class VerifyRequest(BaseModel):
    text: str


class ContextVerifyRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    answer: str = Field(min_length=1, max_length=12000)
    context: str = Field(default="", max_length=16000)
    conversation_history: str = Field(default="", max_length=16000)
    instructions: str = Field(default="", max_length=6000)

    @field_validator("question", "answer")
    @classmethod
    def require_non_whitespace(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("This field must not be blank.")
        return value


class MathVerifyRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    answer: str = Field(min_length=1, max_length=12000)

    @field_validator("question", "answer")
    @classmethod
    def require_non_whitespace(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("This field must not be blank.")
        return value


# ------------------------------------------------------------
# SERVICE INITIALIZATION
# ------------------------------------------------------------

pipeline = TruthLensPipeline()
contextual_auditor = ContextualAuditor()
context_memory_analyzer = ContextMemoryAnalyzer()


# ------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------

def _evidence_to_json(items):
    """Convert evidence objects into JSON-compatible dictionaries."""
    output = []

    for item in items or []:
        if isinstance(item, dict):
            record = item
        elif hasattr(item, "__dict__"):
            record = dict(item.__dict__)
        else:
            record = {"text": str(item)}

        output.append({
            "text": str(record.get("text", "")),
            "source": str(record.get("source", "") or "Unknown"),
            "url": record.get("url"),
            "published_date": record.get("published_date"),
        })

    return output


def _run_contextual_audit(request):
    """Execute the existing contextual audit."""
    return contextual_auditor.audit(
        question=request.question,
        answer=request.answer,
        context=request.context,
        conversation_history=request.conversation_history,
        instructions=request.instructions,
    )


def _run_memory_analysis(request):
    """Execute the existing conversation memory analysis."""
    return context_memory_analyzer.analyze(
        conversation_history=request.conversation_history,
        current_question=request.question,
        answer=request.answer,
        instructions=request.instructions,
    )


# ------------------------------------------------------------
# FACTUAL VERIFICATION
# POST /verify
# ------------------------------------------------------------

@app.post("/verify")
def verify(request: VerifyRequest):
    text = (request.text or "").strip()

    if not text:
        return {
            "claims": [],
            "summary": {
                "total_claims": 0,
                "verdict_counts": {},
            },
            "error": "No text provided.",
        }

    try:
        results = pipeline.process_answer(text)
    except Exception as error:
        logger.exception("Factual verification failed")
        return {
            "claims": [],
            "summary": {
                "total_claims": 0,
                "verdict_counts": {},
            },
            "error": f"{type(error).__name__}: {error}",
        }

    claims = []
    counts = {}

    for item in results or []:
        verification = item["verification_result"]
        verdict = verification.verdict

        counts[verdict] = counts.get(verdict, 0) + 1

        claims.append({
            "claim_id": item["claim_id"],
            "claim": verification.claim,
            "verdict": verdict,
            "confidence": round(float(verification.confidence), 4),
            "llm_relation": verification.llm_relation,
            "explanation": verification.explanation,
            "retrieved_topics": verification.retrieved_topics,
            "deterministic_signals": {
                key: round(float(value), 4)
                for key, value in (
                    verification.deterministic_signals or {}
                ).items()
            },
            "supporting_evidence": _evidence_to_json(
                verification.supporting_evidence
            ),
            "contradicting_evidence": _evidence_to_json(
                verification.contradicting_evidence
            ),
        })

    return {
        "input_text": text,
        "claims": claims,
        "summary": {
            "total_claims": len(claims),
            "verdict_counts": counts,
            "note": (
                "TruthLens verifies each claim independently. "
                "No document-level aggregate verdict is produced."
            ),
        },
    }


# ------------------------------------------------------------
# MATH VERIFICATION
# POST /verify/math
# ------------------------------------------------------------

@app.post("/verify/math")
async def verify_math(request: MathVerifyRequest):
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(
                verify_math_answer,
                request.question,
                request.answer,
            ),
            timeout=2.0,
        )
    except asyncio.TimeoutError as error:
        logger.warning("Math verification timed out")
        raise HTTPException(
            status_code=504,
            detail="Math verification timed out.",
        ) from error
    except Exception as error:
        logger.exception("Math verification failed")
        raise HTTPException(
            status_code=500,
            detail="Math verification failed.",
        ) from error

    return result.to_dict()


# ------------------------------------------------------------
# HEALTH CHECK
# GET /health
# ------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok"}


# ------------------------------------------------------------
# CONTEXTUAL AUDITING
# POST /verify/context
# ------------------------------------------------------------

@app.post("/verify/context")
def verify_context(request: ContextVerifyRequest):
    try:
        result = _run_contextual_audit(request)

        return {
            "status": "completed",
            "audit": result,
        }

    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error
    except Exception as error:
        logger.exception("Contextual audit failed")
        raise HTTPException(
            status_code=502,
            detail="Contextual audit failed. Check backend logs.",
        ) from error


# ------------------------------------------------------------
# CONTEXT MEMORY ANALYSIS
# POST /verify/context/memory
# ------------------------------------------------------------

@app.post("/verify/context/memory")
def verify_context_memory(request: ContextVerifyRequest):
    try:
        result = _run_memory_analysis(request)

        return {
            "status": "completed",
            "memory_analysis": result,
        }

    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error
    except Exception as error:
        logger.exception("Context memory analysis failed")
        raise HTTPException(
            status_code=502,
            detail=(
                "Context memory analysis failed. "
                "Check backend logs."
            ),
        ) from error


# ------------------------------------------------------------
# UNIFIED CONTEXTUAL RELIABILITY WORKFLOW
# POST /verify/context/full
# ------------------------------------------------------------

@app.post("/verify/context/full")
def verify_context_full(request: ContextVerifyRequest):
    """
    Run contextual auditing and memory analysis together.

    This endpoint combines the analyses but does not correct
    the answer. Use /verify/context/mitigate for that workflow.
    """

    audit_result = None
    memory_result = None
    errors = {}

    try:
        audit_result = _run_contextual_audit(request)
    except Exception as error:
        logger.exception(
            "Unified workflow: contextual audit failed"
        )
        errors["contextual_audit"] = (
            f"{type(error).__name__}: {error}"
        )

    try:
        memory_result = _run_memory_analysis(request)
    except Exception as error:
        logger.exception(
            "Unified workflow: memory analysis failed"
        )
        errors["memory_analysis"] = (
            f"{type(error).__name__}: {error}"
        )

    if audit_result is None and memory_result is None:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "Both reliability analyses failed.",
                "errors": errors,
            },
        )

    workflow_status = (
        "completed"
        if audit_result is not None and memory_result is not None
        else "partially_completed"
    )

    return {
        "status": workflow_status,
        "question": request.question,
        "answer": request.answer,
        "contextual_audit": audit_result,
        "memory_analysis": memory_result,
        "errors": errors,
        "scope": {
            "contextual_audit": (
                "Supplied question, answer, context, history, "
                "and instructions"
            ),
            "memory_analysis": (
                "Supplied conversation history only"
            ),
        },
        "note": (
            "These analyses are returned separately. "
            "This endpoint does not automatically correct the answer."
        ),
    }


# ------------------------------------------------------------
# TARGETED MITIGATION + INDEPENDENT RE-VERIFICATION
# POST /verify/context/mitigate
# ------------------------------------------------------------

@app.post("/verify/context/mitigate")
def verify_context_mitigate(request: ContextVerifyRequest):
    """
    Audit the original answer, propose a targeted correction
    when actionable failures are detected, and re-audit it.
    The original answer is never modified automatically.
    """
    try:
        result = contextual_auditor.audit_and_mitigate(
            question=request.question,
            answer=request.answer,
            context=request.context,
            conversation_history=request.conversation_history,
            instructions=request.instructions,
        )

        # Keep the response compatible with the existing frontend.
        result["limitations"] = result.get(
            "correction_limitations", []
        )

        return result

    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error

    except Exception as error:
        logger.exception("Targeted mitigation failed")
        raise HTTPException(
            status_code=502,
            detail=(
                "Targeted mitigation failed. "
                "Check the backend terminal for details."
            ),
        ) from error


# ------------------------------------------------------------
# FRONTEND MOUNT — KEEP LAST
# ------------------------------------------------------------

app.mount(
    "/",
    StaticFiles(directory="frontend", html=True),
    name="frontend",
)
