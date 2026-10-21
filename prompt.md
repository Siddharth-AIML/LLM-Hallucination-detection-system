# JARS — Port the code hallucination notebook into code_verifier/

## Context

JARS (repo folder TruthLens) is a hallucination-detection project. The code hallucination
detector was prototyped cell by cell in TruthLensv2\code_verifier\CodeHallucinations.ipynb
Read that notebook fully first. Your job is to turn it into a small Python package plus its
own server. Port the existing logic faithfully: same rules, same thresholds, same verdicts.
Do not redesign or "improve" the detection logic. The team needs the code to match the
notebook they built and can explain.

Code, math and the main claim-verification pipeline are kept separate. Do NOT modify
anything outside code_verifier/ except the frontend addition described in Task 3.

## Task 1 — Package layout

Create this structure, one file per notebook stage so it reads in the same order the
notebook was built:

code_verifier/
**init**.py
extract.py code-block extraction (backtick fence regex), safe_parse
imports.py get_imports, KNOWN_IMPORTS, on_pypi (with cache), classify
background.py near_miss, package_profile (with cache), background_check
functions.py build_aliases (the fixed version), attr_chain, get_references,
resolve, can_inspect, check_function
checker.py analyze_code, summarize (the public entry point)
server.py the API (Task 2)
tests/test_checker.py
README.md

Rules:

- No print statements in library code. Functions return data.
- Keep PYPI_URL as a module-level setting so the offline test can point it at an invalid host.
- Keep every function name from the notebook so the paper's Methodology can refer to them.
- Use only the standard library in the detector itself (ast, re, difflib, importlib, urllib,
  json, datetime). FastAPI/uvicorn only in server.py.

## Task 2 — Server (FastAPI, port 8001)

- POST /check-code with body {"text": "<LLM answer>"}.
  Returns {"findings": [...], "summary": {...}, "blocks_found": <int>}.
  Each finding keeps the notebook's shape: block, kind (parse/package/function), item,
  verdict, reason.
- GET /health returns {"status": "ok"}.
- CORS: allow the main frontend's localhost origins (127.0.0.1:8000 and localhost:8000).
- Run from the TruthLens root with: uvicorn code_verifier.server:app --port 8001
- Network calls to PyPI must keep the notebook's timeout and must never crash a request:
  unreachable PyPI must produce INSUFFICIENT_INFORMATION exactly as in the notebook.

## Task 3 — Frontend hookup (minimal)

Add a separate "Code check" section or tab to the existing frontend that sends the text
to http://127.0.0.1:8001/check-code and shows each finding as a row: item, kind, verdict
badge (same colours as the main page's verdicts), reason. Show the summary counts on top.
Do not change how the existing claim-verification view works or which server it calls.

## Safety rules (must hold in every file)

- Never pip install anything a user's code mentions.
- Never execute, exec(), or eval() submitted code. Only ast.parse it.
- Only import modules that are standard library or already installed (can_inspect), as in
  the notebook.

## Task 4 — Tests (pytest)

Turn the notebook's checks into tests:

- The Round 1 example answer: fastjson_turbo and requests.fetch are CONTRADICTED; nothing
  real is flagged.
- The 12 TEST_CASES from the notebook give precision 1.0 and recall 1.0.
- fakefn-06 (method on a variable, d.append_key) is NOT caught. Keep this as a test that
  documents a known limitation; do not add type inference to make it pass.
- Broken code returns a parse finding with INSUFFICIENT_INFORMATION and does not raise.
- Offline: with PYPI_URL pointed at an invalid host, an unknown package returns
  INSUFFICIENT_INFORMATION and is not stored in the cache.
- Simulated typosquat (pre-filled caches for "reqeusts", 3 days old, 1 release) returns
  CONTRADICTED.
- POST /check-code returns the documented JSON shape.
  Mark tests that need the internet so they can be skipped offline.

## Deliverables

1. The package, server, frontend section and tests, all passing (state which tests needed
   the internet).
2. A table mapping each notebook cell/function to the file it now lives in.
3. A list of any place where you had to deviate from the notebook, and why. If none, say so.
4. README with run instructions for both servers side by side (8000 main, 8001 code).
