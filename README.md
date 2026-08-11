# TruthLens V2

## LLM Hallucination Detection and Mitigation System

TruthLens V2 is a **Responsible AI / Trustworthy AI** system designed to detect, verify, and mitigate factual hallucinations in Large Language Model (LLM) responses.

Instead of directly trusting an LLM-generated response, TruthLens breaks the response into individual claims, retrieves relevant evidence from a Knowledge Base using **FAISS + BM25 Hybrid Retrieval**, verifies the claim using deterministic evidence signals and LLM-based semantic analysis, and produces a confidence-aware verification result.

When the Knowledge Base does not contain sufficient evidence, TruthLens sends the missing claim into an **automated Knowledge Expansion Pipeline**. The system validates the topic using external sources and, when sufficiently supported, creates or updates knowledge in the Knowledge Base.

---

# 📌 Project Classification

### Primary Domain

**Responsible AI / Trustworthy AI**

### Specific Problem

**LLM Hallucination Detection and Mitigation**

### Supporting Areas

- Generative AI / LLMs
- Natural Language Processing
- Information Retrieval
- Semantic Search
- Knowledge Representation
- Evidence-based Verification
- Explainable AI
- Automated Knowledge Expansion

---

# 🎯 Problem Statement

Large Language Models can generate responses that are fluent and convincing but factually incorrect.

A traditional LLM application may simply return the generated answer to the user.

TruthLens introduces a verification layer between the generated answer and the user.

The system asks:

> **"Can this claim be supported by the evidence available to us?"**

If sufficient evidence exists, the claim is verified.

If evidence is insufficient, TruthLens does **not** force a decision. Instead, it can send the missing claim into the Knowledge Expansion Pipeline.

---

# 🚀 What TruthLens Does

TruthLens V2 performs the following major operations:

1. Receives an LLM response.
2. Extracts individual factual claims.
3. Processes each claim.
4. Searches the Knowledge Base using FAISS + BM25.
5. Generates candidate evidence.
6. Validates retrieved candidates.
7. Calculates retrieval-related signals.
8. Sends sufficient evidence to the Verifier.
9. Performs deterministic verification.
10. Uses an LLM for semantic evidence analysis.
11. Produces a final verification result.
12. Detects insufficient information.
13. Adds missing claims to the Expansion Queue.
14. Periodically validates missing topics using external sources.
15. Creates or updates the Knowledge Base.
16. Makes the updated knowledge available for future retrieval.

---

# 🔄 ACTUAL IMPLEMENTED PIPELINE

This is the current implemented pipeline.

The Knowledge Expansion system is a feedback loop connected to the normal verification pipeline.

```text
                         LLM RESPONSE
                              │
                              ▼
                    ┌───────────────────┐
                    │   CLAIM PROCESSOR │
                    │                   │
                    │ Claim Extraction  │
                    │ Claim Refinement  │
                    │ Claim Filtering   │
                    └─────────┬─────────┘
                              │
                        Individual Claim
                              │
                              ▼
                    ┌───────────────────┐
                    │  HYBRID RETRIEVER │
                    └─────────┬─────────┘
                              │
                   ┌──────────┴──────────┐
                   ▼                     ▼
               ┌────────┐            ┌────────┐
               │ FAISS  │            │  BM25  │
               │Semantic│            │Keyword │
               │Search  │            │Search  │
               └────┬───┘            └────┬───┘
                    │                     │
                    └──────────┬──────────┘
                               ▼
                    Candidate Generation
                               │
                               ▼
                    Candidate Validation
                               │
                               ▼
                     Retrieval Confidence
                               │
                    ┌──────────┴──────────┐
                    │                     │
                    ▼                     ▼
          Sufficient Evidence     Insufficient Evidence
                    │                     │
                    ▼                     ▼
                VERIFIER           EXPANSION QUEUE
                    │                     │
                    │                   PENDING
                    │                     │
                    │                     ▼
                    │             6-HOUR SCHEDULER
                    │                     │
                    │                     ▼
                    │             TOPIC VALIDATOR
                    │                     │
                    │              External Sources
                    │                     │
                    │                     ▼
                    │              LLM Validation
                    │                     │
                    │          ┌──────────┼──────────┐
                    │          ▼          ▼          ▼
                    │        VALID     INVALID      RETRY
                    │          │          │           │
                    │          ▼          ▼           │
                    │     VALIDATED   DISCARDED       │
                    │          │                     │
                    │          ▼                Next Cycle
                    │  KNOWLEDGE EXPANSION
                    │       MANAGER
                    │          │
                    │          ▼
                    │  KNOWLEDGE CREATION
                    │       ENGINE
                    │          │
                    │          ▼
                    │   KNOWLEDGE MANAGER
                    │          │
                    │          ▼
                    │ knowledge_base.json
                    │          │
                    │          ▼
                    │   Future Retrieval
                    │
                    ▼
             VERIFICATION FUSION
                    │
                    ▼
              FINAL VERDICT
                    │
          ┌─────────┼──────────────┐
          ▼         ▼              ▼
      SUPPORTED  CONTRADICTED  INSUFFICIENT
```

