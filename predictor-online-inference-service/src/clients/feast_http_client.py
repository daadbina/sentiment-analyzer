"""
Feast HTTP client for communicating with remote Feast feature server.

This client provides HTTP-based access to Feast feature store deployed on a remote server.
It supports online feature retrieval, feature pushing, and health checks.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
import aiohttp
from datetime import datetime

logger = logging.getLogger(__name__)

# All 28 features in semantic_group_features view
ALL_SEMANTIC_GROUP_FEATURES = [
    # Source features (4)
    "num_sources",
    "source_credibility_avg",
    "source_credibility_std",
    "source_diversity_score",
    # Temporal features (4)
    "time_span_hours",
    "publication_velocity",
    "temporal_concentration",
    "days_since_first_article",
    # Sentiment features (4)
    "sentiment_mean",
    "sentiment_std",
    "sentiment_polarity_ratio",
    "sentiment_volatility",
    # Entity features (4)
    "entity_count",
    "entity_diversity",
    "entity_prominence",
    "entity_concentration",
    # Content features (4)
    "avg_word_count",
    "avg_title_length",
    "language_diversity",
    "domain_diversity",
    # Embedding features (4)
    "centroid_magnitude",
    "intra_cluster_similarity_mean",
    "intra_cluster_similarity_std",
    "embedding_drift_score",
    # BTC price features (4)
    "btc_change_pct_10h",
    "btc_volatility_score",
    "btc_volume",
    "btc_label_spike",
]


class FeastHTTPClient:
    """
    HTTP client for remote Feast feature server.
    
    Communicates with Feast server via HTTP API for feature operations.
    """

    def __init__(
        self,
        server_url: str,
        timeout: int = 30,
        max_retries: int = 3,
    ):
        """
        Initialize Feast HTTP client.

        Args:
            server_url: Base URL of Feast server (e.g., "http://154.53.166.231:6566")
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.server_url = server_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self._session: Optional[aiohttp.ClientSession] = None
        logger.info(f"Initialized Feast HTTP client: server={self.server_url}")

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self):
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def get_online_features(
        self,
        feature_view_name: str,
        entity_rows: List[Dict[str, Any]],
        features: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Retrieve online features from Feast server.

        Args:
            feature_view_name: Name of the feature view
            entity_rows: List of entity dictionaries (e.g., [{"group_id": "123"}])
            features: Optional list of specific features to retrieve

        Returns:
            Dictionary with feature values

        Raises:
            Exception: If feature retrieval fails
        """
        session = await self._get_session()
        url = f"{self.server_url}/get-online-features"

        # Convert entity_rows from list of dicts to dict of lists
        # From: [{"group_id": "123"}, {"group_id": "456"}]
        # To: {"group_id": ["123", "456"]}
        entities_dict: Dict[str, List[Any]] = {}
        for row in entity_rows:
            for key, value in row.items():
                if key not in entities_dict:
                    entities_dict[key] = []
                entities_dict[key].append(value)

        # Use the Feast HTTP API format with features list
        # Format: {"features": ["view:feature1", "view:feature2"], "entities": {"entity_name": [values]}}
        if features is None:
            # Get all 28 features - use view:feature format
            feature_refs = [f"{feature_view_name}:{f}" for f in ALL_SEMANTIC_GROUP_FEATURES]
        else:
            # Get specific features - use view:feature format
            feature_refs = [f"{feature_view_name}:{f}" for f in features]

        payload = {
            "features": feature_refs,
            "entities": entities_dict,
            "full_feature_names": False,
        }

        logger.info(f"Feast HTTP request payload: features_count={len(feature_refs)}, entities={list(entities_dict.keys())}, entity_count={len(next(iter(entities_dict.values())))}")

        for attempt in range(self.max_retries):
            try:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(
                            f"Retrieved online features: "
                            f"feature_view={feature_view_name}, "
                            f"entities={len(entity_rows)}"
                        )
                        return result
                    else:
                        error_text = await response.text()
                        logger.error(
                            f"Failed to get online features (attempt {attempt + 1}): "
                            f"status={response.status}, error={error_text}"
                        )
                        if attempt == self.max_retries - 1:
                            raise Exception(
                                f"Failed to get online features after {self.max_retries} attempts: "
                                f"{error_text}"
                            )
            except aiohttp.ClientError as e:
                logger.error(f"HTTP error getting online features (attempt {attempt + 1}): {e}")
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)  # Exponential backoff

        raise Exception("Failed to get online features")

    async def health_check(self) -> bool:
        """
        Check if Feast server is healthy.

        Returns:
            True if server is healthy, False otherwise
        """
        session = await self._get_session()
        url = f"{self.server_url}/health"

        try:
            async with session.get(url) as response:
                is_healthy = response.status == 200
                if is_healthy:
                    logger.info("Feast server health check: OK")
                else:
                    logger.warning(f"Feast server health check failed: status={response.status}")
                return is_healthy
        except Exception as e:
            logger.error(f"Feast server health check error: {e}")
            return False


def get_feast_http_client(
    server_url: str = "http://154.53.166.231:6566",
    timeout: int = 30,
    max_retries: int = 3,
) -> FeastHTTPClient:
    """
    Get Feast HTTP client instance (singleton pattern).

    Args:
        server_url: Base URL of Feast server
        timeout: Request timeout in seconds
        max_retries: Maximum number of retry attempts

    Returns:
        FeastHTTPClient instance
    """
    return FeastHTTPClient(
        server_url=server_url,
        timeout=timeout,
        max_retries=max_retries,
    )

