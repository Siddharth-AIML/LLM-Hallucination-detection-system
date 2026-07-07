"""
=========================================================
TruthLens V2

Fetch News

Downloads news articles from NewsAPI
using predefined topics and trusted sources.

Pipeline

topics.json
        │
        ▼
NewsAPI
        │
        ▼
Normalize Articles
        │
        ▼
Remove Duplicates
        │
        ▼
news_dataset.json

Author:
Siddharth Metkari
=========================================================
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict

import requests

from dotenv import load_dotenv


# =========================================================
# Load Environment Variables
# =========================================================

load_dotenv()

NEWS_API_KEY = os.getenv(

    "NEWS_API_KEY"

)

if NEWS_API_KEY is None:

    raise ValueError(

        "NEWS_API_KEY not found inside .env"

    )


# =========================================================
# Project Paths
# =========================================================

PROJECT_ROOT = Path(

    __file__

).resolve().parent.parent


CONFIG_FOLDER = PROJECT_ROOT / "config"

DATA_FOLDER = PROJECT_ROOT / "data"


TOPICS_FILE = CONFIG_FOLDER / "topics.json"

TRUSTED_SOURCES_FILE = (

    CONFIG_FOLDER

    / "trusted_sources.json"

)

OUTPUT_FILE = (

    DATA_FOLDER

    / "news_dataset.json"

)


# =========================================================
# News API Configuration
# =========================================================

NEWS_API_URL = (

    "https://newsapi.org/v2/everything"

)

PAGE_SIZE = 20

LANGUAGE = "en"

SORT_BY = "publishedAt"

REQUEST_DELAY = 1


# =========================================================
# Fetch News
# =========================================================

class FetchNews:

    """
    Downloads news from NewsAPI and creates
    news_dataset.json
    """

    def __init__(self):

        self.api_key = NEWS_API_KEY

        self.topics = []

        self.trusted_sources = []

        self.dataset = []

        print(

            "Fetch News Initialized."

        )

        # =====================================================
    # Load Topics
    # =====================================================

    def load_topics(

        self

    ) -> List[str]:

        """
        Loads topics from config/topics.json
        """

        if not TOPICS_FILE.exists():

            raise FileNotFoundError(

                f"{TOPICS_FILE} not found."

            )

        with open(

            TOPICS_FILE,

            "r",

            encoding="utf-8"

        ) as file:

            topics = json.load(

                file

            )

        if not isinstance(

            topics,

            list

        ):

            raise ValueError(

                "topics.json must contain a list."

            )

        self.topics = [

            topic.strip()

            for topic in topics

            if topic.strip()

        ]

        print(

            f"Loaded {len(self.topics)} topics."

        )

        return self.topics


    # =====================================================
    # Load Trusted Sources
    # =====================================================

    def load_trusted_sources(

        self

    ) -> List[str]:

        """
        Loads trusted news publishers.
        """

        if not TRUSTED_SOURCES_FILE.exists():

            raise FileNotFoundError(

                f"{TRUSTED_SOURCES_FILE} not found."

            )

        with open(

            TRUSTED_SOURCES_FILE,

            "r",

            encoding="utf-8"

        ) as file:

            sources = json.load(

                file

            )

        if not isinstance(

            sources,

            list

        ):

            raise ValueError(

                "trusted_sources.json must contain a list."

            )

        self.trusted_sources = [

            source.strip()

            for source in sources

            if source.strip()

        ]

        print(

            f"Loaded {len(self.trusted_sources)} trusted sources."

        )

        return self.trusted_sources


    # =====================================================
    # Initialize Configuration
    # =====================================================

    def initialize(

        self

    ):

        """
        Loads project configuration before
        downloading news.
        """

        self.load_topics()

        self.load_trusted_sources()

        DATA_FOLDER.mkdir(

            parents=True,

            exist_ok=True

        )

        print(

            "\nConfiguration Loaded Successfully."

        )

        print(

            f"Topics           : {len(self.topics)}"

        )

        print(

            f"Trusted Sources  : {len(self.trusted_sources)}"

        )

        print(

            f"Output File      : {OUTPUT_FILE}"

        )
    
        # =====================================================
    # Create Request Parameters
    # =====================================================

    def create_request_params(

        self,

        topic: str,

        page: int = 1

    ) -> Dict:

        """
        Creates request parameters for NewsAPI.
        """

        return {

            "q": topic,

            "language": LANGUAGE,

            "sortBy": SORT_BY,

            "pageSize": PAGE_SIZE,

            "page": page,

            "apiKey": self.api_key

        }


    # =====================================================
    # Call NewsAPI
    # =====================================================

    def call_news_api(

        self,

        topic: str,

        page: int = 1

    ) -> Dict:

        """
        Calls NewsAPI and returns the JSON response.
        """

        params = self.create_request_params(

            topic,

            page

        )

        try:

            response = requests.get(

                NEWS_API_URL,

                params=params,

                timeout=30

            )

            response.raise_for_status()

            data = response.json()

            if data.get("status") != "ok":

                raise RuntimeError(

                    f"NewsAPI Error : "

                    f"{data.get('message')}"

                )

            return data

        except requests.exceptions.Timeout:

            print(

                f"Request timed out for topic: {topic}"

            )

        except requests.exceptions.ConnectionError:

            print(

                f"Connection failed for topic: {topic}"

            )

        except requests.exceptions.HTTPError as e:

            print(

                f"HTTP Error : {e}"

            )

        except Exception as e:

            print(

                f"Unexpected Error : {e}"

            )

        return {

            "status": "error",

            "articles": []

        }


    # =====================================================
    # Fetch Articles For One Topic
    # =====================================================

    def fetch_topic_articles(

        self,

        topic: str

    ) -> List[Dict]:

        """
        Downloads all articles for a topic.
        """

        print(

            f"\nFetching Topic : {topic}"

        )

        data = self.call_news_api(

            topic

        )

        articles = data.get(

            "articles",

            []

        )

        print(

            f"Downloaded {len(articles)} articles."

        )

        time.sleep(

            REQUEST_DELAY

        )

        return articles
    
        # =====================================================
    # Normalize One Article
    # =====================================================

    def normalize_article(

        self,

        topic: str,

        article: Dict

    ) -> Dict | None:

        """
        Converts a NewsAPI article into the
        TruthLens dataset format.
        """

        source = article.get(

            "source",

            {}

        )

        publisher = source.get(

            "name",

            ""

        )

        # ---------------------------------------------
        # Ignore articles without publisher
        # ---------------------------------------------

        if not publisher:

            return None

        # ---------------------------------------------
        # Keep only trusted publishers
        # ---------------------------------------------

        publisher_lower = publisher.lower()

        trusted = False

        for src in self.trusted_sources:

            if src.lower() in publisher_lower:

                trusted = True

                break

        if not trusted:

            return None

        # ---------------------------------------------
        # Ignore empty content
        # ---------------------------------------------

        content = article.get(

            "content"

        )

        description = article.get(

            "description"

        )

        if not content:

            content = description

        if not content:

            return None

        # ---------------------------------------------
        # Build normalized article
        # ---------------------------------------------

        normalized = {

            "topic": topic,

            "title": article.get(

                "title",

                ""

            ),

            "publisher": publisher,

            "author": article.get(

                "author"

            ),

            "url": article.get(

                "url"

            ),

            "published_date": article.get(

                "publishedAt"

            ),

            "description": description,

            "content": content,

            "language": LANGUAGE,

            "retrieved_at": datetime.now().isoformat()

        }

        return normalized


    # =====================================================
    # Normalize Articles
    # =====================================================

    def normalize_articles(

        self,

        topic: str,

        articles: List[Dict]

    ) -> List[Dict]:

        """
        Normalize all articles for one topic.
        """

        normalized_articles = []

        for article in articles:

            normalized = self.normalize_article(

                topic,

                article

            )

            if normalized is not None:

                normalized_articles.append(

                    normalized

                )

        print(

            f"Accepted {len(normalized_articles)} trusted articles."

        )

        return normalized_articles
    
        # =====================================================
    # Remove Duplicate Articles
    # =====================================================

    def remove_duplicates(

        self,

        articles: List[Dict]

    ) -> List[Dict]:

        """
        Removes duplicate articles based on URL.

        If URL is unavailable, Title is used.
        """

        unique_articles = []

        seen = set()

        for article in articles:

            key = article.get(

                "url"

            )

            if not key:

                key = article.get(

                    "title",

                    ""

                ).strip().lower()

            if key in seen:

                continue

            seen.add(

                key

            )

            unique_articles.append(

                article

            )

        print(

            f"Removed {len(articles) - len(unique_articles)} duplicate articles."

        )

        print(

            f"Remaining {len(unique_articles)} unique articles."

        )

        return unique_articles


    # =====================================================
    # Collect Dataset
    # =====================================================

    def build_dataset(

        self

    ) -> List[Dict]:

        """
        Downloads and normalizes articles
        for all configured topics.
        """

        dataset = []

        for topic in self.topics:

            raw_articles = self.fetch_topic_articles(

                topic

            )

            normalized = self.normalize_articles(

                topic,

                raw_articles

            )

            dataset.extend(

                normalized

            )

        dataset = self.remove_duplicates(

            dataset

        )

        self.dataset = dataset

        return dataset
    
        # =====================================================
    # Save Dataset
    # =====================================================

    def save_dataset(

        self

    ):

        """
        Saves the collected dataset into
        data/news_dataset.json
        """

        DATA_FOLDER.mkdir(

            parents=True,

            exist_ok=True

        )

        with open(

            OUTPUT_FILE,

            "w",

            encoding="utf-8"

        ) as file:

            json.dump(

                self.dataset,

                file,

                indent=4,

                ensure_ascii=False

            )

        print(

            f"\nDataset saved successfully."

        )

        print(

            f"Location : {OUTPUT_FILE}"

        )

        print(

            f"Articles : {len(self.dataset)}"

        )


    # =====================================================
    # Dataset Statistics
    # =====================================================

    def dataset_statistics(

        self

    ):

        """
        Displays statistics about the dataset.
        """

        topic_count = {}

        publisher_count = {}

        for article in self.dataset:

            topic = article["topic"]

            publisher = article["publisher"]

            topic_count[topic] = (

                topic_count.get(

                    topic,

                    0

                ) + 1

            )

            publisher_count[publisher] = (

                publisher_count.get(

                    publisher,

                    0

                ) + 1

            )

        print(

            "\n=============================="

        )

        print(

            "Dataset Statistics"

        )

        print(

            "=============================="

        )

        print(

            f"Total Articles : {len(self.dataset)}"

        )

        print(

            f"Topics         : {len(topic_count)}"

        )

        print(

            f"Publishers     : {len(publisher_count)}"

        )

        print(

            "\nArticles per Topic"

        )

        for topic, count in topic_count.items():

            print(

                f"• {topic} : {count}"

            )

        print(

            "\nArticles per Publisher"

        )

        for publisher, count in sorted(

            publisher_count.items(),

            key=lambda x: x[1],

            reverse=True

        ):

            print(

                f"• {publisher} : {count}"

            )

        print(

            "\n=============================="

        )

        # =====================================================
    # Fetch Complete Dataset
    # =====================================================

    def fetch_dataset(

        self

    ):

        """
        Complete news fetching pipeline.

        Steps

        1. Load configuration

        2. Download articles

        3. Normalize articles

        4. Remove duplicates

        5. Save dataset

        6. Print statistics
        """

        print(

            "\n========================================"

        )

        print(

            "TruthLens V2 News Collection Started"

        )

        print(

            "========================================"

        )

        # ---------------------------------------------
        # Initialize
        # ---------------------------------------------

        self.initialize()

        # ---------------------------------------------
        # Build Dataset
        # ---------------------------------------------

        self.build_dataset()

        # ---------------------------------------------
        # Save Dataset
        # ---------------------------------------------

        self.save_dataset()

        # ---------------------------------------------
        # Statistics
        # ---------------------------------------------

        self.dataset_statistics()

        print(

            "\n========================================"

        )

        print(

            "News Collection Completed Successfully"

        )

        print(

            "========================================\n"

        )

        return self.dataset


    # =====================================================
    # Get Dataset
    # =====================================================

    def get_dataset(

        self

    ) -> List[Dict]:

        """
        Returns the collected dataset.
        """

        return self.dataset


    # =====================================================
    # Total Articles
    # =====================================================

    def total_articles(

        self

    ) -> int:

        """
        Returns total collected articles.
        """

        return len(

            self.dataset

        )
    
    # =====================================================
# Main
# =====================================================

if __name__ == "__main__":

    try:

        fetcher = FetchNews()

        dataset = fetcher.fetch_dataset()

        print(

            f"\nSuccessfully downloaded "

            f"{len(dataset)} articles."

        )

    except KeyboardInterrupt:

        print(

            "\nNews collection interrupted by user."

        )

    except Exception as e:

        print(

            "\nFatal Error"

        )

        print(

            e

        )