---

# 🧠 PIPELINE EXPLAINED STEP-BY-STEP

## Step 1 — LLM Response

TruthLens starts with an LLM-generated response.

Example:

```text
SpaceX reported a loss of $541 million.
```

The complete response can contain multiple claims.

TruthLens processes claims individually instead of treating the entire response as one fact.

---

## Step 2 — Claim Processing

The Claim Processing layer extracts and prepares individual claims.

```text
LLM Response
     ↓
Sentence Processing
     ↓
Claim Candidate Generation
     ↓
Claim Refinement
     ↓
Claim Filtering
     ↓
Individual Claim
```

The output is an individual claim ready for evidence retrieval.

---

## Step 3 — Hybrid Retrieval

Each claim is sent to the Hybrid Retriever.

TruthLens uses two retrieval approaches:

```text
                 CLAIM
                   │
          ┌────────┴────────┐
          ▼                 ▼
        FAISS             BM25
    Semantic Search    Keyword Search
          │                 │
          └────────┬────────┘
                   ▼
          Candidate Documents
```

### FAISS

FAISS is used for semantic/vector retrieval.

It helps find documents with similar meaning even when the wording is different.

Example:

```text
Claim:
SpaceX reported a loss of $541 million.

Evidence:
SpaceX's Q2 2026 financial results showed a
net loss of 541 million dollars.
```

The wording is different, but the semantic meaning is similar.

### BM25

BM25 is used for lexical/keyword retrieval.

It is useful for exact terms such as:

- Entity names
- Numbers
- Dates
- Important keywords

For example:

```text
SpaceX
541
million
loss
2026
```

BM25 can strongly match these terms.

### Why use FAISS + BM25?

FAISS and BM25 solve different retrieval problems.

```text
FAISS
   ↓
"What evidence has a similar meaning?"

BM25
   ↓
"What evidence contains important matching terms?"
```

For hallucination detection, both are useful.

Semantic similarity alone does not guarantee that exact factual details match.

Therefore:

```text
FAISS + BM25
       ↓
Hybrid Evidence Retrieval
```

---

## Step 4 — Candidate Generation

The Hybrid Retriever generates candidate documents from the Knowledge Base.

The candidates come from the combination of:

```text
FAISS results
+
BM25 results
```

The system then performs further validation instead of assuming that the retrieved documents are automatically correct evidence.

---

## Step 5 — Candidate Validation

Retrieved candidates are evaluated using several signals.

Current signals include:

```text
Entity Consistency
Keyword Consistency
Temporal Consistency
Evidence Coverage
Source Reliability
Evidence Agreement
Evidence Count
```

These signals help determine whether the retrieved evidence is strong enough for verification.

---

## Step 6 — Retrieval Confidence

The retrieval stage determines whether enough useful evidence has been found.

### Path A — Sufficient Evidence

```text
Claim
 ↓
FAISS + BM25
 ↓
Candidate Evidence
 ↓
Candidate Validation
 ↓
Sufficient Evidence
 ↓
Verifier
```

### Path B — Insufficient Evidence

```text
Claim
 ↓
FAISS + BM25
 ↓
Weak / Insufficient Evidence
 ↓
INSUFFICIENT_INFORMATION
 ↓
Knowledge Expansion Required
 ↓
Expansion Queue
```

---

## Step 7 — Verification

If sufficient evidence is available, the claim enters the Verifier.

The Verifier performs:

```text
Retrieved Evidence
       ↓
Evidence Collection
       ↓
Deterministic Verification Signals
       +
LLM Semantic Analysis
       ↓
Verification Fusion
       ↓
Final Verdict
```

