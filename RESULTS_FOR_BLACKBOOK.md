# RESULTS_FOR_BLACKBOOK — Test results and measurements for the project report

Repository: `D:\LLM-Hallucination-detection-system` (branch `main`). Collected 2026-10-22.
Nothing in project code was changed and nothing was committed. Secret values from `.env` were never printed or copied; keys are referred to by variable name only.

**How to read this file**
- Every number below is copied from a file or from a command output I ran. Nothing is rounded or recomputed unless a line says "derived".
- Where no evidence exists, the text says "not available".
- File modification dates are the dates the files were checked out or edited on this machine (`2026-10-17` for the original checkout, `2026-10-22` for the later pull). They are not the dates the experiments were run. Where a file records its own run timestamp, that timestamp is quoted.

**Headline findings you should know before using any number**
1. In my own re-run of the test suite, **61 of 108 tests could not run** (setup error: the spaCy model `en_core_web_sm` is not installed in this machine's `venv`). The team's own saved run, made on another machine, shows 59 passed / 3 skipped / 0 failed out of 62. Both are reported in Part B.
2. Several results quoted in your gap list (72 tests, the 11-case math set with 0.73 ms, the RBI / Eiffel / contextual case studies, the latency table) have **no evidence in the repo**. See Part E.
3. The team's saved test report (`TruthLensV2_Test_Results.xlsx/.docx`) lists 20 tests in `test_math_verifier.py` and 14 in `test_request_validation.py`. The team's own pytest log and my run both show 21 and 13. The total of 62 is the same.

---

# PART A — Result artifacts that already exist

Searched `TruthLensv2/`, `docs/`, `notebooks/` and the repo root for `*.csv`, `*.json`, `*.log`, `*.txt`, `*.png`, `*.jpg`, `*.ipynb`, `*.xml`, `*.xlsx`, `*.docx`. Skipped as requested: `knowledge_base.json` (analysed in Part C6), `news_dataset.json`, `config/`, `venv`, caches.
There are **no** `.csv`, `.log`, `.png` or `.jpg` files in the repo outside `venv`. There are no `results/` or `outputs/` folders.

## A.1 Artifact list

| # | Path | Size (bytes) | Modified | What it measures |
|---|---|---|---|---|
| 1 | `TruthLensv2/reports/functional-tests.txt` | 17134 | 2026-10-22 13:34 | Full verbose pytest log of the 62-test suite (team's run) |
| 2 | `TruthLensv2/reports/functional-tests.xml` | 9147 | 2026-10-22 13:34 | JUnit XML of the same 62-test run |
| 3 | `TruthLensv2/reports/contextual-tests.xml` | 1316 | 2026-10-22 13:34 | JUnit XML, `test_context_modules_contract.py` only |
| 4 | `TruthLensv2/reports/factual-tests.xml` | 649 | 2026-10-22 13:34 | JUnit XML, `test_factual_pipeline_contract.py` only |
| 5 | `TruthLensv2/reports/factual-edge-10.xml` | 1593 | 2026-10-22 13:34 | JUnit XML, `test_factual_edge_cases_10.py` (F01–F10) |
| 6 | `TruthLensv2/reports/contextual-edge-10.xml` | 1737 | 2026-10-22 13:34 | JUnit XML, `test_contextual_edge_cases_10_fixed.py` (C01–C10) |
| 7 | `TruthLensv2/reports/TruthLensV2_Test_Results.xlsx` | 8022 | 2026-10-22 13:34 | Table 6.1 and Table 6.2 for the report |
| 8 | `TruthLensv2/reports/TruthLensV2_Test_Results.docx` | 38955 | 2026-10-22 13:34 | Same two tables as the xlsx, with a limitation note |
| 9 | `TruthLensv2/data/expansion_queue.json` | 611744 | 2026-10-22 13:34 | Record of 10 knowledge-expansion topics and their LLM validation results |
| 10 | `TruthLensv2/code_verifier/CodeHallucinations.ipynb` | 45805 | 2026-10-17 12:55 | Code-hallucination prototype and the 12-case benchmark |
| 11 | `TruthLensv2/test1.ipynb` | 12129 | 2026-10-17 12:52 | One claim-processor run |
| 12 | `notebooks/complete_verification_pipeline.ipynb` | 18215 | 2026-10-17 12:52 | Prototype pipeline: 3 claims, trust report |
| 13 | `notebooks/Complete_Pipeline.ipynb` | 9129 | 2026-10-17 12:52 | Prototype topic retrieval |
| 14 | `notebooks/Evidence_verification.ipynb` | 22755 | 2026-10-17 12:52 | Prototype NLI verification, FAISS fallback |
| 15 | `notebooks/evidence_retrieval.ipynb` | 25201 | 2026-10-17 12:52 | Prototype FAISS retrieval and corpus growth |
| 16 | `notebooks/claim_extraction.ipynb` | 8290 | 2026-10-17 12:52 | Prototype claim extraction |
| 17 | `notebooks/Topic Corpus V2.ipynb` | 6995 | 2026-10-17 12:52 | Topic embedding prototype |
| 18 | `notebooks/topic_corpus_builder.ipynb` | 17157 | 2026-10-17 12:52 | Topic corpus build (evidence counts) |
| 19 | `notebooks/corpus_building.ipynb` | 61174 | 2026-10-17 12:52 | Wikipedia corpus fetch log |
| 20 | `docs/TRUTHLENS_CONTEXT.md` | 14184 | 2026-10-17 12:52 | Hand-written project notes with some measured KB facts (22 topics / 193 evidence) |
| — | `TruthLensv2/test.ipynb` | 0 | 2026-10-17 12:52 | Empty, not valid JSON |
| — | `notebooks/corpus.json`, `notebooks/topic_corpus.json` | 3326945 / 44289 | 2026-10-17 12:52 | Data inputs for prototypes, not results |

`docs/report.md` and `docs/architecture.md` are 0 bytes.

## A.2 Details for each artifact

### Artifacts 1–6: pytest logs and JUnit XML (team's run)

Produced by pytest on a different machine. The log header says `platform win32 -- Python 3.10.11, pytest-9.1.1`, `configfile: pytest.ini`, `testpaths: tests`.
The XML files give a hostname of `SHALAN`. The exact command was not recorded; the log is consistent with `pytest -v` from `TruthLensv2/`. The XML files were evidently written with `--junitxml`.

Key numbers copied from each file:

```text
functional-tests.txt : collected 62 items ... 59 passed, 3 skipped, 4 warnings in 44.07s
functional-tests.xml : testsuite errors="0" failures="0" skipped="3" tests="62" time="80.981" timestamp="2026-10-22T09:49:02.292619+05:30"
contextual-tests.xml : errors="0" failures="0" skipped="0" tests="8"  time="43.040" timestamp="2026-10-22T10:43:47.336070+05:30"
factual-tests.xml    : errors="0" failures="0" skipped="0" tests="3"  time="45.780" timestamp="2026-10-22T10:46:00.584706+05:30"
factual-edge-10.xml  : errors="0" failures="0" skipped="0" tests="10" time="45.316" timestamp="2026-10-22T11:15:36.032612+05:30"
contextual-edge-10.xml: errors="0" failures="0" skipped="0" tests="10" time="44.763" timestamp="2026-10-22T11:26:38.084697+05:30"
```

Note: `functional-tests.xml` reports `time="80.981"` while `functional-tests.txt` reports `44.07s`. They are two different runs; neither file says which run produced which.
In each file the first test took most of the time (about 42–78 s). That is the `api` import (model loading) inside the session fixture, not the test itself.

The `skipped` entries in `functional-tests.txt`:

```text
SKIPPED [1] tests\test_live_functionality_optional.py:15: Set TRUTHLENS_RUN_LIVE=1 to run real configured modules.
SKIPPED [1] tests\test_live_functionality_optional.py:29: Set TRUTHLENS_RUN_LIVE=1 to run real configured modules.
SKIPPED [1] tests\test_live_functionality_optional.py:43: Set TRUTHLENS_RUN_LIVE=1 to run real configured modules.
```

The full per-test PASSED list is in `functional-tests.txt` (62 lines); it is not repeated here.

### Artifacts 7–8: `TruthLensV2_Test_Results.xlsx` and `.docx`

Written by `TruthLensv2/scripts/generate_test_report.py`. The rows in that script are hard-coded (for example `["GSM8K Benchmark Tests", "test_gsm8k_benchmark.py", 2, 2, "Included in full-suite run", ...]`), so the tables are not computed from a pytest run.
Contents of the xlsx (the docx has the same two tables), copied exactly:

```text
Table 6.1: Automated Test Results
Test Suite Package | Test Module File | Tests Collected | Tests Passed | Execution Time | Primary Subsystem Evaluated
Context Module Contract Tests | test_context_modules_contract.py | 8 | 8 | 43.04 s* | Context audit, memory analysis, workflow error handling
Extreme Input Tests | test_extreme_inputs.py | 7 | 7 | Included in full-suite run | Oversized inputs, Unicode, multiline text
Factual Pipeline Contract Tests | test_factual_pipeline_contract.py | 3 | 3 | 45.78 s* | Factual result schema, structured errors, empty output
GSM8K Benchmark Tests | test_gsm8k_benchmark.py | 2 | 2 | Included in full-suite run | Numeric answer extraction and benchmark metrics
Live Functionality Tests | test_live_functionality_optional.py | 3 | 0 | Skipped | Real configured modules; requires TRUTHLENS_RUN_LIVE=1
Math API Tests | test_math_api.py | 5 | 5 | Included in full-suite run | Math API validation and route availability
Math Verifier Tests | test_math_verifier.py | 20 | 20 | Included in full-suite run | Arithmetic, word problems, ambiguous cases
Request Validation Tests | test_request_validation.py | 14 | 14 | Included in full-suite run | Required fields, sizes, types, health endpoint
Full Suite Summary | All test modules | 62 | 59 passed | 44.07 s | 3 skipped, 0 failures, 4 warnings

Table 6.2: Edge-Case Test Results
Case ID | Test Module | Input / Test Scenario | Expected / Observed Behaviour | Result
F01 | Factual | Supported claim | Supporting evidence and verdict are serialized | Pass
F02 | Factual | Contradicted claim | Contradicting evidence and verdict are serialized | Pass
F03 | Factual | No evidence available | Claim is not promoted to supported without evidence | Pass
F04 | Factual | Multiple claims | Each claim retains its own verdict | Pass
F05 | Factual | Conflicting evidence | Both supporting and contradicting evidence are preserved | Pass
F06 | Factual | Date and numeric claims | Per-claim results preserve response structure | Pass
F07 | Factual | Duplicate claims | Duplicate claims do not break response structure | Pass
F08 | Factual | Empty input | A safe empty result is returned | Pass
F09 | Factual | Unicode, multiline, injection-like text | Input is forwarded as data to the simulated pipeline | Pass
F10 | Factual | Pipeline failure | A structured error response is returned | Pass
C01 | Contextual | Context contradiction | Contradiction finding is returned | Pass
C02 | Contextual | No-action mitigation | Supported answer does not trigger unnecessary mitigation | Pass
C03 | Contextual | Missing context | Insufficient-context result is returned by the simulated auditor | Pass
C04 | Contextual | Instruction violation | Instruction-violation finding is preserved | Pass
C05 | Contextual | Irrelevant answer | Answer is passed for alignment auditing | Pass
C06 | Contextual | Empty conversation history | Memory analysis is marked not assessable | Pass
C07 | Contextual | Conflicting history and injection-like text | Inputs are passed as untrusted data | Pass
C08 | Contextual | Partial workflow failure | Workflow reports partial failure safely | Pass
C09 | Contextual | Mitigation re-verification | Remaining issue status is returned | Pass
C10 | Contextual | Validation/backend failure | Validation and simulated backend errors are handled | Pass
Total | Both suites | 20 edge-case tests | 20 passed; 0 failed | Pass
```

The docx adds this sentence, which belongs in the report:

```text
Testing limitation: Several edge-case tests use mocked/simulated pipeline or module responses. These results validate API contracts, response serialization, input validation, and error handling; they do not independently prove live LLM hallucination-detection accuracy.
```

### Artifact 9: `data/expansion_queue.json`

A JSON array of 10 queue items, written by `expansion/expansion_queue.py` during knowledge-expansion runs (default `queue_file="data/expansion_queue.json"`). Status counts: COMPLETED 3, DISCARDED 3, PENDING 3, RETRY 1.
It is the only recorded output of the LLM topic validator (prompt §3 in `PROMPTS_APPENDIX.md`). Values copied exactly:

| topic | queue status | validation status | llm_relation | confidence | source_count | created_at | updated_at | retry_count |
|---|---|---|---|---|---|---|---|---|
| SpaceX reported a loss of $541 million. | COMPLETED | VALID | SUPPORT | 1.0 | 33 | 2026-08-10T14:32:36.748773 | 2026-08-10T19:16:14.900357 | 1 |
| SpaceX acquired Netflix in 2026. | DISCARDED | INVALID | NEUTRAL | 0.0 | 18 | 2026-08-10T18:23:25.235919 | 2026-08-10T19:30:02.333585 | 1 |
| The Eiffel Tower is in Paris. | COMPLETED | VALID | SUPPORT | 0.98 | 37 | 2026-08-17T05:40:57.165544 | 2026-08-24T17:07:13.523697 | 0 |
| Eiffel Tower is in Paris | RETRY | RETRY | NEUTRAL | 0.0 | 28 | 2026-08-17T05:45:24.404106 | 2026-09-09T16:27:05.046259 | 1 |
| SpaceX revenue grew 92% year over year and it acquired Netflix. | DISCARDED | INVALID | NEUTRAL | 0.9 | 12 | 2026-08-24T16:55:02.404733 | 2026-08-24T16:59:24.053446 | 0 |
| The Eiffel Tower was built in 1889 by Gustave Eiffel. | COMPLETED | VALID | SUPPORT | 0.95 | 15 | 2026-08-24T16:55:05.815947 | 2026-09-09T16:27:55.487005 | 0 |
| Antarctica's penguin population doubled in 2026. | DISCARDED | INVALID | NEUTRAL | 0.9 | 11 | 2026-08-24T16:55:09.176636 | 2026-08-24T17:00:49.751394 | 0 |
| Ola Electric Mobility confirmed it has acquired Tesla's Indian manufacturing division outright. | PENDING | (none yet) | — | — | — | 2026-09-09T17:04:36.511085 | 2026-09-09T17:04:36.511085 | 0 |
| Ola Electric has acquired Tesla's Indian manufacturing division outright. | PENDING | (none yet) | — | — | — | 2026-09-09T17:08:25.664450 | 2026-09-09T17:08:25.664450 | 0 |
| The Earth orbits the Sun. | PENDING | (none yet) | — | — | — | 2026-10-22T04:22:55.278729 | 2026-10-22T04:22:55.278729 | 0 |

`reason` text recorded by the LLM (copied exactly):

```text
SpaceX reported a loss of $541 million.        -> Multiple independent sources (EVIDENCE 1, EVIDENCE 2, EVIDENCE 3, EVIDENCE 4, EVIDENCE 5, EVIDENCE 6, EVIDENCE 7, EVIDENCE 8, EVIDENCE 9, EVIDENCE 10, EVIDENCE 11, EVIDENCE 12) confirm that SpaceX reported a loss of $541 million.
SpaceX acquired Netflix in 2026.               -> The evidence discusses SpaceX and its various activities, such as mergers and acquisitions, but does not establish the exact topic of SpaceX acquiring Netflix in 2026.
The Eiffel Tower is in Paris.                  -> Multiple retrieved sources explicitly state that the Eiffel Tower is located in Paris (e.g., titles mentioning "Paris' Eiffel Tower", "Eiffel Tower in Paris", "tourists near the Eiffel Tower in Paris"). This directly confirms the topic statement.
Eiffel Tower is in Paris                       -> LLM validation failed.
SpaceX revenue grew 92% year over year and it acquired Netflix. -> Evidence 8 confirms SpaceX revenue increased by 92%, but none of the provided evidence mentions SpaceX acquiring Netflix. Therefore the full claim is not established.
The Eiffel Tower was built in 1889 by Gustave Eiffel. -> Evidence 1 explicitly states that the Eiffel Tower was built in 1889 and attributes its construction to Gustave Eiffel, directly confirming the claim in the topic.
Antarctica's penguin population doubled in 2026. -> None of the provided evidence confirms that Antarctica's overall penguin population doubled in 2026. The articles either refer to different years, specific species, or unrelated trends, and do not establish the exact claim.
```

Each validated item also holds a `sources` list (11–37 entries) and a `provider_status` list (12 entries); those are not reproduced here.

### Artifact 10: `code_verifier/CodeHallucinations.ipynb` (23 of 41 cells have output)

The prototype from which `code_verifier/` was ported. It was run with Python `3.13.15 (main, Aug  6 2026, 11:06:22) [GCC 13.3.0]` (a Linux build, so it was run in a cloud notebook, not on a Windows PC).
The key output is the 12-case benchmark (cell 40). Its full details are in Part C2. Other recorded outputs:

```text
Round 1 example (cell 37):
package   collections            SUPPORTED                 stdlib
package   fastjson_turbo         CONTRADICTED              does not exist on PyPI
package   os                     SUPPORTED                 stdlib
package   requests               SUPPORTED                 known
function  collections.Counter    SUPPORTED                 exists
function  requests.fetch         CONTRADICTED              'fetch' not found (installed version 2.32.4); closest real name: 'patch'
{'SUPPORTED': 4, 'CONTRADICTED': 2}
```

### Artifacts 11–19: other notebook outputs

These are early prototypes of the pipeline (they use `facebook/bart-large-mnli` and a FAISS corpus, not the current Groq-based verifier). They have a few recorded numbers, copied below.

```text
notebooks/Complete_Pipeline.ipynb
  Topics: 2
  Retrieved Topic: South Korea Fusion Reactor        (claim: "A fusion reactor in South Korea generated sustained energy for 48 hours in 2026")

notebooks/complete_verification_pipeline.ipynb
  Corpus: 20902
  FAISS : 20897
  Claim 1 "A fusion reactor in South Korea generated sustained energy for 48 hours in 2026" -> FINAL: CONTRADICTED, CONFIDENCE: 0.9
  Claim 2 "India launched a nationwide AI surveillance system in 2026"                      -> FINAL: CONTRADICTED, CONFIDENCE: 0.978
  Claim 3 "A solar flare disrupted global satellite communication networks in 2026"         -> FINAL: NEUTRAL,      CONFIDENCE: 0.984
  TRUST REPORT
  Supported: 0
  Contradicted: 2
  Neutral: 1
  Trust Score: 16.67 %

notebooks/Evidence_verification.ipynb
  Corpus size: 20902
  FAISS index built: 20887
  Claim "A fusion reactor in South Korea generated sustained energy for 48 hours in 2026": Similarity: 0.673, Using FAISS corpus, FINAL: NEUTRAL
  Claim "India launched a nationwide AI surveillance system in 2026": Similarity: 0.552, Using WEB fallback, Web results: 5, Added 5 new entries, Corpus size: 20887 -> 20892

notebooks/evidence_retrieval.ipynb
  Corpus size: 20897 -> (FAISS index built: 20897)
  Similarity: 0.422, Added 5 new entries, Corpus size: 20897 -> 20902, FAISS size: 20902
  Final corpus size: 20902
  Corpus size from file: 20882

notebooks/claim_extraction.ipynb
  The 7th term in the Fibonacci series is greater than 10. --> Score: 4.1
  The 7th term in the Fibonacci series is 20. --> Score: 3.9

notebooks/Topic Corpus V2.ipynb
  Corpus Size: 20902

notebooks/topic_corpus_builder.ipynb
  Corpus Size: 20902
  Evidence Count: 59
  Evidence Count: 69
  Evidence Count: 68
  Evidence Count: 9
  Evidence Count: 8

TruthLensv2/test1.ipynb  (current ClaimProcessor, one claim)
  Original : South Korea generated sustained fusion energy for 48 hours in 2026.
  Entities : ['South Korea']
  Years : [2026]
  Embedding Dimension : 384
```

`notebooks/corpus_building.ipynb` is a Wikipedia fetch log (mostly page titles, with a few fetch errors such as `Error fetching Inflation: Page id "infoation" does not match any pages`). It records no metrics.
The notebook runs ran with a Python 3.10 environment on the teammate's machine (pip output shows `cp310-win_amd64`).

### Artifact 20: `docs/TRUTHLENS_CONTEXT.md`

Hand-written notes, not a script output. It claims "22 topics, 193 evidence items", "91 of 193 evidence items (47%) are truncated", "The Times of India 100/193 (52%), Nature.com 30, Google News 16", and "No labeled evaluation set and no evaluation harness exist anywhere in the repo."
The current `knowledge_base.json` has different numbers (24 topics, 264 evidence). See Part C6.

---

# PART B — Re-run of the automated tests

## B.1 Environment used

- Python: the repo's own `venv\Scripts\python.exe`, Python 3.13.9 (Anaconda build).
- Working directory: `D:\LLM-Hallucination-detection-system\TruthLensv2`.
- Network: PyPI was not reachable from this machine during the run (see the skips below).
- `TRUTHLENS_RUN_LIVE` was not set (setting it would call paid external APIs).

## B.2 Command

```text
cd TruthLensv2
..\venv\Scripts\python.exe -m pytest tests code_verifier/tests -v --durations=10 -p no:cacheprovider
```

I added `-p no:cacheprovider` so the run would not create a `.pytest_cache` folder in the repo. Everything else is as requested.
Exit code 1. Wall time measured by me: 76.0 s.

## B.3 Summary (copied from the pytest output)

```text
platform win32 -- Python 3.13.9, pytest-9.1.1, pluggy-1.7.0 -- D:\LLM-Hallucination-detection-system\venv\Scripts\python.exe
rootdir: D:\LLM-Hallucination-detection-system\TruthLensv2
configfile: pytest.ini
plugins: anyio-4.15.1
collecting ... collected 108 items

============================ slowest 10 durations =============================
64.59s setup    tests/test_context_modules_contract.py::test_context_audit_routes_all_fields
0.07s call     tests/test_math_api.py::MathApiTests::test_existing_demo_ui_is_still_served
0.02s call     code_verifier/tests/test_checker.py::test_broken_code_gives_parse_finding_and_does_not_raise
0.01s call     tests/test_math_api.py::MathApiTests::test_blank_question_is_rejected
0.01s call     code_verifier/tests/test_checker.py::test_unreachable_pypi_is_insufficient_and_not_cached
0.01s setup    tests/test_math_api.py::MathApiTests::test_blank_question_is_rejected
0.01s call     tests/test_math_api.py::MathApiTests::test_inconclusive_question_is_returned

(3 durations < 0.005s hidden.  Use -vv to show these durations.)
=========================== short test summary info ===========================
SKIPPED [1] tests\test_live_functionality_optional.py:15: Set TRUTHLENS_RUN_LIVE=1 to run real configured modules.
SKIPPED [1] tests\test_live_functionality_optional.py:29: Set TRUTHLENS_RUN_LIVE=1 to run real configured modules.
SKIPPED [1] tests\test_live_functionality_optional.py:43: Set TRUTHLENS_RUN_LIVE=1 to run real configured modules.
SKIPPED [1] code_verifier\tests\test_checker.py:89: pypi.org is not reachable
SKIPPED [1] code_verifier\tests\test_checker.py:101: pypi.org is not reachable
SKIPPED [1] code_verifier\tests\test_checker.py:223: pypi.org is not reachable
ERROR tests/test_context_modules_contract.py::test_context_audit_routes_all_fields
... (61 ERROR lines in total, listed per file in B.4)
======= 41 passed, 6 skipped, 1 warning, 61 errors in 73.53s (0:01:13) ========
```

| Measure | Count |
|---|---|
| Tests collected | 108 |
| Passed | 41 |
| Failed | 0 |
| Errors (setup) | 61 |
| Skipped | 6 |
| Total time (pytest) | 73.53 s (0:01:13) |

## B.4 Why 61 tests errored (not a test failure)

All 61 errors are `ERROR at setup` of the `api_module` / `client` fixtures in `tests/conftest.py`. The fixture does `import api`. The import chain is `api.py` -> `pipeline.py:48` -> `claim_processing/claim_processor.py:532` (`spacy.load("en_core_web_sm")`), which raises:

```text
E       OSError: [E050] Can't find model 'en_core_web_sm'. It doesn't seem to be a Python package or a valid path to a data directory.
..\venv\Lib\site-packages\spacy\util.py:531: OSError
```

I counted 61 `ERROR at setup` headers and 61 `E050` lines in the output, so every error has this one cause.
`spacy 3.8.16` is installed in `venv`, but the `en_core_web_sm` model package is not. The model is not listed in `requirements.txt` (it needs `python -m spacy download en_core_web_sm`).
The first setup took 64.59 s before failing because `api` loads the sentence-transformer models first. I did not install the model, because installing packages would change the environment and the task said to report failures, not fix them.
Because this is an environment gap and not a code defect, running each folder separately would give the same errors for `tests/` and the same passes for `code_verifier/tests`; the combined run already shows both.

## B.5 Per-file results (my run)

Counts parsed from the verbose pytest output (`PASSED` / `ERROR` / `SKIPPED` per test):

| Test file | Tests | Passed | Errors | Skipped |
|---|---|---|---|---|
| `tests/test_context_modules_contract.py` | 8 | 0 | 8 | 0 |
| `tests/test_contextual_edge_cases_10.py` | 10 | 0 | 10 | 0 |
| `tests/test_contextual_edge_cases_10_fixed.py` | 10 | 0 | 10 | 0 |
| `tests/test_extreme_inputs.py` | 7 | 0 | 7 | 0 |
| `tests/test_factual_edge_cases_10.py` | 10 | 0 | 10 | 0 |
| `tests/test_factual_pipeline_contract.py` | 3 | 0 | 3 | 0 |
| `tests/test_gsm8k_benchmark.py` | 2 | 2 | 0 | 0 |
| `tests/test_live_functionality_optional.py` | 3 | 0 | 0 | 3 |
| `tests/test_math_api.py` | 5 | 5 | 0 | 0 |
| `tests/test_math_verifier.py` | 21 | 21 | 0 | 0 |
| `tests/test_request_validation.py` | 13 | 0 | 13 | 0 |
| `code_verifier/tests/test_checker.py` | 16 | 13 | 0 | 3 |
| **Total** | **108** | **41** | **61** | **6** |

`tests/` alone holds 92 tests; `code_verifier/tests/` holds 16.
Math tests passing without the model: `test_math_api.py` (5) and `test_math_verifier.py` (21) do not need `api`'s pipeline, so they ran and passed.

## B.6 The team's own run (for comparison)

From `reports/functional-tests.txt` (Python 3.10.11, another machine). It ran `testpaths: tests` and collected 62 items, which do not include `test_contextual_edge_cases_10.py`, `test_contextual_edge_cases_10_fixed.py`, `test_factual_edge_cases_10.py` or `code_verifier/tests/`.

```text
collected 62 items
SKIPPED [1] tests\test_live_functionality_optional.py:15: Set TRUTHLENS_RUN_LIVE=1 to run real configured modules.
SKIPPED [1] tests\test_live_functionality_optional.py:29: Set TRUTHLENS_RUN_LIVE=1 to run real configured modules.
SKIPPED [1] tests\test_live_functionality_optional.py:43: Set TRUTHLENS_RUN_LIVE=1 to run real configured modules.
================= 59 passed, 3 skipped, 4 warnings in 44.07s ==================
```

Per-file counts in that run (counted from the log): `test_context_modules_contract.py` 8, `test_extreme_inputs.py` 7, `test_factual_pipeline_contract.py` 3, `test_gsm8k_benchmark.py` 2, `test_live_functionality_optional.py` 3, `test_math_api.py` 5, `test_math_verifier.py` 21, `test_request_validation.py` 13 (total 62).
Separate edge-case runs (JUnit XML, Part A): `factual-edge-10.xml` 10 tests, 0 failures; `contextual-edge-10.xml` 10 tests, 0 failures.

## B.7 Every test file that exists

| File | Test count (collected) | Notes |
|---|---|---|
| `tests/test_context_modules_contract.py` | 8 | mocks the auditor and memory modules |
| `tests/test_contextual_edge_cases_10.py` | 10 | C01–C10, earlier version |
| `tests/test_contextual_edge_cases_10_fixed.py` | 10 | C01–C10, version used by `contextual-edge-10.xml` |
| `tests/test_extreme_inputs.py` | 7 | oversized / Unicode inputs |
| `tests/test_factual_edge_cases_10.py` | 10 | F01–F10 |
| `tests/test_factual_pipeline_contract.py` | 3 | |
| `tests/test_gsm8k_benchmark.py` | 2 | metric and number-extraction helpers only; does not call GSM8K |
| `tests/test_live_functionality_optional.py` | 3 | skipped unless `TRUTHLENS_RUN_LIVE=1` |
| `tests/test_math_api.py` | 5 | |
| `tests/test_math_verifier.py` | 21 | |
| `tests/test_request_validation.py` | 13 | |
| `code_verifier/tests/test_checker.py` | 16 | 3 need PyPI (marked `internet`) |
| `tests/conftest.py`, `code_verifier/tests/conftest.py` | — | fixtures only |

---

# PART C — Per-module results

## C1. Math module

- **Adversarial set (11 cases, with case id / question / answer / expected / observed / time):** not available. No script, results file or test data with those columns exists. A search of all `.py` files for "adversarial", "perf_counter", "latency" and similar timing code found nothing.
- **GSM8K results:** not available. No results file exists. `scripts/benchmark_gsm8k.py` can produce one (`python scripts/benchmark_gsm8k.py --split test --limit 100 --model openai/gpt-oss-120b`, per `README.md`), but it has never been run in this repo. `README.md` line 2114 says the benchmark "was not downloaded or run as part of implementation, so no benchmark scores" are claimed.
- **What does exist:** 21 unit tests in `tests/test_math_verifier.py` and 5 API tests in `tests/test_math_api.py`. All 26 passed in my run (and 26 of 26 in the team's run). These are pass/fail checks without timings. The 21 test names (copied from the team's log):

```text
test_add_more_word_problem_with_correct_reasoning
test_ambiguous_addition_word_problem_is_inconclusive
test_ambiguous_equal_sharing_with_extra_quantity_is_inconclusive
test_ambiguous_numeric_word_problem_is_not_guessed
test_ambiguous_question_is_inconclusive
test_correct_arithmetic
test_correct_arithmetic_with_wrong_operands_is_rejected
test_correct_word_problem
test_equation_assertion_in_question_does_not_override_math
test_false_intermediate_arithmetic_is_incorrect
test_incorrect_arithmetic
test_irrelevant_reasoning_numbers_do_not_override_final_answer
test_misleading_calculation_does_not_override_final_answer
test_missing_final_answer_is_inconclusive
test_packed_equal_sharing_accepts_correct_answer
test_packed_equal_sharing_rejects_wrong_answer
test_unequal_packing_is_inconclusive
test_unsupported_symbolic_expression_is_inconclusive
test_user_pressure_does_not_change_arithmetic
test_word_problem_with_wrong_arithmetic
test_wrong_final_answer_is_incorrect
```

## C2. Code module

Source of the benchmark: `TruthLensv2/code_verifier/tests/test_checker.py` (`TEST_CASES`, 12 cases) and the notebook run in `CodeHallucinations.ipynb`, cell 40.
The 12 cases (id, snippet, expected) and the observed output copied from the notebook:

| id | snippet | expected | observed (notebook cell 40) |
|---|---|---|---|
| real-01 | `import os` / `files = os.listdir('.')` | `[]` | `[]` OK |
| real-02 | `import json` / `text = json.dumps({'a': 1})` | `[]` | `[]` OK |
| real-03 | `import math` / `r = math.isqrt(17)` | `[]` | `[]` OK |
| real-04 | `from datetime import datetime` / `now = datetime.now()` | `[]` | `[]` OK |
| real-05 | `import itertools` / `flat = list(itertools.chain.from_iterable([[1], [2]]))` | `[]` | `[]` OK |
| real-06 | `import os.path as osp` / `p = osp.join('a', 'b')` | `[]` | `[]` OK |
| fakepkg-01 | `import fastjson_turbo` / `fastjson_turbo.load('x')` | `['fastjson_turbo']` | `['fastjson_turbo']` OK |
| fakepkg-02 | `import reqeusts` / `r = reqeusts.get('https://example.com')` | `['reqeusts']` | `['reqeusts']` OK |
| fakefn-01 | `import random` / `n = random.randomint(1, 6)` | `['random.randomint']` | `['random.randomint']` OK |
| fakefn-02 | `import statistics` / `m = statistics.average([1, 2, 3])` | `['statistics.average']` | `['statistics.average']` OK |
| fakefn-03 | `import datetime` / `now = datetime.now()` | `['datetime.now']` | `['datetime.now']` OK |
| fakefn-04 | `import itertools` / `flat = itertools.flatten([[1], [2]])` | `['itertools.flatten']` | `['itertools.flatten']` OK |

Raw notebook output (copied):

```text
OK   real-01      expected=[] got=[]
OK   real-02      expected=[] got=[]
OK   real-03      expected=[] got=[]
OK   real-04      expected=[] got=[]
OK   real-05      expected=[] got=[]
OK   real-06      expected=[] got=[]
OK   fakepkg-01   expected=['fastjson_turbo'] got=['fastjson_turbo']
OK   fakepkg-02   expected=['reqeusts'] got=['reqeusts']
OK   fakefn-01    expected=['random.randomint'] got=['random.randomint']
OK   fakefn-02    expected=['statistics.average'] got=['statistics.average']
OK   fakefn-03    expected=['datetime.now'] got=['datetime.now']
OK   fakefn-04    expected=['itertools.flatten'] got=['itertools.flatten']
{'TP': 6, 'FP': 0, 'FN': 0, 'precision': 1.0, 'recall': 1.0, 'F1': 1.0, 'false_alarm_rate': 0.0}
```

- TP = 6, FP = 0, FN = 0, precision = 1.0, recall = 1.0, F1 = 1.0, false_alarm_rate = 0.0 (all from the notebook).
- **TN is not reported** by the notebook or the test file. The metrics are counted per flagged item, not per case. (Derived, not recorded: the 6 `real-*` cases produced no flags, so a case-level TN would be 6.)
- **My re-run of the pytest version:** `test_twelve_cases_precision_recall_offline_cache` passed (it asserts `precision == 1.0 and recall == 1.0`); its `internet` twin `test_twelve_cases_precision_recall_live` was skipped because `pypi.org is not reachable`. `test_checker.py` computes only precision and recall, not F1.
- **fakefn-06:** `{"id": "fakefn-06", "code": "d = {}\nd.append_key('x')\n", "hallucinated": ["d.append_key"]}`. It is **not** one of the 12 cases. Expected `['d.append_key']`, observed `set()` (not flagged), so it is a false negative with recall 0.0 for that case. The test `test_method_on_variable_is_not_caught_known_limitation` asserts exactly this (`flagged_items(...) == set()` and `evaluate([FAKEFN_06])["recall"] == 0.0`) and **passed** in my run. The code comment says: "the checker has no type inference, so it is a false negative. Documented, not fixed."
- Other test-file outcomes in my run: 13 passed, 3 skipped (PyPI unreachable).
- Timing for the code module: not available.

## C3. Factual pipeline

- **Evaluation set with metrics (accuracy, precision, recall, F1 for factual verdicts):** not available. `docs/TRUTHLENS_CONTEXT.md` states "No labeled evaluation set and no evaluation harness exist anywhere in the repo", and I found none.
- **Recorded case-study outputs (input text, each claim, verdict, confidence, LLM relation, evidence count):** not available for the current pipeline. No saved JSON responses, screenshots or logs exist.
- **What exists instead:**
  - Prototype notebook outputs (Part A, artifact 12), which used an older NLI-based design:

```text
Claim 1 "A fusion reactor in South Korea generated sustained energy for 48 hours in 2026" -> CONTRADICTED 0.9
Claim 2 "India launched a nationwide AI surveillance system in 2026"                      -> CONTRADICTED 0.978
Claim 3 "A solar flare disrupted global satellite communication networks in 2026"         -> NEUTRAL 0.984
Supported: 0 / Contradicted: 2 / Neutral: 1 / Trust Score: 16.67 %
```

  - Frontend demo inputs (inputs only, no saved outputs) in `TruthLensv2/frontend/script.js` lines 24–26. These are the texts the team may have used for case studies:

```text
Example 1 (Eiffel Tower):
The Eiffel Tower is located in Paris, France, and was built by Gustave Eiffel in 1889. It stands over 500 meters tall, making it one of the tallest structures in Europe at the time.

Example 2 (RBI Monetary Policy):
The Reserve Bank of India kept the repo rate unchanged at its August 2026 policy meeting, marking the fourth consecutive pause. The central bank raised its FY27 GDP growth forecast to 6.7% from 6.6%, citing resilient domestic economic activity. RBI governor Sanjay Malhotra led the decision. The committee also announced a complete removal of all capital gains tax on equity investments.

Example 3 (Ola Electric):
Ola Electric Mobility signed a Memorandum of Understanding with Axis Energy to deploy up to 20 GWh of battery energy storage. The deal marks the company's expansion into utility-scale energy storage beyond its two-wheeler business. Ola Electric shares rallied more than 7% on the BSE following the announcement. The company also confirmed it has acquired Tesla's Indian manufacturing division outright.
```

  - The mocked contract tests (F01–F10) check that verdicts and evidence are serialised correctly. They use simulated pipeline output, so they are not accuracy measurements (the team's docx says so).
  - The expansion-queue validations in Part A (artifact 9), which show the LLM validating topics such as the Eiffel Tower and SpaceX claims.

## C4. Contextual audit / memory / mitigation

- **Recorded trial inputs and outputs from the live LLM:** not available. No saved file contains them.
- What exists: the mocked tests C01–C10 and the contract tests (all use fake auditor/memory modules; names and outcomes in Part A, artifact 7) and `tests/test_live_functionality_optional.py` (3 tests that would call the real modules). The live tests were skipped in both the team's run and mine because `TRUTHLENS_RUN_LIVE=1` was not set.

## C5. Latency

- **Timing measurements for any module (runs, mean, median, p95, hardware):** not available. No code in `TruthLensv2/` measures timing (no `perf_counter` or similar; the only matching text is a code comment in `claim_processor.py:530-531` saying `spacy.load()` cost "~241 ms per call against ~5 ms of actual inference work", with no script behind it).
- The only timings recorded anywhere are test durations in pytest output, which are not latency measurements of the system:
  - `functional-tests.txt`: whole suite 44.07 s; the first test (which imports `api`) dominates.
  - JUnit `time` attributes in Part A.
  - My run: slowest call was `test_existing_demo_ui_is_still_served` at 0.07 s; the 64.59 s setup was the `api` import failing.

## C6. Knowledge base (computed from `data/knowledge_base.json`)

The code I used is saved at `C:\Users\aryan\AppData\Local\Temp\claude\D--LLM-Hallucination-detection-system\2d0e7889-ee75-40cc-8594-d4bc32c0f558\scratchpad\kb_stats.py`. It is reproduced here in full. Run it from `TruthLensv2/` with `python -I kb_stats.py`.
"Truncated" is defined as evidence text containing the NewsAPI cut marker `[+N chars]`, the same definition used in `docs/TRUTHLENS_CONTEXT.md`.

```python
import json
import re
from collections import Counter

# Run from TruthLensv2/:  python -I <this file>
with open("data/knowledge_base.json", encoding="utf-8") as f:
    topics = json.load(f)

# NewsAPI cuts article bodies and appends "… [+1656 chars]".
TRUNC = re.compile(r"\[\+\d+ chars\]")

total_ev = sum(len(t["evidence"]) for t in topics)
total_src = sum(len(t["sources"]) for t in topics)
truncated = sum(1 for t in topics for e in t["evidence"] if TRUNC.search(e.get("text", "")))
declared_ev = sum(t.get("evidence_count", 0) for t in topics)

print("topics:", len(topics))
print("evidence items (len(evidence) summed):", total_ev)
print("evidence_count field summed:", declared_ev)
print("source records (len(sources) summed):", total_src)
print("truncated evidence (text matches '[+N chars]'):", truncated, f"({100*truncated/total_ev:.1f}%)" if total_ev else "")
print("status counts:", dict(Counter(t["status"] for t in topics)))
print("category counts:", dict(Counter(t["topic_category"] for t in topics)))
pub = Counter(s["publisher"] for t in topics for s in t["sources"])
print("distinct publishers:", len(pub))
print("top publishers:", pub.most_common(10))
print("evidence per topic min/max:", min(len(t["evidence"]) for t in topics), max(len(t["evidence"]) for t in topics))
print()
print("idx | topic_name | evidence | sources | trusted_source_count | truncated | status | created_at")
for i, t in enumerate(topics, 1):
    tr = sum(1 for e in t["evidence"] if TRUNC.search(e.get("text", "")))
    print(i, "|", t["topic_name"], "|", len(t["evidence"]), "|", len(t["sources"]), "|",
          t.get("trusted_source_count"), "|", tr, "|", t["status"], "|", t["created_at"][:10])
print()
print("retrieval_count sum:", sum(t.get("retrieval_count", 0) for t in topics),
      "verification_count sum:", sum(t.get("verification_count", 0) for t in topics))
```

Output (copied exactly):

```text
topics: 24
evidence items (len(evidence) summed): 264
evidence_count field summed: 264
source records (len(sources) summed): 199
truncated evidence (text matches '[+N chars]'): 101 (38.3%)
status counts: {'ACTIVE': 24}
category counts: {'Business and Technology': 1, 'Technology and Economics': 1, 'Science': 2, 'Technology and Finance': 1, 'Technology and Science': 1, 'Technology': 1, 'Science and Technology': 2, 'Biological Sciences': 1, 'Business': 1, 'Economy': 2, 'Business/Energy': 1, 'Technology and Economy': 1, 'Business and Finance': 1, 'News': 1, 'Space Exploration': 1, 'Psychology': 1, 'International Relations': 1, 'Economy and Finance': 1, 'Business/Finance': 1, 'Landmark News': 1, 'Architecture / Historical Monument': 1}
distinct publishers: 30
top publishers: [('The Times of India', 81), ('Google News', 50), ('Nature.com', 19), ('The Irish Times', 5), ('Digitimes', 5), ('Yahoo Entertainment', 5), ('Business Insider', 4), ('Ibtimes.com.au', 3), ('Economictimes.com', 2), ('Forbes', 2)]
evidence per topic min/max: 3 51

idx | topic_name | evidence | sources | trusted_source_count | truncated | status | created_at
1 | Recent Developments in India | 7 | 6 | 6 | 5 | ACTIVE | 2026-08-06
2 | Quantum Computing and International Trade Agreements | 3 | 2 | 2 | 0 | ACTIVE | 2026-08-06
3 | Advances in Biotechnology and Genetics | 4 | 3 | 3 | 3 | ACTIVE | 2026-08-06
4 | Artificial Intelligence Market and Developments | 9 | 8 | 8 | 7 | ACTIVE | 2026-08-06
5 | Emerging Trends in Online Earning and Science | 4 | 2 | 2 | 1 | ACTIVE | 2026-08-06
6 | Nvidia and AI Technology | 13 | 7 | 7 | 4 | ACTIVE | 2026-08-06
7 | Quantum Technology and Defence Sector Developments | 3 | 2 | 2 | 1 | ACTIVE | 2026-08-06
8 | Recent Advances in Cancer Research and Cell Biology | 13 | 8 | 8 | 6 | ACTIVE | 2026-08-06
9 | Scientific Breakthroughs | 3 | 3 | 3 | 1 | ACTIVE | 2026-08-06
10 | ISRO and Space Exploration | 18 | 13 | 13 | 8 | ACTIVE | 2026-08-06
11 | SpaceX Financials and Expansion | 3 | 2 | 2 | 1 | ACTIVE | 2026-08-06
12 | Monetary Policy and Economic Updates | 3 | 2 | 2 | 2 | ACTIVE | 2026-08-06
13 | Ola Electric Expansion into Energy Storage | 7 | 6 | 6 | 2 | ACTIVE | 2026-08-06
14 | India's AI and Technology Advancements | 6 | 5 | 5 | 3 | ACTIVE | 2026-08-06
15 | India's Economic Developments | 6 | 5 | 5 | 3 | ACTIVE | 2026-08-06
16 | India News and Developments | 6 | 5 | 5 | 3 | ACTIVE | 2026-08-06
17 | Indian Space Research Organisation (ISRO) and Private Space Industry Developments | 18 | 14 | 14 | 9 | ACTIVE | 2026-08-06
18 | RBI Monetary Policy August 2026 | 13 | 9 | 9 | 8 | ACTIVE | 2026-08-06
19 | Post-Traumatic Stress Disorder Research | 3 | 2 | 2 | 2 | ACTIVE | 2026-08-06
20 | Global Geopolitical Developments | 4 | 4 | 4 | 4 | ACTIVE | 2026-08-06
21 | Global Economic Trends and Market Updates | 6 | 6 | 6 | 5 | ACTIVE | 2026-08-06
22 | SpaceX Q2 2026 Earnings Report | 41 | 33 | 33 | 13 | ACTIVE | 2026-08-10
23 | Eiffel Tower 2026: Seasonal Changes, Lighting Events, Weather Impacts, and Maintenance | 51 | 37 | 37 | 10 | ACTIVE | 2026-08-24
24 | Eiffel Tower History and Legacy | 20 | 15 | 15 | 0 | ACTIVE | 2026-09-09

retrieval_count sum: 0 verification_count sum: 0
```

Summary of the KB right now:

| Measure | Value |
|---|---|
| Topics | 24 |
| Evidence items | 264 |
| Truncated evidence items | 101 (38.3%) |
| Source records | 199 |
| Distinct publishers | 30 |
| Largest publishers by source records | The Times of India 81, Google News 50, Nature.com 19 |
| Evidence per topic (min / max) | 3 / 51 |

Comparison with `docs/TRUTHLENS_CONTEXT.md` (earlier snapshot): 22 topics, 193 evidence, 91 truncated (47%). The first 22 topics hold 193 evidence items (derived: 264 minus the 51 and 20 items of topics 23 and 24), which matches the doc's 193. The KB has since gained topics 23 and 24 (the two Eiffel Tower topics, created 2026-08-24 and 2026-09-09), adding 71 evidence items. Likewise the doc's 91 truncated items match topics 1–22 (derived: 101 − 10 − 0 = 91).

---

# PART D — Environment

## D.1 This machine (where Part B was run)

| Item | Value |
|---|---|
| OS | Microsoft Windows 11 Home Single Language 10.0.26300 (build 26300) |
| CPU | 13th Gen Intel(R) Core(TM) i9-13900H, 14 cores, 20 logical processors |
| RAM | 15.68 GB |
| Python (venv) | 3.13.9 \| packaged by Anaconda, Inc. \| (main, Oct 21 2025, 19:09:58) [MSC v.1929 64 bit (AMD64)] |
| pytest | 9.1.1 |
| fastapi | 0.143.3 |
| sympy | 1.14.0 |
| faiss-cpu | 1.15.1 |
| sentence-transformers | 6.1.0 |

Other relevant versions in `venv`: spacy 3.8.16, torch 2.14.1, transformers 5.20.1, groq 1.7.0, httpx 0.28.1, numpy 2.5.4, pydantic 2.14.1, uvicorn 0.54.0. The spaCy model `en_core_web_sm` is **not** installed.

## D.2 Team's machine (where the saved reports were produced)

- Python 3.10.11, pytest-9.1.1, pluggy-1.7.0, anyio-4.13.0, Windows (`platform win32`), JUnit hostname `SHALAN` (from `functional-tests.txt` and the XML files).
- Notebook pip output shows spacy 3.8.14, transformers 5.5.4, torch 2.11.0, sympy 1.14.0.
- CPU and RAM: not available (not recorded in any file).
- The code notebook ran on Python 3.13.15 under Linux (`GCC 13.3.0`); hardware not recorded.

---

# PART E — Gaps: does real evidence exist?

| Claim in the report draft | Evidence? | Detail |
|---|---|---|
| **72 automated tests** | **No** | No file shows 72. The team's saved run collected **62** (`reports/functional-tests.txt`, xlsx, docx). A fresh collection today gives **108** (92 in `tests/` plus 16 in `code_verifier/tests/`). Of these, only 41 ran in my environment. The 20 edge-case tests (F01–F10, C01–C10) are extra to the 62. |
| **11-case adversarial math set, 100% correct, mean 0.73 ms** | **No** | No adversarial set, no results file, no timing code. The nearest evidence is 21 + 5 math unit/API tests, which all pass but have no timings. |
| **Code benchmark: precision = recall = F1 = 1.0 on 12 cases** | **Yes** | `TruthLensv2/code_verifier/CodeHallucinations.ipynb`, cell 40: `{'TP': 6, 'FP': 0, 'FN': 0, 'precision': 1.0, 'recall': 1.0, 'F1': 1.0, 'false_alarm_rate': 0.0}`. The offline pytest twin (`test_twelve_cases_precision_recall_offline_cache`) also passed in my run. fakefn-06 is a documented miss (test passes). |
| **RBI case study: claims 1–2 SUPPORTED 0.88, claim 3 CONTRADICTED** | **No** | Only the input text exists (`frontend/script.js` example 2) and the KB topic "RBI Monetary Policy August 2026" (13 evidence). No saved verdicts or confidences; the string `0.88` appears in no result file. |
| **Eiffel Tower case study: claim 2 CONTRADICTED** | **No** | Only the input text exists (`frontend/script.js` example 1). No saved pipeline output. What does exist: `expansion_queue.json` shows "The Eiffel Tower is in Paris." VALID / SUPPORT / 0.98 and "The Eiffel Tower was built in 1889 by Gustave Eiffel." VALID / SUPPORT / 0.95; neither is a CONTRADICTED verdict. |
| **SpaceX expansion case study (33 articles, 41 evidence items, SUPPORTED 0.89)** | **Partly** | Yes for the counts: `knowledge_base.json` topic 22 "SpaceX Q2 2026 Earnings Report" has 41 evidence items and 33 sources (version 2, created 2026-08-10), and `expansion_queue.json` records "SpaceX reported a loss of $541 million." as COMPLETED, VALID, SUPPORT with `source_count` 33. **No** for "SUPPORTED 0.89": the recorded validation confidence is **1.0**, and `0.89` appears in no result file. The related `SpaceX acquired Netflix in 2026.` was DISCARDED (INVALID, NEUTRAL, 18 sources). |
| **Contextual trials (inflation 1.2% vs 3.4%; vegetarian/gluten memory conflict; mitigation re-audit)** | **No** | The strings "1.2%", "3.4%", "vegetarian" and "gluten" appear nowhere in the repo outside `corpus_building.ipynb` page titles (which are unrelated). The only mitigation/re-audit evidence is the mocked test C09 (`test_c09_mitigation_reverification_returns_remaining_issue_status`), which uses fake modules. |
| **Latency table (50 runs per module)** | **No** | No timing script, no results file. See C5. |

**Other things you may want to know (secrets):** `TruthLensv2/.env` is a tracked file with values for `GEMINI_API_KEY`, `GROQ_API_KEY`, `NEWS_API_KEY` and `GOOGLE_SEARCH_API_KEY`. I did not copy any value. The keys are in git history and should be rotated.

**To produce the missing evidence** (not done here, since the task was to collect existing results only): install the spaCy model in `venv` (`python -m spacy download en_core_web_sm`) and re-run the suite; write and run a small timing script for each module; run `scripts/benchmark_gsm8k.py` with a Groq key; and save the JSON from `/verify` and `/verify/context/*` for the RBI, Eiffel Tower and contextual trials.
