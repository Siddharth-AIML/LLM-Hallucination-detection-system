"""
=========================================================
TruthLens V2

Document Processor

Purpose:
--------
Converts raw web search results into clean, standardized
documents that can be consumed by the Knowledge Creation
Engine.

Author:
Siddharth Metkari

=========================================================
"""

import re
from typing import List, Dict
from dataclasses import dataclass


# =========================================================
# Standard Document Schema
# =========================================================

@dataclass
class Document:

    title: str

    content: str

    publisher: str

    url: str

    published_date: str


# =========================================================
# Document Processor
# =========================================================

class DocumentProcessor:

    """
    Cleans and standardizes documents.
    """

    def __init__(self):

        pass


    # -----------------------------------------------------
    # Clean Text
    # -----------------------------------------------------

    def clean_text(
        self,
        text: str
    ) -> str:

        if not text:

            return ""

        text = text.replace("\n", " ")

        text = text.replace("\t", " ")

        text = re.sub(
            r"\s+",
            " ",
            text
        )

        text = re.sub(
            r"<.*?>",
            "",
            text
        )

        return text.strip()


    # -----------------------------------------------------
    # Normalize Single Document
    # -----------------------------------------------------

    def normalize_document(
        self,
        article: Dict
    ) -> Document:

        return Document(

            title=self.clean_text(

                article.get(
                    "title",
                    ""
                )

            ),

            content=self.clean_text(

                article.get(
                    "content",
                    article.get(
                        "snippet",
                        ""
                    )
                )

            ),

            publisher=self.clean_text(

                article.get(
                    "publisher",

                    article.get(
                        "source",
                        ""
                    )

                )

            ),

            url=article.get(
                "url",
                ""
            ),

            published_date=article.get(
                "published_date",

                article.get(
                    "date",
                    ""
                )

            )

        )


    # -----------------------------------------------------
    # Normalize All Documents
    # -----------------------------------------------------

    def normalize_documents(
        self,
        articles: List[Dict]
    ) -> List[Document]:

        documents = []

        for article in articles:

            documents.append(

                self.normalize_document(
                    article
                )

            )

        return documents


    # -----------------------------------------------------
    # Remove Duplicate Documents
    # -----------------------------------------------------

    def remove_duplicates(
        self,
        documents: List[Document]
    ) -> List[Document]:

        unique = {}

        for doc in documents:

            key = (

                doc.title.lower(),

                doc.url.lower()

            )

            if key not in unique:

                unique[key] = doc

        return list(

            unique.values()

        )


    # -----------------------------------------------------
    # Remove Empty Documents
    # -----------------------------------------------------

    def remove_empty_documents(
        self,
        documents: List[Document]
    ) -> List[Document]:

        filtered = []

        for doc in documents:

            if (

                len(doc.title) > 5

                and

                len(doc.content) > 30

            ):

                filtered.append(doc)

        return filtered


    # -----------------------------------------------------
    # Complete Processing Pipeline
    # -----------------------------------------------------

    def process(
        self,
        articles: List[Dict]
    ) -> List[Document]:

        documents = self.normalize_documents(
            articles
        )

        documents = self.remove_duplicates(
            documents
        )

        documents = self.remove_empty_documents(
            documents
        )

        return documents