Possible final outcomes:

```text
SUPPORTED
CONTRADICTED
INSUFFICIENT_INFORMATION
```

---

## Step 8 — Deterministic Verification Signals

The verifier calculates evidence-related signals such as:

| Signal | Purpose |
|---|---|
| Entity Consistency | Checks whether important entities match |
| Keyword Consistency | Measures lexical overlap |
| Temporal Consistency | Checks year/time alignment |
| Evidence Coverage | Measures how much of the claim is represented |
| Source Reliability | Uses stored source reliability |
| Evidence Agreement | Measures agreement between evidence |
| Evidence Count | Measures available evidence quantity |

These signals are used together with LLM semantic analysis.

---

## Step 9 — LLM Semantic Verification

The verifier also sends the claim and retrieved evidence to the configured LLM service.

The LLM analyzes the semantic relationship between:

```text
CLAIM
   +
EVIDENCE
```

The result contributes to the final verification decision.

Important:

> The LLM is not the only source of truth.

TruthLens combines:

```text
Retrieval Evidence
+
Deterministic Signals
+
LLM Semantic Analysis
```

---

## Step 10 — Final Verification

The verification layer produces a final result.

### SUPPORTED

Evidence supports the claim.

```text
Claim
 ↓
Relevant Evidence
 ↓
Verification
 ↓
SUPPORTED
```

### CONTRADICTED

Retrieved evidence conflicts with the claim.

```text
Claim
 ↓
Relevant Evidence
 ↓
Conflicting Evidence
 ↓
CONTRADICTED
```

### INSUFFICIENT_INFORMATION

The system cannot reliably verify the claim using the current Knowledge Base.

```text
Claim
 ↓
Insufficient Evidence
 ↓
INSUFFICIENT_INFORMATION
```

This state is important because TruthLens does not force a binary decision when evidence is missing.

---

# 🔄 KNOWLEDGE EXPANSION PIPELINE

When a claim reaches:

```text
INSUFFICIENT_INFORMATION
```

the system can start the Knowledge Expansion workflow.

---

## Step 11 — Expansion Queue

The missing claim is added to the Expansion Queue.

Example:

```text
Topic:
SpaceX acquired Netflix in 2026.

Status:
PENDING
```

The queue manages topics waiting for external validation.

Possible states:

```text
PENDING
VALIDATED
COMPLETED
RETRY
DISCARDED
```

---

## Step 12 — Six-Hour Expansion Scheduler

The scheduler is responsible for running the expansion workflow periodically.

### Test / One-Cycle Mode

```bash
python -m expansion.expansion_scheduler --once
```

This runs one expansion cycle immediately.

### Continuous Mode

```bash
python -m expansion.expansion_scheduler
```

This runs the scheduler continuously according to the configured expansion interval.

---

## Step 13 — Retry Preparation

Before validating pending topics, the scheduler checks topics that previously received:

```text
RETRY
```

A retry topic can be reactivated for another validation cycle.

```text
RETRY
  ↓
Next Scheduler Cycle
  ↓
PENDING
  ↓
Topic Validator
```

This prevents uncertain topics from being permanently discarded after one unsuccessful search.

---

## Step 14 — Topic Validation

The Topic Validator determines whether external evidence supports the exact topic.

The process is:

```text
Pending Topic
      ↓
External Search
      ↓
Multiple Sources
      ↓
Deduplication
      ↓
Source Relevance
      ↓
LLM Evidence Validation
```

The validator can return:

```text
VALID
INVALID
RETRY
```

---

## Step 15 — VALID

If external evidence sufficiently supports the exact topic:

```text
VALID
 ↓
VALIDATED
```

The topic can proceed to Knowledge Base expansion.

---

## Step 16 — INVALID

If the retrieved evidence does not support the exact topic:

```text
INVALID
 ↓
DISCARDED
```

The system does not add unsupported information to the Knowledge Base.

---

## Step 17 — RETRY

If the search or evidence is insufficient to make a reliable decision:

```text
RETRY
```

The topic waits for a future expansion cycle.

This is an important conservative design decision.

TruthLens prefers:

```text
RETRY
```

over:

```text
False VALIDATION
```

---

## Step 18 — Knowledge Expansion Manager

Once a topic is:

```text
VALIDATED
```

the Knowledge Expansion Manager processes it.

