# TruthLens V2 — System Context for R&D Discussion

> Paste this whole file into Claude Chat as context, then ask your research questions.
> It describes an LLM hallucination-detection system built as a final-year BE project.

---

## 1. What the system is

TruthLens V2 detects hallucinations in LLM-generated answers by decomposing them into
atomic factual claims and verifying each claim independently against a locally-built,
news-derived Knowledge Base.

**Core design commitment (the project's central thesis):**
An LLM is never allowed to decide truth. The LLM is used only for *linguistic* work —
claim decomposition and semantic relation labelling. The final verdict is produced by
deterministic, rule-based fusion over evidence signals. This is a deliberate stance
against "LLM-as-judge" fact-checking, motivated by the circularity of using a
hallucination-prone model to detect hallucinations.

**Scale:** ~17,000 lines of Python across 6 subsystems.
**Stack:** Python 3.13, spaCy (`en_core_web_sm`), KeyBERT, sentence-transformers
(`all-MiniLM-L6-v2`, 384-dim), FAISS, `rank_bm25` (BM25Okapi), Groq API
(`openai/gpt-oss-120b` for extraction, validation and verification),
NewsAPI + Google News/Web Search for KB construction.

---

## 2. Architecture — the four stages

```
LLM Answer
    ↓
[1] RICH CLAIM EXTRACTION      (claim_processing/claim_processor.py, 1364 L)
    ↓ independent atomic claims
[2] HYBRID RETRIEVAL           (retrieval/hybrid_retrieval.py, 1534 L)
    ↓ ranked evidence  ── on failure ──▶ [4] KNOWLEDGE EXPANSION
[3] VERIFICATION               (verification/verifier.py, 1390 L)
    ↓
Per-claim verdict + confidence + explanation
```

Orchestrated by `pipeline.py`. **Each claim is processed fully independently; no
aggregate document-level verdict is produced.** This is intentional but is itself a
research question (see §7).

### Stage 1 — Rich Claim Extraction
Two classes in one file:
- `ClaimProcessor` — deterministic. Normalize → spaCy NER → KeyBERT keywords →
  regex year extraction → MiniLM embedding. Emits `ProcessedClaim`. This is the
  retrieval representation and is treated as a frozen contract.
- `RichClaimExtractor` — LLM-driven, Claimify-inspired. A single large system prompt
  performs sentence segmentation, factual-claim detection, coreference resolution,
  decontextualization, and atomic decomposition in one call (temperature 0, JSON out).
  Emits `ExtractedClaim`. 17 explicit rules forbid adding knowledge, collapsing
  uncertainty ("reportedly", "approximately" must survive), or merging propositions.

### Stage 2 — Hybrid Retrieval
Two-stage retrieve-then-rerank:
- **Candidate generation:** FAISS dense search (top-30) ∪ BM25 lexical (top-30), fused by
  **Reciprocal Rank Fusion**, `score = 1/(60+rank_sem) + 1/(60+rank_kw)`. RRF is used
  because it needs no score normalization between incomparable scales.
- **Validation/rerank:** five deterministic signals combined by fixed weights —
  `0.35·semantic + 0.25·entity_overlap + 0.20·keyword_overlap + 0.10·year_match + 0.10·evidence_coverage`
  Gates: `MINIMUM_CONFIDENCE = 0.50`, `MINIMUM_EVIDENCE = 2`.
- On failure → returns `INSUFFICIENT_INFORMATION` and **queues the claim for expansion**
  rather than guessing. Abstention is a first-class outcome.

### Stage 3 — Verification (the core contribution)
Computes six deterministic signals: `entity_consistency`, `keyword_consistency`,
`temporal_consistency`, `evidence_coverage`, `source_reliability`, `evidence_agreement`
(pairwise Jaccard over evidence token sets).

Then one LLM call returns *only* a semantic relation —
`SUPPORT | CONTRADICT | NEUTRAL | MIXED` + confidence + supported/contradicted/unresolved
aspects. The prompt explicitly forbids deciding the verdict.

**Fusion is a hard-coded rule cascade, not a weighted score** (`fuse_verification`):
```
if evidence_count < 2                              → INSUFFICIENT_INFORMATION
if not (coverage ≥ 0.20 or entity ≥ 0.50)          → INSUFFICIENT_INFORMATION
if reliability < 0.50 and evidence_count < 3       → INSUFFICIENT_INFORMATION
if relation == CONTRADICT and llm_conf ≥ 0.60      → CONTRADICTED
if relation == MIXED      and llm_conf ≥ 0.60      → PARTIALLY_SUPPORTED
if relation == SUPPORT    and llm_conf ≥ 0.60      → SUPPORTED
otherwise                                          → INSUFFICIENT_INFORMATION
```
The deterministic signals act as **gates/veto** (they can block a verdict) while the LLM
relation acts as the **direction selector**. Confidence is computed separately and is
explicitly a *reporting* signal that does not affect the verdict:
`final = min(retrieval_conf, verifier_conf)`, halved for abstentions.

### Stage 4 — Knowledge Expansion (self-healing KB)
Failed claims enter a persistent queue (`data/expansion_queue.json`) with
PENDING/COMPLETED status and retry counts. `TopicValidator` (1730 L) searches Google News,
Google Web, Bing, and NewsAPI, ranks sources by relevance, and asks an LLM to validate
whether external evidence supports the topic. Validated topics go to
`KnowledgeCreationEngine` (1578 L) which merges articles into a unified `Topic` and
writes it back to the KB. The system grows its own knowledge from its own failures.

---

## 3. Data layer — current state

`data/knowledge_base.json` (513 KB), schema in `knowledge_base/topic_schema.py`:
`Topic{topic_id, topic_name, topic_category, summary, years, entities, keywords,
semantic_tags, evidence[], sources[], topic_embedding, source_reliability,
evidence_count, trusted_source_count, ..., status, version}`,
`Evidence{text, source, url, published_date, retrieval_score}`.

**Measured facts about the current KB (I verified these directly):**
- **22 topics, 193 evidence items total.** Range 3–41 evidence per topic.
- **91 of 193 evidence items (47%) are truncated**, ending in `… [+1656 chars]` —
  the NewsAPI free-tier content cap. Nearly half the evidence corpus is cut mid-sentence.
- **Source concentration:** The Times of India 100/193 (52%), Nature.com 30, Google News 16.
- **`source_reliability` is ~0.9 for all 22 topics** (values 0.8999–0.9000).
- Topic granularity is coarse and overlapping — e.g. both "ISRO and Space Exploration"
  and "Indian Space Research Organisation (ISRO) and Private Space", plus several
  near-duplicate "India ... Developments" topics.
- Domain is almost entirely **recent Indian news / business / space / science (2026)**.
- **No labeled evaluation set and no evaluation harness exist anywhere in the repo.**

---

## 4. Known issues I have already identified

These are confirmed by reading the code and data — you can treat them as given.

1. **`source_reliability` is a constant.** It is a gating threshold in `fuse_verification`
   (`reliability < 0.50` blocks a verdict), but every topic scores ~0.9, so the gate never
   fires and the signal carries zero discriminative information.
2. **47% truncated evidence.** Verification reasons over sentences cut mid-clause. A
   truncated article may contain the refuting detail in the cut portion — a systematic
   false-`SUPPORTED`/false-abstain risk.
3. **Recall ceiling from KB size.** With 22 topics, almost any claim outside recent Indian
   news abstains. Abstention is currently the dominant outcome, which makes the system
   look "safe" while actually being uninformative.
4. **`spacy.load("en_core_web_sm")` is called inside `_extract_claim_entities()`**
   (`claim_processing/claim_processor.py:933`), i.e. re-loading the model on every claim
   instead of reusing `self.nlp`. Pure per-claim latency waste.
5. **Threshold values are unjustified.** `0.35/0.25/0.20/0.10/0.10`, `0.50`, `0.60`, `0.20`,
   `MIN_EVIDENCE=2` are hand-set, never tuned or ablated against labeled data.
6. **`evidence_agreement` compares every evidence item only to `sets[0]`**, not all pairs —
   it is a star comparison against an arbitrary anchor, not true pairwise agreement.
7. **Lexical-overlap signals cannot see negation or paraphrase.** "X did not acquire Y"
   and "X acquired Y" have near-identical token/entity overlap, so all deterministic
   signals pass and the verdict rests entirely on the LLM relation.
8. **Single-LLM dependency.** Both extraction and relation labelling run on Groq; a
   parse failure or API error silently degrades to `NEUTRAL` → `INSUFFICIENT_INFORMATION`.
9. **No document-level aggregation.** Per-claim independence loses cross-claim
   consistency (two claims can be individually plausible but mutually contradictory).

---

## 5. What is genuinely novel here (worth defending / publishing)

- **Gate-vs-direction separation:** deterministic signals hold veto power, the LLM only
  picks direction among already-permitted outcomes. This is a cleaner constitutional
  split than typical LLM-as-judge or NLI-only pipelines.
- **Abstention as a first-class verdict**, with a distinct `INSUFFICIENT_INFORMATION`
  outcome and confidence explicitly capped below 0.49 for it.
- **Failure-driven self-expanding KB:** retrieval failure is not an error, it is the
  trigger for autonomous knowledge acquisition with a validation gate before write-back.
- **Explicit uncertainty preservation** in claim extraction (qualifiers like "reportedly"
  must survive decomposition) — a known weak point in Claimify-style decomposition.

---

## 6. Comparable literature to position against

FEVER / FEVEROUS (benchmark + shared task), Claimify (Microsoft, claim decomposition),
SAFE (Search-Augmented Factuality Evaluator, DeepMind), FActScore (atomic fact precision),
RARR (retrofit attribution), MiniCheck (cheap grounding classifiers), SelfCheckGPT
(sampling-consistency, no external KB), Lookback Lens / attention-based detectors,
Chainpoll, and RAG-triad evaluation frameworks (RAGAS, TruLens).

---

## 7. My R&D directions — I want research help here

### A. Evaluation (my biggest gap — nothing exists yet)
- How do I build a rigorous evaluation given no labeled data? What is the minimum viable
  labeled set size for a credible BE thesis result?
- Should I evaluate on FEVER/FEVEROUS (standard, comparable, but Wikipedia-domain and
  mismatched with my news KB) or build a bespoke news-domain set? What are the trade-offs?
- How do I evaluate a system whose dominant output is abstention? Standard accuracy
  rewards abstaining on everything. What metrics handle this — selective-prediction /
  risk-coverage curves, AURC, coverage-at-precision? How do I report them?
- How do I separate *retrieval* failure from *verification* failure in error analysis, so
  I know whether to fix the KB or the fusion rules?
- Is my confidence score calibrated? How would I measure calibration (ECE, reliability
  diagrams) and does an uncalibrated confidence undermine the thesis?

### B. The fusion rules — my central contribution
- Is the hard rule cascade defensible versus a learned fusion (logistic regression /
  small classifier over the same signals)? A learned model would need labels but might
  win; does learning weights compromise the "no LLM decides truth" thesis, or is a
  transparent linear model still deterministic and interpretable enough?
- How do I *justify* thresholds rather than hand-setting them? Grid search on a dev set?
  What ablation table would a reviewer expect to see?
- Should deterministic signals be able to *override* the LLM relation, not just veto it?
  E.g. strong temporal contradiction forcing `CONTRADICTED` regardless of relation.

### C. Beating lexical overlap
- Negation and paraphrase defeat my token-overlap signals. Should I add a real NLI model
  (DeBERTa-MNLI, MiniCheck) as an additional *deterministic* signal? It is a neural model
  but not generative — does that stay within my "no LLM decides truth" commitment?
- Numeric and temporal claims ("$541 million", "Q2 2026") need exact reasoning. Is a
  dedicated numeric/temporal consistency checker worth building as a separate signal?

### D. Knowledge base quality
- How do I derive a *real* source-reliability score instead of a constant? Media-bias/
  factuality databases, domain authority, cross-source corroboration count?
- The 47% truncation problem: full-article scraping (legal/ToS implications?) versus
  switching provider versus treating truncation as an explicit uncertainty signal that
  feeds the fusion gate. Which is most defensible academically?
- Topic granularity: my topics are coarse and overlapping. What is the right granularity
  for retrieval — entity-centric, event-centric, or claim-centric KB units?
- Source concentration (52% one publisher) is a systemic bias. How do I quantify and
  report this, and does corroboration-across-independent-sources fix or mask it?

### E. Architecture extensions
- Multi-hop claims needing two evidence pieces composed — my flat retrieval cannot do
  this. Is iterative/agentic retrieval worth adding, and what does it cost in determinism?
- Document-level aggregation: how should per-claim verdicts combine into an answer-level
  hallucination score while preserving per-claim interpretability?
- Cross-claim consistency checking as a new signal.

### F. Framing for the thesis
- What is the single strongest, most defensible novelty claim I can make?
- What would a reviewer attack first, and what experiment preempts that attack?
- What is the smallest set of experiments that makes this publishable as a workshop paper?

---

## 8. Constraints

- Final-year BE (undergraduate) project, solo developer, limited compute (laptop, no GPU
  cluster), free-tier APIs (NewsAPI content cap is the source of the truncation problem).
- Existing `ProcessedClaim` / `ClaimProcessor` API is treated as a frozen contract that
  downstream modules depend on.
- Groq free-tier rate limits constrain how many LLM calls per claim are affordable.
- Prefer changes that are explainable in a thesis defense over black-box gains.
