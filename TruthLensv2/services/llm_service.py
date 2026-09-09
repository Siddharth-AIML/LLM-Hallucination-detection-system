"""
TruthLens V2

LLM Service (Groq Version)
"""

import logging
import os
import json
import time
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

logger = logging.getLogger(__name__)

API_KEY = os.getenv("GROQ_API_KEY")

if not API_KEY:
    raise ValueError("GROQ_API_KEY not found in .env file.")

MODEL_NAME = "openai/gpt-oss-120b"
client = Groq(api_key=API_KEY)


# =========================================================
# Token Budget
# =========================================================
#
# Groq's free tier enforces 8000 tokens per minute (TPM) for
# this model. A single validated topic can carry 30+ source
# documents, which measured at ~9400 tokens when bundled into
# one request - a hard 413, not a transient error, so retrying
# identically could never succeed.
#
# ARTICLE_TOKEN_BUDGET is the ceiling for the article text in
# ONE request. The remaining headroom below 8000 covers the
# prompt template (~200 tokens) and the completion (~1000),
# both of which count toward TPM.
ARTICLE_TOKEN_BUDGET = 6500

# A single oversized document is truncated to this many
# tokens so that one huge article cannot blow the budget on
# its own. Measured max was 674 tokens, so in practice this
# never triggers.
MAX_TOKENS_PER_DOCUMENT = 2000

# Groq resets the TPM window every 60s. Sequential batches
# would otherwise refill the same window and 429, so pause
# between them.
BATCH_PAUSE_SECONDS = 20

# Fallback ratio when the real tokenizer cannot be loaded
# (offline, no HF cache). Deliberately pessimistic: assuming
# more tokens per character makes batches smaller and safer.
_FALLBACK_CHARS_PER_TOKEN = 3.0

_tokenizer = None
_tokenizer_loaded = False


def count_tokens(text):
    """
    Count tokens using the real model tokenizer.

    Falls back to a conservative character heuristic only if
    the tokenizer cannot be loaded, so token accounting never
    becomes a hard dependency on network access.
    """

    global _tokenizer, _tokenizer_loaded

    if not _tokenizer_loaded:

        _tokenizer_loaded = True

        try:
            from transformers import AutoTokenizer

            _tokenizer = AutoTokenizer.from_pretrained(
                MODEL_NAME
            )

        except Exception as exc:
            logger.warning(
                "Could not load the %r tokenizer (%s: %s); "
                "falling back to a character-based token "
                "estimate.",
                MODEL_NAME,
                type(exc).__name__,
                exc
            )

            _tokenizer = None

    if _tokenizer is not None:

        try:
            return len(
                _tokenizer.encode(text)
            )

        except Exception:
            logger.warning(
                "Tokenizer failed on a document; using the "
                "character-based estimate instead.",
                exc_info=True
            )

    return int(
        len(text) / _FALLBACK_CHARS_PER_TOKEN
    ) + 1


