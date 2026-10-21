"""Stage 6: the code-check API.

Run from the TruthLensv2 root:
    uvicorn code_verifier.server:app --port 8001
or let it pick a free port (8001, else 8002):
    python -m code_verifier.server
"""

import socket

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .checker import analyze_code, summarize
from .extract import extract_code_blocks

PREFERRED_PORTS = (8001, 8002)

app = FastAPI(title="TruthLens Code Check API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "null",  # page opened from disk (file://)
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


class CodeCheckRequest(BaseModel):
    text: str = Field(max_length=100_000)


@app.get("/health")
def health():
    return {"status": "ok"}


# Plain `def` on purpose: PyPI lookups block, so FastAPI runs this in its
# thread pool instead of stalling the event loop.
@app.post("/check-code")
def check_code(req: CodeCheckRequest):
    # HTTPException responses pass through the CORS middleware; a bare
    # crash would not, and the browser would report it as a CORS error.
    try:
        findings = analyze_code(req.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"code check failed: {e}")
    return {
        "findings": findings,
        "summary": summarize(findings),
        "blocks_found": len(extract_code_blocks(req.text)),
    }


def port_in_use(port, host="127.0.0.1"):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def pick_port():
    for port in PREFERRED_PORTS:
        if not port_in_use(port):
            return port
    raise RuntimeError(f"ports {PREFERRED_PORTS} are all in use")


def main():
    import uvicorn

    port = pick_port()
    print(f"Code check API on http://127.0.0.1:{port}")
    uvicorn.run(app, host="127.0.0.1", port=port)


if __name__ == "__main__":
    main()
