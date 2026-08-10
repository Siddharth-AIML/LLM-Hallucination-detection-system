"""
TruthLens V2

LLM Service (Groq Version)
"""

import os
import json
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

API_KEY = os.getenv("GROQ_API_KEY")

if not API_KEY:
    raise ValueError("GROQ_API_KEY not found in .env file.")

MODEL_NAME = "llama-3.3-70b-versatile"
client = Groq(api_key=API_KEY)


class LLMService:

    def __init__(self):
        self.client = client
        self.model_name = MODEL_NAME

    def generate_topic_metadata(self, documents):
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