```text
VALIDATED Topic
       ↓
Validated Sources
       ↓
Source Documents
       ↓
Knowledge Creation Engine
```

The manager coordinates the expansion process.

---

## Step 19 — Knowledge Creation Engine

The Knowledge Creation Engine converts validated external information into structured knowledge.

There are two possible cases.

### New Topic

```text
Validated Topic
      ↓
No Existing Topic
      ↓
Create Knowledge
      ↓
Knowledge Base
```

### Existing Topic

```text
Validated Topic
      ↓
Related Topic Found
      ↓
Merge / Update
      ↓
Existing Knowledge Updated
```

This avoids unnecessary duplicate topics.

---

## Step 20 — Knowledge Base Update

The generated or updated knowledge is stored in:

```text
knowledge_base.json
```

The overall process is:

```text
Validated Evidence
       ↓
Knowledge Creation Engine
       ↓
Knowledge Manager
       ↓
knowledge_base.json
```

---

## Step 21 — Future Retrieval

The updated Knowledge Base becomes available to the retrieval system.

Conceptually:

```text
knowledge_base.json
       ↓
Knowledge Base
       ↓
Search Corpus
       ↓
FAISS + BM25
       ↓
Future Claims
```

Therefore the system forms a feedback loop:

```text
INSUFFICIENT_INFORMATION
          ↓
   Knowledge Expansion
          ↓
   External Validation
          ↓
   Knowledge Creation
          ↓
 Knowledge Base Update
          ↓
    Future Retrieval
```

---

# 🏗️ SYSTEM ARCHITECTURE

The project can be viewed as the following major layers:

```text
┌──────────────────────────────────────────┐
│               LLM INTERFACE              │
│          ChatGPT / Gemini / LLMs         │
└──────────────────────┬───────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────┐
│             BROWSER EXTENSION            │
│      Content Script / Background         │
└──────────────────────┬───────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────┐
│              FASTAPI SERVER              │
└──────────────────────┬───────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────┐
│          VERIFICATION BACKEND            │
│                                          │
│  Claim Processing                        │
│        ↓                                 │
│  Hybrid Retrieval                        │
│        ↓                                 │
│  Evidence Verification                   │
│        ↓                                 │
│  Confidence / Trust Analysis             │
│        ↓                                 │
│  Verification Report                     │
└──────────────────────┬───────────────────┘
                       │
                       ▼
              Knowledge Base
                       │
                ┌──────┴──────┐
                ▼             ▼
              FAISS          BM25
                │             │
                └──────┬──────┘
                       │
                       ▼
                Future Retrieval
                       ▲
                       │
             Knowledge Expansion
                       ▲
                       │
              Insufficient Evidence
```

---

# 📂 PROJECT STRUCTURE

The exact directory structure may evolve, but the important modules are organized around the following responsibilities:

```text
TruthLensV2/
│
├── verifier/
│   └── verifier.py
│
├── retrieval/
│   └── hybrid_retrieval.py
│
├── claim_processing/
│   └── claim_processor.py
│
├── expansion/
│   ├── expansion_queue.py
│   ├── topic_validator.py
│   ├── knowledge_expansion_manager.py
│   └── expansion_scheduler.py
│
├── knowledge/
│   ├── knowledge_creation_engine.py
│   └── knowledge_manager.py
│
├── services/
│   └── llm_service.py
│
├── knowledge_base.json
│
├── .env
│
└── README.md
```

---

# 🧩 IMPORTANT MODULE RESPONSIBILITIES

## `verifier.py`

### Role

Main verification entry point.

### Responsible for

- Receiving claims
- Calling retrieval
- Collecting evidence
- Running verification
- Combining verification signals
- Producing final verdict

### Run

```bash
python -m verifier.verifier
```

---

## `hybrid_retrieval.py`

### Role

Evidence retrieval from the Knowledge Base.

### Responsible for

- Loading Knowledge Base
- Preparing search corpus
- Creating embeddings
- Building FAISS index
- Building BM25 index
- Generating candidates
- Validating candidates
- Calculating retrieval confidence
- Triggering missing-topic handling when evidence is insufficient

### Important

Do **not** treat this file as the final truth decision layer.

Its primary responsibility is:

```text
Claim
 ↓
Retrieve Evidence
 ↓
Rank / Validate Evidence
 ↓
Return Retrieval Result
```

---

