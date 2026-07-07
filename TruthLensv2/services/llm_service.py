"""
=========================================================
TruthLens V2

LLM Service

Handles all communication with Gemini.

Author:
Siddharth Metkari
=========================================================
"""

import os
import json

from dotenv import load_dotenv
import google.generativeai as genai


# =========================================================
# Load Environment Variables
# =========================================================

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError(
        "GEMINI_API_KEY not found in .env file."
    )

genai.configure(api_key=API_KEY)


# =========================================================
# Gemini Model
# =========================================================

MODEL_NAME = "gemini-2.5-flash"

model = genai.GenerativeModel(
    MODEL_NAME
)


# =========================================================
# LLM Service
# =========================================================

class LLMService:

    def __init__(self):
        self.model = model

    # =====================================================
    # Generate Topic Metadata
    # =====================================================

    def generate_topic_metadata(self, documents):
        """
        Input:
            List[Document]

        Output:
            Dictionary
        """

        article_text = ""

        for i, doc in enumerate(documents):

            article_text += f"""

==========================
ARTICLE {i + 1}
==========================

Title:
{doc.title}

Publisher:
{doc.publisher}

Published Date:
{doc.published_date}

Content:
{doc.content}

"""

        prompt = f"""
You are an expert Knowledge Base Builder.

Your task is to read multiple trusted articles that describe
the SAME EVENT or TOPIC.

Create ONE unified topic.

Rules:

1. Use ONLY the information present in the articles.
2. Do NOT hallucinate.
3. Merge duplicate information.
4. Return ONLY valid JSON.
5. Do NOT write markdown.
6. Do NOT explain anything.

Return EXACTLY this schema.

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

        response = self.model.generate_content(prompt)

        text = response.text.strip()

        # Remove Markdown if Gemini returns it

        text = text.replace("```json", "")
        text = text.replace("```", "")
        text = text.strip()

        try:

            return json.loads(text)

        except json.JSONDecodeError:

            raise ValueError(
                f"Gemini returned invalid JSON:\n\n{text}"
            )

    # =====================================================
    # Explain Verification
    # =====================================================

    def explain_verification(
        self,
        claim,
        evidence,
        verdict
    ):

        prompt = f"""
Claim:
{claim}

Verdict:
{verdict}

Evidence:
{evidence}

Explain in simple language why the claim is
SUPPORTED,
CONTRADICTED,
or NEUTRAL.

Limit the explanation to 120 words.
"""

        response = self.model.generate_content(prompt)

        return response.text.strip()