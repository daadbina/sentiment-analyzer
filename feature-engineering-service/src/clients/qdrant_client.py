"""Qdrant client for feature engineering service."""

import os
from typing import List, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from ..utils import StructuredLogger
from ..exceptions import QdrantError

logger = StructuredLogger(__name__)


class QdrantVectorClient:
    """Client for Qdrant vector database."""

    def __init__(self):
        """Initialize Qdrant client."""
        self.host = os.getenv("QDRANT_HOST", "localhost")
        self.port = int(os.getenv("QDRANT_PORT", 6333))
        self.collection_name = os.getenv("QDRANT_COLLECTION", "embeddings")
        self.client = None

    def connect(self):
        """Connect to Qdrant."""
        try:
            self.client = QdrantClient(host=self.host, port=self.port)
            logger.info(
                "Qdrant connected",
                host=self.host,
                port=self.port,
                collection=self.collection_name,
            )
        except Exception as e:
            logger.error("Error connecting to Qdrant", error=str(e))
            raise QdrantError(f"Error connecting to Qdrant: {str(e)}")

    def get_articles_by_ids(self, article_ids: List[str]) -> List[Dict[str, Any]]:
        """Get articles by IDs from Qdrant.

        Args:
            article_ids: List of article IDs

        Returns:
            List of article dictionaries with metadata
        """
        if not self.client:
            raise QdrantError("Not connected to Qdrant")

        if not article_ids:
            return []

        try:
            articles = []

            # Query Qdrant for each article ID
            for article_id in article_ids:
                try:
                    # Search for points with matching article_id in payload
                    search_result = self.client.search(
                        collection_name=self.collection_name,
                        query_filter={
                            "must": [
                                {
                                    "key": "article_id",
                                    "match": {"value": article_id},
                                }
                            ]
                        },
                        limit=1,
                    )

                    if search_result:
                        point = search_result[0]
                        # Extract metadata from payload
                        article_data = {
                            "article_id": article_id,
                            "title": point.payload.get("title", ""),
                            "body": point.payload.get("body", ""),
                            "language": point.payload.get("language", ""),
                            "domain": point.payload.get("domain", ""),
                            "source": point.payload.get("source", ""),
                            "published_at": point.payload.get("published_at", ""),
                            "sentiment_score": float(
                                point.payload.get("sentiment_score", 0.0)
                            ),
                            "entities": point.payload.get("entities", []),
                        }
                        articles.append(article_data)
                except Exception as e:
                    logger.warning(
                        "Error retrieving article from Qdrant",
                        article_id=article_id,
                        error=str(e),
                    )
                    continue

            logger.debug(
                "Articles retrieved from Qdrant",
                requested=len(article_ids),
                fetched=len(articles),
            )
            return articles

        except Exception as e:
            logger.error(
                "Error retrieving articles from Qdrant",
                error=str(e),
                article_count=len(article_ids),
            )
            raise QdrantError(f"Error retrieving articles: {str(e)}")

    def close(self):
        """Close Qdrant connection."""
        if self.client:
            self.client.close()
            logger.info("Qdrant connection closed")