## `claim_processor.py`

### Role

Claim preprocessing.

Responsible for preparing claims before retrieval.

Conceptually:

```text
Raw Claim
 ↓
Normalization
 ↓
Entity / Keyword Processing
 ↓
Processed Claim
```

---

## `expansion_queue.py`

### Role

Stores topics that require Knowledge Base expansion.

Example:

```text
PENDING
```

The queue separates:

```text
Verification
```

from:

```text
Knowledge Expansion
```

---

## `topic_validator.py`

### Role

Determines whether a missing topic is supported by external evidence.

It does **not** directly update the Knowledge Base.

It produces:

```text
VALID
INVALID
RETRY
```

---

## `knowledge_expansion_manager.py`

### Role

Processes topics that have already been externally validated.

It coordinates:

```text
Validated Topic
 ↓
Source Documents
 ↓
Knowledge Creation Engine
 ↓
Knowledge Update
```

The manager should not replace the Topic Validator.

---

## `knowledge_creation_engine.py`

### Role

Creates or updates structured knowledge from validated information.

It can:

- Create new topics
- Merge information into existing topics
- Update existing knowledge
- Generate structured knowledge fields

---

## `knowledge_manager.py`

### Role

Manages persistence of Knowledge Base information.

Primary storage:

```text
knowledge_base.json
```

---

## `expansion_scheduler.py`

### Role

Main controller for automated Knowledge Base expansion.

It coordinates:

```text
Retry Topics
      ↓
Pending Topics
      ↓
Topic Validation
      ↓
Validated Topics
      ↓
Knowledge Expansion
```

### Run one cycle

```bash
python -m expansion.expansion_scheduler --once
```

### Run continuously

```bash
python -m expansion.expansion_scheduler
```

---

# ▶️ HOW TO RUN THE PROJECT

## 1. Activate Virtual Environment

Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

---

## 2. Configure `.env`

Required services depend on the current implementation.

Example:

```env
GEMINI_API_KEY=your_gemini_key
GROQ_API_KEY=your_groq_key
NEWS_API_KEY=your_news_api_key
GOOGLE_SEARCH_API_KEY=your_google_search_key
GOOGLE_SEARCH_CX=your_google_search_engine_id
```

### IMPORTANT

Never commit real API keys to GitHub.

Use:

```text
.env
```

and add it to:

```text
.gitignore
```

Example:

```gitignore
.env
venv/
__pycache__/
*.pyc
```

---

# 🧪 RUNNING THE NORMAL VERIFICATION PIPELINE

Run:

```powershell
python -m verifier.verifier
```

This is the **main pipeline demo**.

Use a claim such as:

```text
SpaceX reported a loss of $541 million.
```

Conceptually:

```text
LLM / User Claim
      ↓
Claim Processing
      ↓
FAISS + BM25
      ↓
Evidence Retrieval
      ↓
Verifier
      ↓
Final Result
```

---

# 🧪 TESTING INSUFFICIENT INFORMATION

Use:

```text
SpaceX acquired Netflix in 2026.
```

The purpose of this test is to demonstrate the Knowledge Expansion path.

Expected conceptual flow:

```text
Claim
 ↓
Hybrid Retrieval
 ↓
Insufficient Evidence
 ↓
INSUFFICIENT_INFORMATION
 ↓
Knowledge Expansion Required
 ↓
Expansion Queue
 ↓
PENDING
```

---

# 🧪 RUNNING KNOWLEDGE EXPANSION

For a single expansion cycle:

```powershell
python -m expansion.expansion_scheduler --once
```

This is recommended for development and demonstrations.

The output will show:

```text
Pending topics
Validated topics
Retry topics
Validation results
Expansion results
```

---

# ⏰ RUNNING THE CONTINUOUS SCHEDULER

For continuous operation:

```powershell
python -m expansion.expansion_scheduler
```

The scheduler performs expansion cycles according to the configured interval.

For demonstrations, prefer:

```powershell
python -m expansion.expansion_scheduler --once
```

because it executes immediately instead of waiting for the next scheduled cycle.

---

# 🎬 RECOMMENDED TEAM DEMONSTRATION

You do **not** need to execute every Python file individually.

Use the main entry points.

## Demo 1 — Normal Verification

```powershell
python -m verifier.verifier
```

Show:

