"""
TruthLens V2

Knowledge Base Topic Validator V3

Purpose:
    Validate whether a queued topic has real,
    externally verifiable information before allowing
    it to proceed to Knowledge Base expansion.

Search Strategy:

    1. Google News RSS
    2. Google Web Search
    3. Bing / Azure Grounding Search
    4. News API

Important:

    Search providers are evidence collectors.

    They do NOT decide whether a topic is valid.

    Groq LLM receives the collected evidence and
    determines whether the evidence supports the
    EXACT topic.

Possible statuses:

    VALID
    INVALID
    RETRY
"""

import os
import sys
import json
import re
import html
import urllib.parse
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET

from dotenv import load_dotenv

# ---------------------------------------------------------
# Project Root
# ---------------------------------------------------------

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(
        0,
        PROJECT_ROOT
    )

load_dotenv()

from services.llm_service import (
    LLMService,
    MODEL_NAME
)


class TopicValidator:

    # =====================================================
    # Configuration
    # =====================================================

    MAX_SEARCH_QUERIES = 4

    MAX_SOURCES_PER_PROVIDER = 10

    MAX_LLM_SOURCES = 12

    SEARCH_TIMEOUT = 10

    MIN_RELEVANT_SOURCES = 1

    MIN_LLM_CONFIDENCE = 0.60

    # -----------------------------------------------------
    # Optional Search APIs
    # -----------------------------------------------------

    GOOGLE_API_KEY = os.getenv(
        "GOOGLE_SEARCH_API_KEY"
    )

    GOOGLE_CX = os.getenv(
        "GOOGLE_SEARCH_CX"
    )

    NEWS_API_KEY = os.getenv(
        "NEWS_API_KEY"
    )

    # Azure/Bing configuration.
    #
    # We do NOT call the retired Bing Search API.
    #
    # These variables are reserved for a future
    # Azure Grounding with Bing Search integration.

    AZURE_ENDPOINT = os.getenv(
        "AZURE_ENDPOINT"
    )

    AZURE_API_KEY = os.getenv(
        "AZURE_API_KEY"
    )

    USER_AGENT = (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/151.0 Safari/537.36"
    )

    # =====================================================
    # Initialization
    # =====================================================

    def __init__(
        self,
        search_timeout=None,
        llm_service=None
    ):

        self.search_timeout = (
            search_timeout
            if search_timeout is not None
            else self.SEARCH_TIMEOUT
        )

        self.llm_service = (
            llm_service
            if llm_service is not None
            else LLMService()
        )

    # =====================================================
    # Text Normalization
    # =====================================================

    @staticmethod
    def _normalize_text(text):

        if not text:
            return ""

        text = html.unescape(
            str(text)
        )

        text = text.lower()

        text = re.sub(
            r"<[^>]+>",
            " ",
            text
        )

        text = re.sub(
            r"[^a-z0-9\s]",
            " ",
            text
        )

        text = re.sub(
            r"\s+",
            " ",
            text
        )

        return text.strip()

    # =====================================================
    # Build Search Queries
    # =====================================================

    def _build_search_queries(
        self,
        topic
    ):

        clean_topic = topic.strip()

        queries = [
            clean_topic,
            f'"{clean_topic}"',
            f"{clean_topic} news",
            f"{clean_topic} latest"
        ]

        unique_queries = []

        seen = set()

        for query in queries:

            normalized = (
                self._normalize_text(
                    query
                )
            )

            if normalized not in seen:

                seen.add(
                    normalized
                )

                unique_queries.append(
                    query
                )

        return unique_queries[
            :self.MAX_SEARCH_QUERIES
        ]

    # =====================================================
    # Google News RSS
    # =====================================================

    def _search_google_news(
        self,
        query
    ):

        encoded_query = (
            urllib.parse.quote_plus(
                query
            )
        )

        url = (
            "https://news.google.com/rss/search?"
            f"q={encoded_query}"
            "&hl=en-IN"
            "&gl=IN"
            "&ceid=IN:en"
        )

        request = urllib.request.Request(
            url,
            headers={
                "User-Agent":
                    self.USER_AGENT
            }
        )

        try:

            with urllib.request.urlopen(
                request,
                timeout=self.search_timeout
            ) as response:

                data = response.read()

        except Exception as error:

            return {
                "provider": "google_news",
                "status": "FAILED",
                "sources": [],
                "error": str(error)
            }

        try:

            root = ET.fromstring(
                data
            )

        except ET.ParseError as error:

            return {
                "provider": "google_news",
                "status": "FAILED",
                "sources": [],
                "error": str(error)
            }

        channel = root.find(
            "channel"
        )

        if channel is None:

            return {
                "provider": "google_news",
                "status": "SUCCESS",
                "sources": [],
                "error": None
            }

        sources = []

        for item in channel.findall(
            "item"
        ):

            title_element = (
                item.find("title")
            )

            link_element = (
                item.find("link")
            )

            description_element = (
                item.find("description")
            )

            pub_date_element = (
                item.find("pubDate")
            )

            title = (
                title_element.text
                if title_element is not None
                and title_element.text
                else ""
            )

            link = (
                link_element.text
                if link_element is not None
                and link_element.text
                else ""
            )

            description = (
                description_element.text
                if description_element is not None
                and description_element.text
                else ""
            )

            published_date = (
                pub_date_element.text
                if pub_date_element is not None
                and pub_date_element.text
                else ""
            )

            if not title:

                continue

            sources.append(
                {
                    "provider":
                        "Google News",
                    "title":
                        title.strip(),
                    "link":
                        link.strip(),
                    "description":
                        html.unescape(
                            description.strip()
                        ),
                    "published_date":
                        published_date.strip(),
                    "search_query":
                        query
                }
            )

            if len(sources) >= (
                self.MAX_SOURCES_PER_PROVIDER
            ):

                break

        return {
            "provider": "google_news",
            "status": "SUCCESS",
            "sources": sources,
            "error": None
        }

    # =====================================================
    # Google Web Search
    # =====================================================

    def _search_google_web(
        self,
        query
    ):

        if not (
            self.GOOGLE_API_KEY
            and self.GOOGLE_CX
        ):

            return {
                "provider": "google_web",
                "status": "SKIPPED",
                "sources": [],
                "error":
                    "Google Web Search API "
                    "credentials not configured."
            }

        params = urllib.parse.urlencode(
            {
                "key":
                    self.GOOGLE_API_KEY,
                "cx":
                    self.GOOGLE_CX,
                "q":
                    query,
                "num":
                    self.MAX_SOURCES_PER_PROVIDER
            }
        )

        url = (
            "https://www.googleapis.com/"
            "customsearch/v1?"
            + params
        )

        request = urllib.request.Request(
            url,
            headers={
                "User-Agent":
                    self.USER_AGENT
            }
        )

        try:

            with urllib.request.urlopen(
                request,
                timeout=self.search_timeout
            ) as response:

                data = json.loads(
                    response.read().decode(
                        "utf-8"
                    )
                )

        except Exception as error:

            return {
                "provider": "google_web",
                "status": "FAILED",
                "sources": [],
                "error": str(error)
            }

        sources = []

        for item in data.get(
            "items",
            []
        ):

            sources.append(
                {
                    "provider":
                        "Google Web",
                    "title":
                        item.get(
                            "title",
                            ""
                        ),
                    "link":
                        item.get(
                            "link",
                            ""
                        ),
                    "description":
                        item.get(
                            "snippet",
                            ""
                        ),
                    "published_date":
                        "",
                    "search_query":
                        query
                }
            )

        return {
            "provider": "google_web",
            "status": "SUCCESS",
            "sources": sources,
            "error": None
        }

    # =====================================================
    # Bing / Azure Search
    # =====================================================

    def _search_bing(
        self,
        query
    ):

        """
        Microsoft retired the standalone Bing Search APIs.

        Therefore this method intentionally does NOT call
        the old Bing endpoint.

        When Azure Grounding with Bing Search is added,
        this method becomes the integration point.

        For now it safely reports SKIPPED.
        """

        if not (
            self.AZURE_ENDPOINT
            and self.AZURE_API_KEY
        ):

            return {
                "provider": "bing",
                "status": "SKIPPED",
                "sources": [],
                "error":
                    "Azure Grounding with Bing Search "
                    "is not configured."
            }

        return {
            "provider": "bing",
            "status": "SKIPPED",
            "sources": [],
            "error":
                "Azure Bing grounding integration "
                "is reserved for the Azure search adapter."
        }

    # =====================================================
    # News API
    # =====================================================

    def _search_news_api(
        self,
        query
    ):

        if not self.NEWS_API_KEY:

            return {
                "provider": "news_api",
                "status": "SKIPPED",
                "sources": [],
                "error":
                    "NEWS_API_KEY not configured."
            }

        params = urllib.parse.urlencode(
            {
                "q":
                    query,
                "language":
                    "en",
                "sortBy":
                    "relevancy",
                "pageSize":
                    self.MAX_SOURCES_PER_PROVIDER
            }
        )

        url = (
            "https://newsapi.org/v2/"
            "everything?"
            + params
        )

        request = urllib.request.Request(
            url,
            headers={
                "User-Agent":
                    self.USER_AGENT,
                "X-Api-Key":
                    self.NEWS_API_KEY
            }
        )

        try:

            with urllib.request.urlopen(
                request,
                timeout=self.search_timeout
            ) as response:

                data = json.loads(
                    response.read().decode(
                        "utf-8"
                    )
                )

        except Exception as error:

            return {
                "provider": "news_api",
                "status": "FAILED",
                "sources": [],
                "error": str(error)
            }

        if data.get(
            "status"
        ) != "ok":

            return {
                "provider": "news_api",
                "status": "FAILED",
                "sources": [],
                "error":
                    data.get(
                        "message",
                        "News API error."
                    )
            }

        sources = []

        for article in data.get(
            "articles",
            []
        ):

            source_info = (
                article.get(
                    "source",
                    {}
                )
            )

            sources.append(
                {
                    "provider":
                        "News API",
                    "title":
                        article.get(
                            "title",
                            ""
                        ),
                    "link":
                        article.get(
                            "url",
                            ""
                        ),
                    "description":
                        article.get(
                            "description",
                            ""
                        )
                        or "",
                    "published_date":
                        article.get(
                            "publishedAt",
                            ""
                        ),
                    "publisher":
                        source_info.get(
                            "name",
                            ""
                        ),
                    "content":
                        article.get(
                            "content",
                            ""
                        )
                        or "",
                    "search_query":
                        query
                }
            )

        return {
            "provider": "news_api",
            "status": "SUCCESS",
            "sources": sources,
            "error": None
        }

    # =====================================================
    # Run All Search Providers
    # =====================================================

    def _search_external_sources(
        self,
        topic
    ):

        queries = (
            self._build_search_queries(
                topic
            )
        )

        all_sources = []

        provider_status = []

        total_successful_searches = 0

        total_failed_searches = 0

        for query in queries:

            # ---------------------------------------------
            # 1. Google News
            # ---------------------------------------------

            result = (
                self._search_google_news(
                    query
                )
            )

            provider_status.append(
                result
            )

            if result["status"] == "SUCCESS":

                total_successful_searches += 1

                all_sources.extend(
                    result["sources"]
                )

            elif result["status"] == "FAILED":

                total_failed_searches += 1

            # ---------------------------------------------
            # 2. Google Web
            # ---------------------------------------------

            result = (
                self._search_google_web(
                    query
                )
            )

            provider_status.append(
                result
            )

            if result["status"] == "SUCCESS":

                total_successful_searches += 1

                all_sources.extend(
                    result["sources"]
                )

            elif result["status"] == "FAILED":

                total_failed_searches += 1

            # ---------------------------------------------
            # 3. Bing / Azure
            # ---------------------------------------------

            result = (
                self._search_bing(
                    query
                )
            )

            provider_status.append(
                result
            )

            if result["status"] == "SUCCESS":

                total_successful_searches += 1

                all_sources.extend(
                    result["sources"]
                )

            elif result["status"] == "FAILED":

                total_failed_searches += 1

            # ---------------------------------------------
            # 4. News API
            # ---------------------------------------------

            result = (
                self._search_news_api(
                    query
                )
            )

            provider_status.append(
                result
            )

            if result["status"] == "SUCCESS":

                total_successful_searches += 1

                all_sources.extend(
                    result["sources"]
                )

            elif result["status"] == "FAILED":

                total_failed_searches += 1

        # =================================================
        # Deduplicate
        # =================================================

        unique_sources = []

        seen_links = set()

        seen_titles = set()

        for source in all_sources:

            link = (
                source.get(
                    "link",
                    ""
                )
                .strip()
                .lower()
            )

            title = (
                self._normalize_text(
                    source.get(
                        "title",
                        ""
                    )
                )
            )

            identifier = (
                link
                if link
                else title
            )

            if not identifier:

                continue

            if identifier in seen_links:

                continue

            if title and title in seen_titles:

                continue

            seen_links.add(
                identifier
            )

            if title:

                seen_titles.add(
                    title
                )

            unique_sources.append(
                source
            )

        # =================================================
        # Return Search State
        # =================================================

        if (
            not unique_sources
            and total_successful_searches == 0
        ):

            return {
                "status": "RETRY",
                "sources": [],
                "provider_status":
                    provider_status,
                "error":
                    "All configured search "
                    "providers failed or were unavailable."
            }

        return {
            "status": "FOUND",
            "sources":
                unique_sources,
            "provider_status":
                provider_status,
            "error": None
        }

    # =====================================================
    # Source Relevance
    # =====================================================

    def _calculate_source_relevance(
        self,
        topic,
        source
    ):

        topic_words = set(
            self._normalize_text(
                topic
            ).split()
        )

        source_text = (
            self._normalize_text(
                (
                    source.get(
                        "title",
                        ""
                    )
                    + " "
                    + source.get(
                        "description",
                        ""
                    )
                    + " "
                    + source.get(
                        "content",
                        ""
                    )
                )
            )
        )

        meaningful_words = [
            word
            for word in topic_words
            if len(word) >= 3
        ]

        if not meaningful_words:

            return 0.0

        matched = 0

        for word in meaningful_words:

            if word in source_text:

                matched += 1

        return (
            matched
            / len(meaningful_words)
        )

    # =====================================================
    # Rank Sources
    # =====================================================

    def _rank_sources(
        self,
        topic,
        sources
    ):

        ranked = []

        for source in sources:

            relevance = (
                self._calculate_source_relevance(
                    topic,
                    source
                )
            )

            source[
                "relevance_score"
            ] = round(
                relevance,
                4
            )

            if relevance > 0:

                ranked.append(
                    source
                )

        ranked.sort(
            key=lambda source:
                source.get(
                    "relevance_score",
                    0.0
                ),
            reverse=True
        )

        return ranked

    # =====================================================
    # Prepare Evidence For LLM
    # =====================================================

    def _prepare_llm_evidence(
        self,
        sources
    ):

        evidence_blocks = []

        selected_sources = sources[
            :self.MAX_LLM_SOURCES
        ]

        for index, source in enumerate(
            selected_sources,
            start=1
        ):

            block = (
                f"EVIDENCE {index}\n"
                f"Provider: "
                f"{source.get('provider', '')}\n"
                f"Publisher: "
                f"{source.get('publisher', '')}\n"
                f"Title: "
                f"{source.get('title', '')}\n"
                f"Published: "
                f"{source.get('published_date', '')}\n"
                f"Description: "
                f"{source.get('description', '')}\n"
                f"Content: "
                f"{source.get('content', '')}\n"
                f"URL: "
                f"{source.get('link', '')}\n"
            )

            evidence_blocks.append(
                block
            )

        return (
            "\n"
            + "\n".join(
                evidence_blocks
            )
        )

    # =====================================================
    # Groq LLM Validation
    # =====================================================

    def _llm_validate(
        self,
        topic,
        sources
    ):

        evidence = (
            self._prepare_llm_evidence(
                sources
            )
        )

        prompt = f"""
You are the evidence validation component
of TruthLens.

Your task is to determine whether the
retrieved external evidence actually
supports the EXACT topic.

TOPIC:

{topic}

RETRIEVED EVIDENCE:

{evidence}

Rules:

1. Use ONLY the supplied evidence.

2. Do NOT rely on your own world knowledge.

3. Matching keywords are NOT sufficient.

4. Matching entities are NOT sufficient.

5. Related articles are NOT sufficient.

6. The evidence must establish the actual
   event, action, relationship, number,
   date, or fact stated in the topic.

7. If multiple independent sources support
   the exact topic, this strengthens VALID.

8. If the evidence directly contradicts
   the topic, return INVALID with relation
   CONTRADICT.

9. If the evidence discusses related topics
   but does not establish the exact topic,
   return INVALID with relation NEUTRAL.

10. If there is not enough evidence to make
    a reliable determination, return RETRY.

11. Be conservative.

12. Do not invent missing facts.

Return ONLY valid JSON.

Format:

{{
    "status": "VALID",
    "relation": "SUPPORT",
    "confidence": 0.0,
    "reason": ""
}}

Allowed status:

VALID
INVALID
RETRY

Allowed relation:

SUPPORT
CONTRADICT
NEUTRAL

Confidence must be between 0.0 and 1.0.
"""

        try:

            response = (
                self.llm_service.client
                .chat.completions.create(
                    model=MODEL_NAME,
                    temperature=0,
                    messages=[
                        {
                            "role":
                                "user",
                            "content":
                                prompt
                        }
                    ]
                )
            )

        except Exception as error:

            return {
                "status": "RETRY",
                "relation": "NEUTRAL",
                "confidence": 0.0,
                "reason":
                    "LLM validation failed.",
                "error":
                    str(error)
            }

        text = (
            response
            .choices[0]
            .message
            .content
            .strip()
        )

        text = (
            text
            .replace(
                "```json",
                ""
            )
            .replace(
                "```",
                ""
            )
            .strip()
        )

        try:

            result = json.loads(
                text
            )

        except json.JSONDecodeError:

            return {
                "status": "RETRY",
                "relation": "NEUTRAL",
                "confidence": 0.0,
                "reason":
                    "LLM returned invalid JSON."
            }

        status = str(
            result.get(
                "status",
                "RETRY"
            )
        ).upper()

        relation = str(
            result.get(
                "relation",
                "NEUTRAL"
            )
        ).upper()

        try:

            confidence = float(
                result.get(
                    "confidence",
                    0.0
                )
            )

        except (
            TypeError,
            ValueError
        ):

            confidence = 0.0

        confidence = max(
            0.0,
            min(
                1.0,
                confidence
            )
        )

        reason = str(
            result.get(
                "reason",
                ""
            )
        )

        if status not in {
            "VALID",
            "INVALID",
            "RETRY"
        }:

            status = "RETRY"

        if relation not in {
            "SUPPORT",
            "CONTRADICT",
            "NEUTRAL"
        }:

            relation = "NEUTRAL"

        return {
            "status":
                status,
            "relation":
                relation,
            "confidence":
                confidence,
            "reason":
                reason
        }

    # =====================================================
    # Main Validation
    # =====================================================

    def validate_topic(
        self,
        topic
    ):

        # -------------------------------------------------
        # Input validation
        # -------------------------------------------------

        if not isinstance(
            topic,
            str
        ):

            return {
                "topic": topic,
                "status": "INVALID",
                "llm_relation":
                    "NEUTRAL",
                "confidence": 0.0,
                "source_count": 0,
                "sources": [],
                "reason":
                    "Topic must be a string."
            }

        topic = topic.strip()

        if not topic:

            return {
                "topic": topic,
                "status": "INVALID",
                "llm_relation":
                    "NEUTRAL",
                "confidence": 0.0,
                "source_count": 0,
                "sources": [],
                "reason":
                    "Topic is empty."
            }

        # -------------------------------------------------
        # Search all providers
        # -------------------------------------------------

        search_result = (
            self._search_external_sources(
                topic
            )
        )

        if (
            search_result["status"]
            == "RETRY"
        ):

            return {
                "topic": topic,
                "status": "RETRY",
                "llm_relation":
                    "NEUTRAL",
                "confidence": 0.0,
                "source_count": 0,
                "sources": [],
                "reason":
                    search_result.get(
                        "error",
                        "External search failed."
                    ),
                "provider_status":
                    search_result.get(
                        "provider_status",
                        []
                    )
            }

        all_sources = (
            search_result.get(
                "sources",
                []
            )
        )

        if not all_sources:

            return {
                "topic": topic,
                "status": "RETRY",
                "llm_relation":
                    "NEUTRAL",
                "confidence": 0.0,
                "source_count": 0,
                "sources": [],
                "reason":
                    "No external evidence was found."
            }

        # -------------------------------------------------
        # Rank
        # -------------------------------------------------

        ranked_sources = (
            self._rank_sources(
                topic,
                all_sources
            )
        )

        if not ranked_sources:

            return {
                "topic": topic,
                "status": "RETRY",
                "llm_relation":
                    "NEUTRAL",
                "confidence": 0.0,
                "source_count": 0,
                "sources": [],
                "reason":
                    "Search returned sources, "
                    "but no sufficiently relevant "
                    "evidence was identified."
            }

        # -------------------------------------------------
        # Groq validation
        # -------------------------------------------------

        llm_result = (
            self._llm_validate(
                topic,
                ranked_sources
            )
        )

        status = (
            llm_result.get(
                "status",
                "RETRY"
            )
        )

        relation = (
            llm_result.get(
                "relation",
                "NEUTRAL"
            )
        )

        confidence = (
            llm_result.get(
                "confidence",
                0.0
            )
        )

        reason = (
            llm_result.get(
                "reason",
                ""
            )
        )

        # -------------------------------------------------
        # Low confidence VALID
        # -------------------------------------------------

        if (
            status == "VALID"
            and confidence
            < self.MIN_LLM_CONFIDENCE
        ):

            status = "RETRY"

            reason = (
                "Evidence may support the topic, "
                "but LLM confidence is below the "
                "validation threshold."
            )

        # -------------------------------------------------
        # Final result
        # -------------------------------------------------

        return {
            "topic":
                topic,

            "status":
                status,

            "llm_relation":
                relation,

            "confidence":
                confidence,

            "source_count":
                len(ranked_sources),

            "sources":
                ranked_sources,

            "reason":
                reason,

            "provider_status":
                search_result.get(
                    "provider_status",
                    []
                )
        }

    # =====================================================
    # Pretty Print
    # =====================================================

    def print_result(
        self,
        result
    ):

        print()

        print("=" * 60)

        print(
            "Knowledge Base Topic Validation V3"
        )

        print("=" * 60)

        print(
            f"Topic       : "
            f"{result.get('topic', '')}"
        )

        print(
            f"Status      : "
            f"{result.get('status', '')}"
        )

        print(
            f"LLM Relation: "
            f"{result.get('llm_relation', 'NEUTRAL')}"
        )

        print(
            f"Confidence  : "
            f"{result.get('confidence', 0.0):.4f}"
        )

        print(
            f"Sources     : "
            f"{result.get('source_count', 0)}"
        )

        print()

        print(
            "Reason:"
        )

        print(
            result.get(
                "reason",
                ""
            )
        )

        # -------------------------------------------------
        # Provider Status
        # -------------------------------------------------

        provider_status = (
            result.get(
                "provider_status",
                []
            )
        )

        if provider_status:

            print()

            print(
                "Search Provider Status:"
            )

            displayed = set()

            for item in provider_status:

                provider = (
                    item.get(
                        "provider",
                        ""
                    )
                )

                if provider in displayed:

                    continue

                displayed.add(
                    provider
                )

                print(
                    f"- {provider}: "
                    f"{item.get('status', '')}"
                )

        # -------------------------------------------------
        # Sources
        # -------------------------------------------------

        sources = result.get(
            "sources",
            []
        )

        if sources:

            print()

            print(
                "Retrieved Sources:"
            )

            for index, source in enumerate(
                sources,
                start=1
            ):

                print()

                print(
                    f"[{index}] "
                    f"{source.get('title', '')}"
                )

                print(
                    f"Provider  : "
                    f"{source.get('provider', '')}"
                )

                print(
                    f"Relevance : "
                    f"{source.get('relevance_score', 0.0):.4f}"
                )

                if source.get(
                    "publisher"
                ):

                    print(
                        f"Publisher : "
                        f"{source.get('publisher')}"
                    )

                if source.get(
                    "published_date"
                ):

                    print(
                        f"Published : "
                        f"{source.get('published_date')}"
                    )

                if source.get(
                    "link"
                ):

                    print(
                        f"Link      : "
                        f"{source.get('link')}"
                    )

        print()

        print("=" * 60)


# =========================================================
# Standalone Test
# =========================================================

if __name__ == "__main__":

    print()

    print("=" * 60)

    print(
        "TruthLens Topic Validator V3 Test"
    )

    print("=" * 60)

    validator = TopicValidator()

    while True:

        topic = input(
            "\nEnter Topic "
            "(or 'exit'): "
        ).strip()

        if topic.lower() == "exit":

            break

        if not topic:

            continue

        result = (
            validator.validate_topic(
                topic
            )
        )

        validator.print_result(
            result
        )