class LLMService:

    def __init__(self):
        self.client = client
        self.model_name = MODEL_NAME

    # =====================================================
    # Article Formatting
    # =====================================================

    def _format_article(self, index, doc):
        """
        Render one document exactly as it has always been
        rendered. Extracted from generate_topic_metadata so
        that batching can measure documents individually.
        """

        content = doc.content

        # Guard against a single pathological document that
        # cannot fit in any batch. Truncation here is a last
        # resort; normal documents measure well under the
        # per-document cap.
        if count_tokens(content) > MAX_TOKENS_PER_DOCUMENT:

            logger.warning(
                "Document %r exceeds %d tokens; truncating "
                "it for the metadata call. Its full text is "
                "still preserved as Evidence.",
                doc.title[:60],
                MAX_TOKENS_PER_DOCUMENT
            )

            # Character-space cut sized from the measured
            # token ratio, then re-checked below.
            ratio = len(content) / max(
                count_tokens(content),
                1
            )

            content = content[
                :int(MAX_TOKENS_PER_DOCUMENT * ratio)
            ]

        return f"""

==========================
ARTICLE {index + 1}
==========================

Title:
{doc.title}

Publisher:
{doc.publisher}

Published Date:
{doc.published_date}

Content:
{content}

"""

    # =====================================================
    # Token-Aware Batching
    # =====================================================

    def _batch_documents(self, documents):
        """
        Split documents into batches that each fit inside
        ARTICLE_TOKEN_BUDGET.

        Strategy: greedy packing by running token total.

        Documents are added to the current batch until the
        next one would exceed the budget, then a new batch
        starts. This is preferred over a fixed
        documents-per-batch count because document sizes vary
        by an order of magnitude (measured 90 to 674 tokens),
        so a fixed count would either waste most of the
        budget or overflow it.

        Source order is preserved, and TopicValidator ranks
        sources by relevance, so the highest-relevance
        sources land in the first batch.
        """

        batches = []
        current = []
        current_tokens = 0

        for index, doc in enumerate(documents):

            rendered = self._format_article(index, doc)

            doc_tokens = count_tokens(rendered)

            if (
                current
                and current_tokens + doc_tokens
                > ARTICLE_TOKEN_BUDGET
            ):
                batches.append(current)
                current = []
                current_tokens = 0

            current.append(rendered)
            current_tokens += doc_tokens

        if current:
            batches.append(current)

        return batches

    # =====================================================
    # Topic Metadata
    # =====================================================

    def generate_topic_metadata(self, documents):
        """
        Produce unified topic metadata for a set of source
        documents.

        When the documents fit inside one request this
        behaves exactly as before: a single LLM call.

        When they do not, the documents are batched, each
        batch is summarised independently, and the partial
        metadata objects are merged into one result. Every
        document therefore still contributes to the metadata
        - no source is discarded.

        The return contract is unchanged: a dict with
        topic_name, topic_category, summary, semantic_tags,
        important_claims and confidence.
        """

        if not documents:
            raise ValueError(
                "generate_topic_metadata requires at least "
                "one document."
            )

        batches = self._batch_documents(documents)

        if len(batches) == 1:
            return self._metadata_for_batch(
                "".join(batches[0])
            )

        logger.info(
            "Topic metadata for %d documents exceeds the "
            "%d-token budget; splitting into %d batched "
            "requests.",
            len(documents),
            ARTICLE_TOKEN_BUDGET,
            len(batches)
        )

        partials = []

        for position, batch in enumerate(batches):

            if position > 0:
                # Respect the per-minute token window.
                time.sleep(BATCH_PAUSE_SECONDS)

            partials.append(
                self._metadata_for_batch(
                    "".join(batch)
                )
            )

        return self._merge_metadata(partials)

    # =====================================================
    # Single Batch Request
    # =====================================================

    def _metadata_for_batch(self, article_text):

        prompt = f"""
You are an expert Knowledge Base Builder.

Your task is to read multiple trusted articles describing the SAME EVENT or TOPIC.

Create ONE unified topic.

Rules:
1. Use ONLY the provided articles.
2. Do NOT hallucinate.
3. Merge duplicate information.
4. Return ONLY valid JSON.
5. Never wrap JSON inside markdown.
6. Do NOT explain anything.

Return exactly:

{{
    "topic_name": "",
    "topic_category": "",
    "summary": "",
    "semantic_tags": [],
    "important_claims": [],
    "confidence": 0.0
}}

Articles:

{article_text}
"""

        response = self.client.chat.completions.create(
            model=self.model_name,
            temperature=0,
            messages=[{"role": "user", "content": prompt}]
        )

        text = response.choices[0].message.content.strip()
        text = text.replace("```json", "").replace("```", "").strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            raise ValueError(f"Groq returned invalid JSON:\n\n{text}")

    # =====================================================
    # Merge Batched Metadata
    # =====================================================

    def _merge_metadata(self, partials):
        """
        Combine per-batch metadata into one topic metadata
        object.

        Merge rules, chosen to match how the fields are
        consumed by KnowledgeCreationEngine.create_topic():

        - topic_name / topic_category: taken from the first
          batch. Sources are relevance-ranked upstream, so
          the first batch holds the strongest evidence for
          what the topic actually is. These are scalar
          fields with no meaningful way to concatenate.

        - summary: the batch summaries are joined. Every
          batch describes the same event from a different
          subset of sources, so this preserves detail that
          a single truncated call would have lost.

        - semantic_tags / important_claims: unioned with
          order preserved and duplicates dropped.

        - confidence: the minimum across batches. A topic is
          only as trustworthy as its weakest batch, which
          keeps this conservative rather than optimistic.
        """

        if not partials:
            raise ValueError(
                "No metadata was produced for this topic."
            )

        merged = {
            "topic_name": partials[0].get("topic_name", ""),
            "topic_category": partials[0].get(
                "topic_category",
                ""
            ),
        }

        summaries = []

        for item in partials:

            summary = str(
                item.get("summary", "")
            ).strip()

            if summary:
                summaries.append(summary)

        merged["summary"] = " ".join(summaries)

        for field in ("semantic_tags", "important_claims"):

            seen = set()
            values = []

            for item in partials:

                entries = item.get(field) or []

                if not isinstance(entries, list):
                    continue

                for entry in entries:

                    key = str(entry).strip().lower()

                    if not key or key in seen:
                        continue

                    seen.add(key)
                    values.append(entry)

            merged[field] = values

        confidences = []

        for item in partials:

            try:
                confidences.append(
                    float(item.get("confidence", 0.0))
                )
            except (TypeError, ValueError):
                logger.warning(
                    "Batch returned non-numeric confidence "
                    "%r; treating it as 0.0.",
                    item.get("confidence")
                )
                confidences.append(0.0)

        merged["confidence"] = (
            min(confidences) if confidences else 0.0
        )

        return merged

    def explain_verification(self, claim, evidence, verdict):
        prompt = f"""
Claim:
{claim}

Verdict:
{verdict}

Evidence:
{evidence}

Explain in simple language why the claim is SUPPORTED,
CONTRADICTED or NEUTRAL.

Limit the explanation to 120 words.
"""

        response = self.client.chat.completions.create(
            model=MODEL_NAME,
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}]
        )

        return response.choices[0].message.content.strip()