```text
Claim
 ↓
Claim Processing
 ↓
FAISS + BM25
 ↓
Evidence
 ↓
Verifier
 ↓
SUPPORTED / CONTRADICTED
```

---

## Demo 2 — Missing Evidence

Use:

```text
SpaceX acquired Netflix in 2026.
```

Show:

```text
INSUFFICIENT_INFORMATION
        ↓
Knowledge Expansion Required
        ↓
PENDING
```

---

## Demo 3 — Knowledge Expansion

Run:

```powershell
python -m expansion.expansion_scheduler --once
```

Show:

```text
PENDING
 ↓
Topic Validator
 ↓
VALID / INVALID / RETRY
```

If valid:

```text
VALIDATED
 ↓
Knowledge Expansion Manager
 ↓
Knowledge Creation Engine
 ↓
Knowledge Base
```

---

# 📊 UNDERSTANDING THE SCHEDULER OUTPUT

You may see:

```text
Pending topics before validation : 1
Validated topics waiting for expansion : 0
Retry topics : 0
```

Meaning:

- **Pending** → topics waiting for validation
- **Validated** → topics waiting for Knowledge Base expansion
- **Retry** → topics that previously could not be reliably validated

---

## Validation Output

```text
VALID
```

Means:

> External evidence sufficiently supports the exact topic.

```text
INVALID
```

Means:

> External evidence does not sufficiently support the exact topic.

```text
RETRY
```

Means:

> The system could not make a reliable determination and will try again later.

---

## Expansion Output

You may see:

```text
Documents built = 33
```

This means validated external source information was converted into documents for the Knowledge Creation Engine.

You may also see:

```text
Merging with existing topic
Updating existing topic
Topic updated successfully
```

This means the system found a related existing Knowledge Base topic and updated it instead of blindly creating a duplicate.

---

# 🧪 RECOMMENDED DEMO CLAIMS

## 1. Supported Claim

```text
SpaceX reported a loss of $541 million.
```

Use this to demonstrate the normal successful verification path.

```text
Claim
 ↓
FAISS + BM25
 ↓
Relevant Evidence
 ↓
Verifier
 ↓
SUPPORTED
```

---

## 2. Contradicted Claim

A contradicted demo should be based on a fact that is explicitly present in the current Knowledge Base.

For example, if the Knowledge Base states that SpaceX reported a loss:

```text
SpaceX reported a $541 million profit in Q2 2026.
```

This demonstrates:

```text
Claim
 ↓
Relevant Evidence
 ↓
Conflicting Evidence
 ↓
CONTRADICTED
```

Do not use this test if the corresponding loss evidence is not currently present in the Knowledge Base.

---

## 3. Insufficient Information

```text
SpaceX acquired Netflix in 2026.
```

Use this to demonstrate:

```text
INSUFFICIENT_INFORMATION
 ↓
Knowledge Expansion Required
 ↓
Expansion Queue
```

---

# 🔐 IMPORTANT DESIGN PRINCIPLES

## 1. Retrieval is not Verification

Do not assume:

```text
FAISS found document
        ↓
Claim is TRUE
```

Instead:

```text
FAISS + BM25
        ↓
Candidate Evidence
        ↓
Candidate Validation
        ↓
Verifier
        ↓
Final Decision
```

---

## 2. Semantic Similarity is not Truth

A document can be semantically related to a claim without actually supporting it.

Therefore TruthLens also considers:

- Entities
- Keywords
- Time
- Evidence coverage
- Source reliability
- Evidence agreement
- LLM semantic relationship

---

## 3. Missing Evidence is not False Evidence

The system distinguishes between:

```text
CONTRADICTED
```

and:

```text
INSUFFICIENT_INFORMATION
```

These are fundamentally different.

### CONTRADICTED

Evidence exists and conflicts with the claim.

### INSUFFICIENT_INFORMATION

The system does not have enough reliable evidence to decide.

---

## 4. Topic Validation and Knowledge Creation are Different

This separation is important.

```text
Topic Validator
      ↓
"Is this topic sufficiently supported?"
```

Then:

```text
Knowledge Expansion Manager
      ↓
"How do we convert this validated information into KB knowledge?"
```

The Knowledge Creation Engine should not be used as a replacement for external validation.

---

# ⚠️ DEVELOPMENT GUIDELINES FOR TEAM MEMBERS

Before modifying a module, understand its responsibility.

### Do not casually change:

