# JARS

## A Hybrid Deterministic and Semantic Verification Framework for LLM Hallucination Detection

JARS checks answers written by Large Language Models (LLMs) for hallucinations. It covers four kinds of output: factual statements, arithmetic, Python code and multi-turn conversations. Each answer is checked against a reference that suits it: a knowledge base of news articles, exact rational arithmetic, the Python syntax tree and the PyPI index, or the context and conversation history the user supplies.

Most hallucination detectors ask a second LLM to grade the answer. JARS doesn't let an LLM make the final decision in the factual, math or code modules. The factual pipeline combines six deterministic evidence signals with one narrow LLM label through fixed rules. The math and code modules use no LLM at all. When the evidence isn't good enough, JARS says `INSUFFICIENT_INFORMATION` instead of guessing.

**Team (VIT Mumbai, Computer Engineering, group 27P31; guide Dr. Amit Nerurkar):** Aryan Kulkarni, Rishant Singh, Jyotsna Kasibhotla, Siddharth Metkari

---

## Contents

1. [The four modules](#the-four-modules)
2. [Results](#results)
3. [Architecture](#architecture)
4. [Factual verification pipeline](#factual-verification-pipeline)
5. [Knowledge expansion](#knowledge-expansion)
6. [Math verification](#math-verification)
7. [Code verification](#code-verification)
8. [Contextual audit, memory analysis and mitigation](#contextual-audit-memory-analysis-and-mitigation)
9. [API reference](#api-reference)
10. [Project structure](#project-structure)
11. [Setup and running](#setup-and-running)
12. [Tests](#tests)
13. [Demo inputs](#demo-inputs)
14. [Design principles](#design-principles)
15. [Limitations](#limitations)
16. [Future work](#future-work)
17. [Guide for team members](#guide-for-team-members)

---

## The four modules

| Module               | What it checks                                               | How it decides                                                    | Uses an LLM?                                 | Verdicts                                                                       |
| -------------------- | ------------------------------------------------------------ | ----------------------------------------------------------------- | -------------------------------------------- | ------------------------------------------------------------------------------ |
| Factual verification | Claims in an answer, against the knowledge base              | Hybrid retrieval, six signals and seven fusion rules              | Claim extraction and one relation label only | `SUPPORTED`, `CONTRADICTED`, `PARTIALLY_SUPPORTED`, `INSUFFICIENT_INFORMATION` |
| Math verification    | Arithmetic answers and their working                         | Rebuilds the expression from the question and computes it exactly | No                                           | `VERIFIED`, `INCORRECT`, `UNABLE_TO_VERIFY`                                    |
| Code verification    | Imports and function calls in Python code                    | Syntax tree, standard library, installed packages and PyPI        | No                                           | `SUPPORTED`, `CONTRADICTED`, `INSUFFICIENT_INFORMATION` per item               |
| Contextual audit     | An answer against the context, conversation and instructions | Four-dimension audit, memory analysis, mitigation with re-audit   | Yes                                          | Per dimension (see below)                                                      |

The web interface has five modes: Factual, Math, Code, Contextual audit and Context Memory Analysis.

---

## Results

These numbers come from the saved test runs and the project data. Nothing else has been measured.

| What                                               | Result                                                                                      |
| -------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| Main test suite (team run, Python 3.10.11)         | 62 tests: 59 passed, 3 skipped, 44.07 s                                                     |
| Code verifier unit tests                           | 16 tests: 13 passed, 3 skipped (pypi.org unreachable)                                       |
| All runs combined                                  | 98 tests: 92 passed, 6 skipped, 0 failed                                                    |
| Math module                                        | 21 unit tests and 5 API tests, all passed                                                   |
| Edge cases F01–F10 (factual), C01–C10 (contextual) | 20 of 20 passed (LLM and auditor mocked)                                                    |
| Code benchmark                                     | 12 cases: TP 6, FP 0, FN 0, so precision = recall = F1 = 1.0                                |
| Knowledge base                                     | 24 topics, 264 evidence items (101 truncated, 38.3%), 199 source records from 30 publishers |
| Expansion queue                                    | 10 entries: 3 VALID, 3 INVALID, 1 RETRY, 3 not yet processed                                |

The skipped tests either call paid or rate-limited APIs (they run only with `TRUTHLENS_RUN_LIVE=1`) or need pypi.org.

**Not measured yet:** accuracy of the live factual and contextual modules on labelled data, latency, and GSM8K accuracy. See [Limitations](#limitations).

---

## Architecture

JARS runs two FastAPI services and a single-page frontend.

```text
                      Browser (single-page frontend, 5 modes)
                         │                              │
                         ▼                              ▼
        ┌────────────────────────────────┐   ┌──────────────────────────┐
        │  Main server  api.py  :8000    │   │ Code server :8001        │
        │                                │   │ (falls back to :8002)    │
        │  /verify          factual      │   │                          │
        │  /verify/math     math         │   │ /check-code              │
        │  /verify/context  context      │   │   AST parsing            │
        │  /verify/context/memory        │   │   stdlib / installed     │
        │  /verify/context/full          │   │   PyPI + typosquat check │
        │  /verify/context/mitigate      │   │   function checks        │
        │  /health                       │   │ /health                  │
        └───────┬───────────────┬────────┘   └────────────┬─────────────┘
                │               │                         │
                ▼               ▼                         ▼
   knowledge_base.json      Groq API               PyPI JSON API
   FAISS + BM25 indexes     (gpt-oss-120b)
   expansion_queue.json
```

The code verifier runs as a separate service so that slow PyPI requests don't hold up the main server. Both services accept requests only from local origins.

---

## Factual verification pipeline

```text
LLM response
   │
   ▼
1. Claim extraction (RichClaimExtractor, LLM)
   │   atomic, self-contained claims
   ▼
2. Claim processing (ClaimProcessor)
   │   entities, keywords, years, 384-d embedding
   ▼
3. Hybrid retrieval (HybridRetriever)
   │   FAISS top 30 + BM25 top 30 → RRF (k = 60) → re-ranking
   ▼
4. Retrieval gate: confidence ≥ 0.50 and at least 2 evidence items?
   │
   ├── no  → INSUFFICIENT_INFORMATION, claim added to the expansion queue
   │
   └── yes
        ▼
5. Verifier: six deterministic signals + one LLM relation label
        ▼
6. Fusion rules 1–7 → verdict + confidence
```

### 1. Claim extraction

`RichClaimExtractor` sends the answer to `openai/gpt-oss-120b` on Groq at temperature 0. It uses a Claimify-style prompt with 17 rules. The prompt splits compound sentences, replaces pronouns with the names they refer to, keeps numbers and dates exactly, and drops opinions and filler. "The Eiffel Tower is in Paris and was built in 1889" becomes two claims, so one wrong part can't hide behind a right one. All prompts are listed in Appendix E of the project report.

### 2. Claim processing

`ClaimProcessor` adds to each claim:

- named entities (spaCy `en_core_web_sm`)
- keywords (KeyBERT)
- four-digit years from 1900 to 2099
- a 384-dimensional embedding (`all-MiniLM-L6-v2`)

The result is a `ProcessedClaim` record.

### 3. Hybrid retrieval

| Method                                                                | Finds                                             | Misses                         |
| --------------------------------------------------------------------- | ------------------------------------------------- | ------------------------------ |
| FAISS (`IndexFlatIP`, cosine similarity on normalised MiniLM vectors) | Evidence with the same meaning in different words | Exact names, numbers and dates |
| BM25 (`BM25Okapi`)                                                    | Exact entity names, numbers, dates and keywords   | Paraphrases and synonyms       |

The top 30 results from each are merged with Reciprocal Rank Fusion. Each document scores `sum(1 / (k + rank))` over both lists, with `k = 60`. RRF uses only ranks, so the two methods' different score scales don't matter. The merged candidates are then re-ranked with weights 0.35, 0.25, 0.20, 0.10 and 0.10.

A retrieved document is **not** treated as proof. It is only a candidate until the verifier has checked it.

### 4. Retrieval gate

A claim goes on to verification only if retrieval confidence is at least 0.50 and there are at least two evidence items. Otherwise it gets `INSUFFICIENT_INFORMATION` and is written to the expansion queue.

### 5. Verifier signals

| Signal               | What it measures                                                  |
| -------------------- | ----------------------------------------------------------------- |
| Entity consistency   | Whether the claim's named entities appear in the evidence         |
| Keyword consistency  | Keyword overlap between claim and evidence                        |
| Temporal consistency | Whether the claim's years match the evidence                      |
| Evidence coverage    | How much of the claim the evidence covers                         |
| Source reliability   | Stored reliability of the source (currently 0.90 for all sources) |
| Evidence agreement   | How much the evidence items agree (pairwise Jaccard similarity)   |

The LLM also labels the relation between the claim and the retrieved evidence as `SUPPORT`, `CONTRADICT`, `MIXED` or `NEUTRAL`, with a confidence. It judges only the evidence it is given, not its own memory.

### 6. Fusion rules

The rules are checked in order, and the first one that matches decides:

1. Fewer than two evidence items → `INSUFFICIENT_INFORMATION`
2. Coverage < 0.20 and entity consistency < 0.50 → `INSUFFICIENT_INFORMATION`
3. Source reliability < 0.50 and fewer than three evidence items → `INSUFFICIENT_INFORMATION`
4. Relation `CONTRADICT` with confidence ≥ 0.60 → `CONTRADICTED`
5. Relation `MIXED` with confidence ≥ 0.60 → `PARTIALLY_SUPPORTED`
6. Relation `SUPPORT` with confidence ≥ 0.60 → `SUPPORTED`
7. Anything else → `INSUFFICIENT_INFORMATION`

Rules 1–3 come first, so a confident LLM label can't produce a verdict on weak evidence. Contradiction is checked before support because passing a false claim as true is the worse error.

### Confidence

```text
verifier confidence = (mean(coverage, reliability, agreement, entity) + LLM confidence) / 2
final confidence    = min(retrieval confidence, verifier confidence)
```

For `INSUFFICIENT_INFORMATION`, the confidence is halved and capped at 0.49, so an abstention never looks like a confident answer. The confidence is a heuristic score. It has not been calibrated on labelled data.

---

## Knowledge expansion

A fixed knowledge base goes out of date. JARS uses failed retrievals to find out what knowledge is missing.

```text
INSUFFICIENT_INFORMATION
        │
        ▼
expansion_queue.json  (status PENDING)
        │
        ▼
Expansion scheduler (one cycle, or every 6 hours)
        │   RETRY topics from earlier cycles go back to PENDING first
        ▼
TopicValidator
        │   Google News RSS, NewsAPI, Google Custom Search (up to 35 articles)
        │   deduplication, relevance, LLM evidence validation
        ▼
   ┌────────────┬─────────────┬──────────────┐
   ▼            ▼             ▼
 VALID       INVALID        RETRY
   │            │             │
   ▼            ▼             ▼
VALIDATED   DISCARDED    next cycle
   │
   ▼
KnowledgeExpansionManager → KnowledgeCreationEngine → KnowledgeManager
   │     creates a new topic, or merges into a related existing one
   ▼
knowledge_base.json → COMPLETED
   │
   ▼
FAISS + BM25 rebuilt at the next server restart → future claims
```

- **Validation and creation are separate.** `TopicValidator` only decides whether external sources support the exact claim. Related articles aren't enough. For "SpaceX acquired Netflix in 2026", it found articles on SpaceX acquisitions but none about Netflix, so it returned INVALID.
- **RETRY is preferred over a false VALID.** When the search or the LLM call fails, the topic waits for the next cycle instead of being accepted.
- **Batches follow the free-tier token budget.** `ARTICLE_TOKEN_BUDGET` is 6500, there are 20-second pauses between batches, and the Groq limit is 8,000 tokens per minute. Some article text is truncated to fit, which is why 38.3% of evidence items are truncated.
- **New topics need a restart.** The running server doesn't rebuild its FAISS and BM25 indexes, so a new topic is searchable only after the next restart.

**Example from the project:** the claim "SpaceX reported a loss of $541 million" was validated with confidence 1.0 from 33 sources. It became the topic "SpaceX Q2 2026 Earnings Report", with 41 evidence items. The two Eiffel Tower topics were added the same way.

---

## Math verification

The math module uses **no language model**. It is separate from the factual pipeline and has its own mode in the interface.

1. **Question interpreter.** A structured regular-expression grammar rebuilds the expression from the **question**, never from the model's answer. It recognises:
   - explicit expressions: "What is 14 \* 2.5 + 8?"
   - equal sharing: "24 chocolates packed equally into 6 boxes" becomes 24 / 6
   - addition: "5 apples, add 3 more" becomes 5 + 3
2. **Rational arithmetic engine.** The expression is evaluated with `fractions.Fraction` and SymPy. Every value is an exact fraction, so 0.1 + 0.2 is exactly 3/10.
3. **Answer and step checker.** It extracts the final answer and checks every intermediate statement in the working. It catches "5 + 3 = 9" even when the final answer of 8 is correct.

| Verdict            | When                                                                                |
| ------------------ | ----------------------------------------------------------------------------------- |
| `VERIFIED`         | The final answer and every step match the computed result                           |
| `INCORRECT`        | A step is false, or the final answer differs from the computed result               |
| `UNABLE_TO_VERIFY` | The question is ambiguous, symbolic, missing a final answer, or outside the grammar |

The module never runs model-generated code and never trusts an equation stated in the model's answer. User pressure ("I'm sure it's 9, please confirm") doesn't change the result, because the module computes the answer itself. It is not a general algebra solver, and it abstains on purpose when it can't rebuild the question safely.

**Example request:**

```http
POST /verify/math
Content-Type: application/json

{
  "question": "Maya has 5 apples and buys 2 more. How many apples does she have?",
  "answer": "She has 8 apples."
}
```

The verdict is `INCORRECT`: the computed result is 7. The response includes `verdict`, `extracted_expression`, `computed_result`, `original_answer`, `explanation`, `is_conclusive` and `intermediate_errors`. The route rejects blank or oversized input and has a two-second timeout.

### GSM8K benchmark (opt-in, not yet run)

`scripts/benchmark_gsm8k.py` streams the GSM8K `train` or `test` split, asks the Groq model each question, and verifies its answer. It needs `GROQ_API_KEY` and the optional loader in `requirements-benchmark.txt`.

```powershell
pip install -r requirements-benchmark.txt
python scripts/benchmark_gsm8k.py --split test --limit 100 --model openai/gpt-oss-120b
```

`--limit 0` processes the whole split and makes a model call for every example. Results go to `gsm8k_results.csv` and `gsm8k_results.summary.json`. Use the test split only for evaluation, never for tuning. **GSM8K has not been run, so no score is claimed.** Coverage is expected to be limited, because the verifier abstains on multi-step problems it can't rebuild.

---

## Code verification

LLMs often suggest Python packages that don't exist. An attacker can register those names on PyPI, so anyone who installs one runs the attacker's code. The code module catches this **without ever running the submitted code**.

````text
LLM response containing ```python blocks
        │
        ▼
1. extract.py     find fenced code blocks, ast.parse()
        │         syntax errors are reported as a finding, not a crash
        ▼
2. imports.py     each top-level module, checked in order:
        │         stdlib → KNOWN_IMPORTS aliases (cv2 → opencv-python,
        │         PIL → pillow, sklearn → scikit-learn) → installed (find_spec)
        │         → PyPI JSON API
        ▼
3. background.py  release history from PyPI
        │         not on PyPI → CONTRADICTED
        │         name similarity ≥ 0.8 to a popular package (difflib)
        │         AND (age < 90 days OR ≤ 2 releases OR no files)
        │         → CONTRADICTED (likely typosquat)
        │         new or thin package with no similar name → INSUFFICIENT_INFORMATION
        ▼
4. functions.py   for SUPPORTED packages only: import the module and check
                  the attribute exists (random.randomint → CONTRADICTED)
````

If PyPI can't be reached, the verdict is `INSUFFICIENT_INFORMATION`. The module never guesses.

**Benchmark (12 cases):**

- 6 real snippets, all passed: `os.listdir`, `json.dumps`, `math.isqrt`, `datetime.now()` on the class, `itertools.chain.from_iterable`, and `os.path` imported as `osp`.
- 6 hallucinated snippets, all caught: `fastjson_turbo`, `reqeusts`, `random.randomint`, `statistics.average`, `now()` on the `datetime` module, and `itertools.flatten`.

**Known miss (fakefn-06):** `append_key` called on a dictionary variable isn't caught. Function checks work on module attributes, and without type inference the module can't know a local variable's type.

The module checks Python only.

---

## Contextual audit, memory analysis and mitigation

Factual verification checks claims against external evidence. The contextual module checks whether an answer fits **the conversation**: the supplied context, the question, the earlier turns and the instructions.

**Inputs** (all modes): `question`, `answer`, `conversation_history`, and optionally `context` and `instructions`.

### Four audit dimensions

| Dimension               | Question it answers                                                   | Result                                                                         |
| ----------------------- | --------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| Context faithfulness    | Are the answer's claims supported by the documents the user supplied? | `SUPPORTED`, `CONTRADICTED`, `PARTIALLY_SUPPORTED`, `INSUFFICIENT_INFORMATION` |
| Conversation alignment  | Does the answer address the question, or drift off topic?             | `ALIGNED`, `MISALIGNED`                                                        |
| Context memory          | Does it respect what the user said in earlier turns?                  | Conflicts found or not                                                         |
| Instruction consistency | Does it follow explicit instructions, prohibitions and format rules?  | `FOLLOWED`, `VIOLATED`                                                         |

### Context Memory Analysis

`ContextMemoryAnalyzer` extracts the user's explicit goals, preferences, constraints, decisions and corrections from the conversation history. It then checks whether the current answer conflicts with any of them. A typical catch is an answer that uses a date the user later corrected.

### Mitigation and re-audit

```text
Question + answer + history + context + instructions
        │
        ▼
Initial audit → failures found?
        │
   no ──┴── yes
   │         │
   ▼         ▼
Return    One LLM call writes a refined prompt (adds the violated
audit     constraints and correction instructions) and a suggested answer
             │
             ▼
          Re-audit of the suggested answer
             │
             ▼
          Remaining failures, if any
```

When no actionable failure is found, the audit is returned without mitigation.

**Example:**

|                  |                                                       |
| ---------------- | ----------------------------------------------------- |
| History          | The user said they are learning Python.               |
| Question         | "What programming language did I say I was learning?" |
| Answer           | "You said you were learning Java."                    |
| Finding          | Contradicts the conversation history (context memory) |
| Suggested answer | "You said you were learning Python."                  |

### Important

This module **uses an LLM as the judge**, so it shares the weaknesses of LLM-as-a-judge methods. It can miss failures or flag valid answers. A refined prompt can improve an answer but doesn't guarantee it is correct, and passing the re-audit doesn't make an answer factually true. Its accuracy has not been measured. The contextual tests check request handling and response structure with a mocked auditor.

---

## API reference

| Endpoint                   | Server        | Method | Request                              | Main response fields                                                                                                                                            |
| -------------------------- | ------------- | ------ | ------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `/verify`                  | 8000          | POST   | `{"text": str}`                      | `claims[]` with `verdict`, `confidence`, `llm_relation`, `explanation`, `deterministic_signals`, `supporting_evidence`, `contradicting_evidence`, and `summary` |
| `/verify/math`             | 8000          | POST   | `{"question": str, "answer": str}`   | `verdict`, `extracted_expression`, `computed_result`, `original_answer`, `explanation`, `is_conclusive`, `intermediate_errors`                                  |
| `/verify/context`          | 8000          | POST   | context request\*                    | `status`, `audit` (four dimensions and `limitations`)                                                                                                           |
| `/verify/context/memory`   | 8000          | POST   | context request\*                    | `memory_analysis` (`memory_items`, `answer_consistency`, `limitations`, `scope`)                                                                                |
| `/verify/context/full`     | 8000          | POST   | context request\*                    | `contextual_audit`, `memory_analysis`, `errors`, `scope`                                                                                                        |
| `/verify/context/mitigate` | 8000          | POST   | context request\*                    | `initial_audit`, `failures`, `refined_prompt`, `suggested_answer`, `changes`, `re_verification`, `remaining_failures`                                           |
| `/check-code`              | 8001          | POST   | `{"text": str}` (1 to 100,000 chars) | `findings[]` (`block`, `kind`, `item`, `verdict`, `reason`), `summary`, `blocks_found`                                                                          |
| `/health`                  | 8000 and 8001 | GET    | none                                 | `{"status": "ok"}`                                                                                                                                              |

\* Context request:

```json
{
  "question": "What programming language did I say I was learning?",
  "answer": "You said you were learning Java.",
  "conversation_history": "User previously stated that they were learning Python.",
  "context": "",
  "instructions": "Answer using the available conversation context."
}
```

If the pipeline fails, `/verify` returns HTTP 200 with `"claims": []` and an `error` field. Invalid requests get a 422. Interactive API docs are at `http://127.0.0.1:8000/docs`.

---

## Project structure

```text
TruthLensv2/
├── api.py                          main FastAPI server (port 8000), serves the frontend
├── claim_processing/
│   └── claim_processor.py          RichClaimExtractor (LLM), ClaimProcessor
├── retrieval/
│   └── hybrid_retrieval.py         HybridRetriever: FAISS + BM25, RRF, re-ranking, gate
├── verification/
│   └── verifier.py                 six signals, Jaccard agreement, fusion rules, confidence
├── expansion/
│   ├── expansion_queue.py          queue and status transitions
│   ├── topic_validator.py          external search + LLM validation
│   ├── knowledge_expansion_manager.py
│   └── expansion_scheduler.py      one cycle (--once) or every 6 hours
├── knowledge_base/
│   ├── knowledge_manager.py        JSON storage, schema checks, index creation
│   └── topic_schema.py
├── math_verifier/                  interpreter, engine, reasoning, answers (no LLM)
├── code_verifier/
│   ├── extract.py  imports.py  background.py  functions.py  checker.py
│   ├── server.py                   code server (port 8001)
│   └── tests/test_checker.py
├── contextual_audit/
│   ├── contextual_auditor.py       four-dimension audit, mitigation, re-audit
│   └── context_memory.py           ContextMemoryAnalyzer
├── services/
│   └── llm_service.py              Groq client, token budget, batching
├── frontend/                       index.html, script.js, style.css (5 modes)
├── scripts/benchmark_gsm8k.py      opt-in GSM8K benchmark
├── tests/                          pytest / unittest suites
├── data/expansion_queue.json
├── knowledge_base.json
└── .env                            API keys (never commit)
```

`contextual_audit/reliability_orchestrator.py` is in the repository but isn't used by the current endpoints. The repository has about 17,750 lines of Python.

---

## Setup and running

### Requirements

- Python 3.10 or later (64-bit). The project was developed on 3.13.9 and the saved test run used 3.10.11.
- Windows, Linux or macOS. No GPU is needed: the large model runs on Groq, and MiniLM, spaCy and FAISS run on the CPU.
- Internet access for Groq, the news APIs and PyPI.

### 1. Create the environment and install dependencies

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1          # Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

`requirements.txt` doesn't install the spaCy model. If you skip the last command, most tests fail with import errors: a test run on a second machine produced 61 errors for this reason alone.

### 2. Configure `.env`

Create `TruthLensv2/.env`:

```env
GROQ_API_KEY=your_groq_key                  # required
NEWS_API_KEY=your_news_api_key              # knowledge expansion
GOOGLE_SEARCH_API_KEY=your_google_key       # knowledge expansion
GOOGLE_SEARCH_CX=your_search_engine_id      # knowledge expansion
```

Never commit `.env`. Make sure `.gitignore` contains:

```gitignore
.env
venv/
__pycache__/
*.pyc
```

If a key has ever been committed, rotate it. Removing the file from git doesn't remove it from the history.

### 3. Start the servers

Terminal 1, the main server:

```powershell
cd TruthLensv2
python -m uvicorn api:app --reload --host 127.0.0.1 --port 8000
```

Terminal 2, the code verifier:

```powershell
cd TruthLensv2
python -m uvicorn code_verifier.server:app --port 8001
```

Then open **http://127.0.0.1:8000/** and pick a mode. If port 8001 is busy, run the code server on 8002; the frontend tries 8002 automatically.

### 4. Run knowledge expansion (optional)

From `TruthLensv2/`:

```powershell
python -m expansion.expansion_scheduler --once    # one cycle now (use this for demos)
python -m expansion.expansion_scheduler           # keep running, one cycle every 6 hours
```

Restart the main server afterwards so new topics are indexed.

The scheduler output shows:

| Line                                                         | Meaning                                                  |
| ------------------------------------------------------------ | -------------------------------------------------------- |
| `Pending topics before validation`                           | Topics waiting for validation                            |
| `Validated topics waiting for expansion`                     | Topics accepted but not yet added                        |
| `Retry topics`                                               | Topics that couldn't be decided last time                |
| `Documents built = 33`                                       | Validated articles turned into documents                 |
| `Merging with existing topic` / `Topic updated successfully` | Added to a related topic instead of creating a duplicate |

---

## Tests

```powershell
# code verifier
python -m pytest TruthLensv2/code_verifier/tests -v

# main suite (math, API, validation, contracts, edge cases)
$env:PYTHONPATH="TruthLensv2"
python -m pytest TruthLensv2/tests -k "not test_existing_demo_ui_is_still_served" -v
```

| File                                     | Tests                                |
| ---------------------------------------- | ------------------------------------ |
| `test_math_verifier.py`                  | 21                                   |
| `test_math_api.py`                       | 5                                    |
| `test_request_validation.py`             | 13                                   |
| `test_extreme_inputs.py`                 | 7                                    |
| `test_context_modules_contract.py`       | 8                                    |
| `test_factual_pipeline_contract.py`      | 3                                    |
| `test_gsm8k_benchmark.py`                | 2                                    |
| `test_live_functionality_optional.py`    | 3 (only with `TRUTHLENS_RUN_LIVE=1`) |
| `test_factual_edge_cases_10.py`          | 10 (F01–F10)                         |
| `test_contextual_edge_cases_10_fixed.py` | 10 (C01–C10)                         |
| `code_verifier/tests/test_checker.py`    | 16 (3 need pypi.org)                 |

Live tests call paid or rate-limited APIs. Turn them on only when you mean to:

```powershell
$env:TRUTHLENS_RUN_LIVE="1"
```

Saved reports are in `reports/` (`functional-tests.txt`, `functional-tests.xml`, `factual-edge-10.xml`, `contextual-edge-10.xml`).

---

## Demo inputs

Run every input once before a demo. LLM output varies, and the factual results depend on what is in the knowledge base.

**Factual**

| Input                                                                            | Expected                                                 |
| -------------------------------------------------------------------------------- | -------------------------------------------------------- |
| `The Eiffel Tower is located in Paris. It was built in 1889 by Gustave Eiffel.`  | Two claims, both `SUPPORTED`                             |
| `SpaceX reported a loss of $541 million in its Q2 2026 earnings.`                | `SUPPORTED` (topic added by knowledge expansion)         |
| `The Eiffel Tower was built in 1889 by Gustave Eiffel and is located in London.` | One claim supported, the London claim not                |
| `SpaceX acquired Netflix in 2026.`                                               | `INSUFFICIENT_INFORMATION`, added to the expansion queue |

**Math**

| Question                                                                | Answer                                         | Expected                 |
| ----------------------------------------------------------------------- | ---------------------------------------------- | ------------------------ |
| What is 14 \* 2.5 + 8?                                                  | 14 \* 2.5 = 35, 35 + 8 = 43. The answer is 43. | `VERIFIED`               |
| 24 chocolates are packed equally into 6 boxes. How many in each box?    | 24 / 6 = 5. Each box has 5.                    | `INCORRECT`              |
| Riya has 5 apples. She adds 3 more. How many does she have?             | 5 + 3 = 9, so she has 8 apples.                | `INCORRECT` (false step) |
| Some chocolates are shared among a few friends. How many does each get? | Each gets 4.                                   | `UNABLE_TO_VERIFY`       |

**Code**

````text
```python
import fastjson_turbo
import reqeusts
import random
import statistics

x = random.randomint(1, 10)
avg = statistics.average([1, 2, 3])
```
````

Expected: all four items are `CONTRADICTED`.

**Context Memory Analysis**

|          |                                                                                                                                                        |
| -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| History  | "My project demo is on 10 November." … "Correction: the demo has been moved to 14 November." … "I want to finish the report two days before the demo." |
| Question | By which date should I finish my report?                                                                                                               |
| Answer   | Since your demo is on 10 November, finish your report by 8 November.                                                                                   |
| Expected | Conflict with the user's correction (the right date is 12 November)                                                                                    |

---

## Design principles

1. **Retrieval is not verification.** A retrieved document is a candidate until the signals and rules have checked it.
2. **Semantic similarity is not truth.** A related document may not support the claim, so entities, keywords, years, coverage, reliability and agreement are checked too.
3. **Missing evidence is not false evidence.** `CONTRADICTED` means evidence exists and conflicts with the claim. `INSUFFICIENT_INFORMATION` means there isn't enough evidence to decide.
4. **The LLM labels; the rules decide.** In the factual pipeline the LLM labels one relation, on evidence JARS retrieved. In math and code it isn't used at all.
5. **Abstain rather than guess,** in every module.
6. **Never execute untrusted code.**
7. **Validation and knowledge creation are separate steps.** Expansion never adds information the validator hasn't accepted.

---

## Limitations

| Limitation                                                       | Effect                                                                           |
| ---------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| No labelled evaluation of the live factual or contextual modules | No accuracy figure can be given                                                  |
| Edge-case tests use mocked LLM responses                         | They test logic and structure, not LLM judgement                                 |
| Latency not measured                                             | Time targets in FR-18 and NFR-01 to NFR-04 aren't verified                       |
| Fusion thresholds (0.20, 0.50, 0.60) and RRF k not tuned         | Set by design judgement                                                          |
| Source reliability is 0.90 for every source                      | The signal doesn't yet separate sources                                          |
| 38.3% of evidence items truncated                                | Some claims abstain when the key sentence was cut                                |
| Small knowledge base (24 topics), mostly Indian news             | Many claims start as `INSUFFICIENT_INFORMATION`                                  |
| New topics need a server restart                                 | Expansion doesn't help until the indexes are rebuilt                             |
| Contextual audit depends on the LLM                              | It shares LLM-as-a-judge biases                                                  |
| Code checks are Python-only and have no type inference           | fakefn-06 is missed                                                              |
| Depends on Groq's free tier                                      | LLM-based modes stop if Groq is down or rate-limited; math and code keep working |
| No authentication or user rate limiting                          | Local prototype only                                                             |

---

## Future work

- Labelled evaluation: FEVER for factual, GSM8K for math, a larger code benchmark, human-labelled conversations
- Latency measurement for every endpoint
- Tune the thresholds and RRF k on validation data, and measure calibration
- Per-publisher source reliability
- Incremental index updates, so new topics are searchable without a restart
- Chunk full articles instead of truncating them
- Type inference in the code module, and npm support
- A browser extension that checks answers inside chat interfaces
- Hindi and Marathi support
- Authentication and rate limiting for deployment

---

## Guide for team members

**Before changing anything, find which layer it belongs to:** claim processing, retrieval, verification, expansion, knowledge creation, persistence, math, code, contextual, or API/frontend. Keep each module to one job. Don't put retrieval, verification, knowledge-creation and scheduling logic in the same file.

**Don't casually change** these. They are the core of the system, and the report and tests describe them:

- retrieval scoring, RRF and re-ranking weights
- verification signals, fusion rules and thresholds
- queue and scheduler status transitions
- the knowledge base schema

Put integration changes in the integration layer (`api.py`, the frontend) rather than rewriting core algorithms.

**Before you commit:**

1. Run both test suites (see [Tests](#tests)).
2. Make sure no `.env` file, API key, token or credential is staged.
3. If you changed a prompt, update Appendix E in the report.

**Quick concepts:**

| Term                | Meaning                                                                                    |
| ------------------- | ------------------------------------------------------------------------------------------ |
| Claim               | One checkable statement extracted from an LLM answer                                       |
| Retrieval           | Finding candidate evidence in the knowledge base                                           |
| Verification        | Deciding from signals and rules whether the evidence supports, contradicts or can't decide |
| Knowledge expansion | Validating and adding missing topics from external sources                                 |
| Abstention          | `INSUFFICIENT_INFORMATION` / `UNABLE_TO_VERIFY`: the system doesn't guess                  |

---

**JARS: extract, retrieve, verify, abstain, expand.**
