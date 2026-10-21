# code_verifier

Detects hallucinated code in an LLM answer: packages that do not exist
(or look like typosquats) and functions that do not exist in real,
installed packages. Ported cell by cell from `CodeHallucinations.ipynb`.

The detector is standard library only. Submitted code is **only parsed**
(`ast.parse`), never executed, and nothing it mentions is ever pip-installed.
Only stdlib or already-installed modules are imported (`can_inspect`).

## Layout (same order as the notebook)

| File | Contents |
|---|---|
| `extract.py` | `extract_code_blocks` (fence regex), `safe_parse` |
| `imports.py` | `get_imports`, `KNOWN_IMPORTS`, `PYPI_URL`, `on_pypi` (cached), `classify`, `VERDICT` |
| `background.py` | `near_miss`, `package_profile` (cached), `background_check` |
| `functions.py` | `build_aliases`, `attr_chain`, `get_references`, `resolve`, `can_inspect`, `check_function` |
| `checker.py` | `analyze_code`, `summarize` (public entry point) |
| `server.py` | FastAPI app (`/check-code`, `/health`) |
| `tests/test_checker.py` | pytest suite |

```python
from code_verifier import analyze_code, summarize
findings = analyze_code(llm_answer)   # [{block, kind, item, verdict, reason}, ...]
summarize(findings)                   # {"SUPPORTED": 3, "CONTRADICTED": 2}
```

`PYPI_URL` is a module-level setting in `code_verifier/imports.py`
(`background.py` reads it from there). Caches: `imports.pypi_cache`,
`background.profile_cache`.

## Run both servers (from the `TruthLensv2` directory)

| Server | Port | Command |
|---|---|---|
| Main claim/math pipeline | 8000 | `uvicorn api:app --port 8000` |
| Code check | 8001 | `uvicorn code_verifier.server:app --port 8001` |

Open the frontend at <http://127.0.0.1:8000> and use the **Code check** tab.

If 8001 might be taken, use the launcher instead; it uses 8001 when free,
otherwise 8002:

```
python -m code_verifier.server
```

The frontend tries `http://127.0.0.1:8001/health`, then `:8002`, and uses
the first that answers.

## API

`POST /check-code` with `{"text": "<LLM answer>"}` returns

```json
{
  "findings": [
    {"block": 0, "kind": "function", "item": "requests.fetch",
     "verdict": "CONTRADICTED",
     "reason": "'fetch' not found (installed version 2.34.2); closest real name: 'get'"}
  ],
  "summary": {"SUPPORTED": 4, "CONTRADICTED": 2},
  "blocks_found": 1
}
```

`kind` is `parse`, `package` or `function`. `GET /health` returns `{"status": "ok"}`.
CORS allows `http://127.0.0.1:8000` and `http://localhost:8000`.
If PyPI is unreachable, unknown packages get `INSUFFICIENT_INFORMATION`
(10 s timeout, never cached, never an error response).

## Tests

```
pip install pytest httpx
pytest code_verifier/tests                    # all (live PyPI tests skip themselves if offline)
pytest code_verifier/tests -m "not internet"  # offline only
```

Tests marked `internet` use the real pypi.org: Round 1 example (live),
12 notebook cases (live), `/check-code` Round 1 (live). Each of the first two
also has an offline twin that pre-fills the cache.

## Known limitations (kept from the notebook)

- Methods on variables (`d.append_key(...)`) are not checked: no type inference
  (`test_method_on_variable_is_not_caught_known_limitation`).
- `from pkg import *` is reported as CONTRADICTED (`pkg.*` is looked up as an
  attribute). This is a notebook bug that was ported unchanged.