- Retrieval scoring
- FAISS logic
- BM25 logic
- Verification thresholds
- Knowledge creation structure
- Queue status transitions
- Scheduler state transitions

These are core components of the implemented pipeline.

If an improvement is required, first identify whether it belongs to:

```text
Claim Processing
Retrieval
Verification
Expansion
Knowledge Creation
Persistence
```

---

# 🔧 CORE VS INTEGRATION CODE

Some modules contain core algorithms while others connect components together.

For example:

```text
hybrid_retrieval.py
```

contains the retrieval logic.

When integrating new components, prefer changing the **integration layer** rather than rewriting the retrieval algorithm unless there is a specific reason.

The same principle applies to:

- Verifier
- Knowledge Creation Engine
- Topic Validator
- Expansion Manager

---

# 🧭 WHICH FILE SHOULD I RUN?

For normal project execution:

```text
┌──────────────────────────────────────────────┐
│ NORMAL VERIFICATION                          │
│                                              │
│ python -m verifier.verifier                  │
└──────────────────────────────────────────────┘
```

For Knowledge Base expansion:

```text
┌──────────────────────────────────────────────┐
│ ONE EXPANSION CYCLE                          │
│                                              │
│ python -m expansion.expansion_scheduler      │
│ --once                                       │
└──────────────────────────────────────────────┘
```

For continuous Knowledge Base expansion:

```text
┌──────────────────────────────────────────────┐
│ CONTINUOUS EXPANSION                         │
│                                              │
│ python -m expansion.expansion_scheduler      │
└──────────────────────────────────────────────┘
```

You generally should **not** run individual internal modules such as:

```text
expansion_queue.py
topic_validator.py
knowledge_expansion_manager.py
hybrid_retrieval.py
```

as the primary application workflow.

They are components coordinated by the main entry points.

---

# 🗂️ STATE FLOW

The Knowledge Expansion state machine can be understood as:

```text
                    ┌─────────────┐
                    │   PENDING   │
                    └──────┬──────┘
                           │
                    Topic Validation
                           │
             ┌─────────────┼─────────────┐
             ▼             ▼             ▼
           VALID         INVALID        RETRY
             │             │             │
             ▼             ▼             │
        VALIDATED       DISCARDED        │
             │                           │
             ▼                           │
      Knowledge Expansion                │
             │                           │
             ▼                           │
         COMPLETED                       │
                                         │
                              Next Scheduler Cycle
                                         │
                                         ▼
                                      PENDING
```

---

# 🔄 KNOWLEDGE BASE FEEDBACK LOOP

The most important architectural concept is:

```text
                  ┌───────────────────────┐
                  │      KNOWLEDGE BASE   │
                  └───────────┬───────────┘
                              │
                              ▼
                         FAISS + BM25
                              │
                              ▼
                          Retrieval
                              │
                              ▼
                           Verifier
                              │
                    ┌─────────┴─────────┐
                    │                   │
             Evidence Found      Evidence Missing
                    │                   │
                    ▼                   ▼
                 Verdict          Expansion Queue
                                        │
                                        ▼
                                External Validation
                                        │
                                        ▼
                                Knowledge Creation
                                        │
                                        ▼
                                 Updated KB
                                        │
                                        └─────────────►
```

This means the system can progressively expand its evidence coverage.

---

# 📈 CURRENT SYSTEM CAPABILITIES

The current implementation supports:

- Claim-level processing
- Knowledge Base retrieval
- FAISS semantic retrieval
- BM25 lexical retrieval
- Hybrid candidate retrieval
- Candidate validation
- Evidence consistency signals
- Source reliability
- LLM semantic verification
- Confidence-aware decisions
- `SUPPORTED`
- `CONTRADICTED`
- `INSUFFICIENT_INFORMATION`
- Knowledge Expansion Queue
- PENDING / VALIDATED / RETRY / COMPLETED / DISCARDED states
- External topic validation
- Knowledge Creation Engine
- Knowledge Base updates
- Six-hour automated expansion workflow

---

# 🚧 FUTURE IMPROVEMENTS

Possible future enhancements include:

- Automatic FAISS/BM25 index refresh immediately after every KB update
- Persistent vector database
- Improved source credibility scoring
- More external search providers
- Better evidence contradiction detection
- Advanced temporal reasoning
- Knowledge conflict resolution
- Improved claim-to-evidence entailment
- Real-time browser extension integration
- Better provenance tracking
- Advanced hallucination risk scoring

