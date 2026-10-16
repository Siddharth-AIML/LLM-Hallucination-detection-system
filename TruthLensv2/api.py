"""
TruthLens V2 - Minimal Demo API

Wraps the existing TruthLensPipeline in a single local HTTP
endpoint so the demo frontend can call it. This is a thin
transport layer only: it adds no verification logic and no
scoring of its own.

Deliberately NOT computed here: any document-level "trust
score". TruthLensPipeline.process_answer() states that no
aggregate verdict is produced, and no such formula exists
anywhere in the codebase. The summary returned below is a
plain tally of the per-claim verdicts the pipeline actually
emitted - counting is reporting, not new fusion logic.

Run:
    uvicorn api:app --port 8000
"""

import asyncio
import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from math_verifier import verify_math_answer
from pipeline import TruthLensPipeline

logger = logging.getLogger(__name__)

app = FastAPI(title="TruthLens V2 Demo API")

# Local demo only. The frontend is served from this same
# process, but file:// pages send an Origin of "null" and
# localhost/127.0.0.1 are distinct origins to the browser,
# so all three are allowed.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "null",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


class VerifyRequest(BaseModel):
    text: str


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


# Loading the pipeline pulls in spaCy, MiniLM and FAISS and
# measured ~17s. Doing it once at import keeps every request
# after startup fast.
pipeline = TruthLensPipeline()


def _evidence_to_json(items):
    """Flatten evidence objects to the fields the UI shows."""

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


@app.post("/verify")
def verify(request: VerifyRequest):
    """Run the full pipeline over one LLM answer."""

    text = (request.text or "").strip()

    if not text:
        return {
            "claims": [],
            "summary": {"total_claims": 0, "verdict_counts": {}},
            "error": "No text provided.",
        }

    try:
        results = pipeline.process_answer(text)

    except Exception as error:
        logger.exception("Pipeline failed")
        return {
            "claims": [],
            "summary": {"total_claims": 0, "verdict_counts": {}},
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
            "confidence": round(
                float(verification.confidence), 4
            ),
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
            # Stated explicitly so the demo never implies a
            # document-level score exists.
            "note": (
                "TruthLens verifies each claim independently. "
                "No document-level aggregate verdict is "
                "produced by design."
            ),
        },
    }


@app.post("/verify/math")
async def verify_math(request: MathVerifyRequest):
    """Independently verify supported arithmetic without using the KB."""
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(
                verify_math_answer, request.question, request.answer
            ),
            timeout=10.0,
        )
    except asyncio.TimeoutError as error:
        logger.warning("Math verification exceeded its 10-second limit")
        raise HTTPException(
            status_code=504, detail="Math verification timed out."
        ) from error
    except Exception as error:
        logger.exception("Math verification failed")
        raise HTTPException(
            status_code=500, detail="Math verification failed."
        ) from error
    return result.to_dict()


@app.get("/health")
def health():
    return {"status": "ok"}


# Serve the demo page from this same process so the whole demo
# is one command. Mounted last so it cannot shadow the API
# routes above.
app.mount(
    "/",
    StaticFiles(directory="frontend", html=True),
    name="frontend",
)
