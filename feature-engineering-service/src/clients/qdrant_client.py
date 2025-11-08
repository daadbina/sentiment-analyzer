"""Qdrant client for feature engineering service."""

import os
from typing import List, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from ..utils import StructuredLogger
from ..exceptions import QdrantError
from ..config import QdrantConfig

logger = StructuredLogger(__name__)


class QdrantVectorClient:
    """Client for Qdrant vector database."""

    def __init__(self, config: QdrantConfig = None):
        """Initialize Qdrant client.

        Args:
            config: Qdrant configuration (uses default if not provided)
        """
        if config is None:
            config = QdrantConfig()
        self.host = config.host
        self.port = config.port
        self.collection_name = config.collection_name
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
            article_id_set = set(article_ids)

            # Scroll through all points and filter by article_id
            try:
                points, _ = self.client.scroll(
                    collection_name=self.collection_name,
                    limit=1000,
                )

                for point in points:
                    if point.payload.get("article_id") in article_id_set:
                        article_id = point.payload.get("article_id")
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
                    "Error scrolling Qdrant collection",
                    error=str(e),
                )
                # Fallback: try to get articles by ID using scroll with offset
                for article_id in article_ids:
                    try:
                        points, _ = self.client.scroll(
                            collection_name=self.collection_name,
                            limit=1000,
                        )
                        for point in points:
                            if point.payload.get("article_id") == article_id:
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
                                break
                    except Exception as inner_e:
                        logger.warning(
                            "Error retrieving article from Qdrant",
                            article_id=article_id,
                            error=str(inner_e),
                        )
                        continue

            logger.debug(
                "Articles retrieved from Qdrant",
                requested=len(article_ids),
                fetched=len(articles),
            )

            # Log sample article data for debugging
            if articles:
                sample_article = articles[0]
                sentiment_score = sample_article.get("sentiment_score")
                entities = sample_article.get("entities", [])
                logger.info(
                    f"Sample article from Qdrant: article_id={sample_article.get('article_id')}, "
                    f"sentiment_score={sentiment_score}, entity_count={len(entities)}, "
                    f"has_title={bool(sample_article.get('title'))}, has_body={bool(sample_article.get('body'))}, "
                    f"publisher_credibility={sample_article.get('publisher_credibility')}, "
                    f"source={sample_article.get('source')}, domain={sample_article.get('domain')}"
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