These are future improvements and should not be confused with the currently implemented pipeline.

---

# 🤝 TEAM CONTRIBUTION GUIDE

Before contributing:

## 1. Understand the pipeline

Read:

```text
README.md
```

Then understand:

```text
verifier.py
        ↓
hybrid_retrieval.py
        ↓
expansion_queue.py
        ↓
topic_validator.py
        ↓
knowledge_expansion_manager.py
        ↓
knowledge_creation_engine.py
        ↓
knowledge_manager.py
        ↓
expansion_scheduler.py
```

---

## 2. Test before modifying

Normal verification:

```bash
python -m verifier.verifier
```

Expansion:

```bash
python -m expansion.expansion_scheduler --once
```

---

## 3. Do not commit secrets

Never commit:

```text
.env
API keys
tokens
credentials
```

---

## 4. Keep responsibilities separated

Avoid putting:

```text
retrieval logic
verification logic
knowledge creation logic
scheduler logic
```

into the same module.

Each module should have one clear responsibility.

---

# 👥 TEAM COLLABORATION

TruthLens V2 is designed as a modular system so team members can work independently on different components.

Possible work areas:

```text
Claim Processing
       │
       ├── Claim extraction
       └── Claim refinement

Retrieval
       │
       ├── FAISS
       ├── BM25
       └── Hybrid ranking

Verification
       │
       ├── Evidence signals
       ├── LLM analysis
       └── Confidence calculation

Knowledge Expansion
       │
       ├── Queue
       ├── Topic validation
       ├── Scheduler
       └── Expansion manager

Knowledge System
       │
       ├── Knowledge creation
       ├── Knowledge merging
       └── Knowledge persistence

Application Layer
       │
       ├── FastAPI
       └── Browser Extension
```

---

# 🧠 QUICK UNDERSTANDING

If you are new to the project, remember these five concepts first:

### 1. Claim

A factual statement extracted from an LLM response.

### 2. Retrieval

Finding relevant evidence from the Knowledge Base.

### 3. Verification

Determining whether the evidence supports or contradicts the claim.

### 4. Knowledge Expansion

Finding external information when the Knowledge Base is insufficient.

### 5. Knowledge Base Feedback

Adding validated knowledge back into the system so future claims can use it.

---

# ⭐ ONE-LINE PROJECT DESCRIPTION

> **TruthLens V2 is a Responsible AI system that detects and verifies LLM hallucinations through claim-level analysis, FAISS + BM25 hybrid evidence retrieval, evidence-grounded verification, and automated Knowledge Base expansion.**

---

# 📌 FINAL PIPELINE

```text
LLM RESPONSE
     ↓
CLAIM EXTRACTION
     ↓
CLAIM PROCESSING
     ↓
FAISS + BM25 HYBRID RETRIEVAL
     ↓
CANDIDATE VALIDATION
     ↓
RETRIEVAL CONFIDENCE
     ↓
┌─────────────────────────────────┐
│                                 │
│ Evidence Available              │
│         ↓                       │
│      VERIFIER                   │
│         ↓                       │
│ LLM + Deterministic Signals     │
│         ↓                       │
│ Verification Fusion             │
│         ↓                       │
│ SUPPORTED / CONTRADICTED        │
│                                 │
└─────────────────────────────────┘
                │
                │ Insufficient Evidence
                ▼
        KNOWLEDGE EXPANSION QUEUE
                ↓
             PENDING
                ↓
        6-HOUR SCHEDULER
                ↓
         TOPIC VALIDATOR
                ↓
      External Evidence Search
                ↓
       LLM Evidence Validation
                ↓
       ┌────────┼────────┐
       ▼        ▼        ▼
     VALID   INVALID    RETRY
       │        │        │
       ▼        ▼        ▼
  VALIDATED  DISCARDED  Next Cycle
       │
       ▼
KNOWLEDGE EXPANSION MANAGER
       ↓
KNOWLEDGE CREATION ENGINE
       ↓
KNOWLEDGE MANAGER
       ↓
knowledge_base.json
       ↓
FAISS + BM25
       ↓
FUTURE RETRIEVAL
```

---

# 🏁 TruthLens V2

### Detect → Retrieve → Verify → Expand → Learn

**Responsible AI for more trustworthy LLM responses.**