"""
Feast HTTP Client for communicating with remote Feast feature server.

This client provides a unified interface for all services to interact with
the Feast feature store deployed at 154.53.166.231:6566.

Usage:
    from shared.feast_http_client import FeastHTTPClient
    
    client = FeastHTTPClient()
    features = await client.get_online_features(
        feature_refs=["semantic_group_features:sentiment_mean"],
        entity_rows=[{"group_id": "test-group-1"}]
    )
"""

import logging
import requests
import pandas as pd
from typing import Dict, List, Any, Optional
from datetime import datetime
import asyncio
from functools import wraps

logger = logging.getLogger(__name__)


def async_retry(max_retries: int = 3, delay: float = 1.0):
    """Decorator for retrying async functions with exponential backoff."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    wait_time = delay * (2 ** attempt)
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries} failed: {e}. "
                        f"Retrying in {wait_time}s..."
                    )
                    await asyncio.sleep(wait_time)
        return wrapper
    return decorator


class FeastHTTPClient:
    """
    HTTP client for Feast feature server.
    
    Provides methods to:
    - Get online features (for inference)
    - Push features to online store (for feature engineering)
    - Get historical features (for training)
    """
    
    def __init__(
        self,
        feature_server_url: str = "http://154.53.166.231:6566",
        timeout: int = 10,
        max_retries: int = 3
    ):
        """
        Initialize Feast HTTP client.
        
        Args:
            feature_server_url: URL of the Feast feature server
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.base_url = feature_server_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        logger.info(f"Feast HTTP client initialized: {self.base_url}")
    
    @async_retry(max_retries=3, delay=1.0)
    async def get_online_features(
        self,
        feature_refs: List[str],
        entity_rows: List[Dict[str, Any]]
    ) -> pd.DataFrame:
        """
        Get online features from Feast feature server.
        
        Args:
            feature_refs: List of feature references in format "feature_view:feature_name"
                         Example: ["semantic_group_features:sentiment_mean"]
            entity_rows: List of entity dictionaries
                        Example: [{"group_id": "test-group-1"}]
        
        Returns:
            DataFrame with requested features
        
        Raises:
            requests.HTTPError: If request fails
            ValueError: If response format is invalid
        """
        payload = {
            "features": feature_refs,
            "entities": entity_rows,
            "full_feature_names": True
        }
        
        logger.debug(f"Fetching online features: {len(feature_refs)} features for {len(entity_rows)} entities")
        
        try:
            response = requests.post(
                f"{self.base_url}/get-online-features",
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Convert to DataFrame
            if "results" in data:
                df = pd.DataFrame(data["results"])
            elif isinstance(data, list):
                df = pd.DataFrame(data)
            else:
                df = pd.DataFrame([data])
            
            logger.info(f"Retrieved {len(df)} rows with {len(df.columns)} features")
            return df
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout fetching features from {self.base_url}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching features: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise
    
    @async_retry(max_retries=3, delay=1.0)
    async def push_features(
        self,
        push_source_name: str,
        df: pd.DataFrame,
        to: str = "online"
    ) -> Dict[str, Any]:
        """
        Push features to Feast online/offline store.

        Args:
            push_source_name: Name of the push source (e.g., "semantic_group_push")
            df: DataFrame with features to push
            to: Target store - "online", "offline", or "online_and_offline"

        Returns:
            Response dictionary from Feast server

        Raises:
            requests.HTTPError: If request fails
        """
        # Convert DataFrame to dict, handling timestamp serialization
        df_copy = df.copy()

        # Convert all timestamp columns to ISO format strings
        for col in df_copy.columns:
            if pd.api.types.is_datetime64_any_dtype(df_copy[col]):
                df_copy[col] = df_copy[col].dt.strftime('%Y-%m-%dT%H:%M:%S.%fZ')

        payload = {
            "push_source_name": push_source_name,
            "df": df_copy.to_dict(orient="records"),
            "to": to
        }

        logger.debug(f"Pushing {len(df)} feature rows to {to} store")

        try:
            response = requests.post(
                f"{self.base_url}/push",
                json=payload,
                timeout=self.timeout * 2  # Push operations may take longer
            )
            response.raise_for_status()

            result = response.json()
            logger.info(f"Successfully pushed {len(df)} feature rows")
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"Error pushing features: {e}")
            raise

    async def health_check(self) -> bool:
        """
        Check if Feast feature server is healthy.

        Returns:
            True if server is healthy, False otherwise
        """
        try:
            response = requests.get(
                f"{self.base_url}/health",
                timeout=5
            )
            is_healthy = response.status_code == 200
            if is_healthy:
                logger.info("Feast server is healthy")
            else:
                logger.warning(f"Feast server health check failed: {response.status_code}")
            return is_healthy
        except Exception as e:
            logger.error(f"Feast server health check failed: {e}")
            return False

    async def get_feature_view_info(self, feature_view_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a feature view.

        Args:
            feature_view_name: Name of the feature view

        Returns:
            Dictionary with feature view metadata or None if not found
        """
        try:
            response = requests.get(
                f"{self.base_url}/feature-views/{feature_view_name}",
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning(f"Feature view not found: {feature_view_name}")
                return None
            logger.error(f"Error getting feature view info: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise

    async def materialize_incremental(
        self,
        feature_view_name: str,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Trigger incremental materialization of features.

        Args:
            feature_view_name: Name of the feature view to materialize
            end_date: End date for materialization (defaults to now)

        Returns:
            Materialization result
        """
        if end_date is None:
            end_date = datetime.now()

        payload = {
            "feature_view": feature_view_name,
            "end_date": end_date.isoformat()
        }

        logger.info(f"Triggering materialization for {feature_view_name}")

        try:
            response = requests.post(
                f"{self.base_url}/materialize-incremental",
                json=payload,
                timeout=self.timeout * 5  # Materialization can take time
            )
            response.raise_for_status()
            result = response.json()
            logger.info(f"Materialization completed: {result}")
            return result
        except Exception as e:
            logger.error(f"Materialization failed: {e}")
            raise


# Singleton instance for easy import
_feast_client_instance: Optional[FeastHTTPClient] = None


def get_feast_client(
    feature_server_url: str = "http://154.53.166.231:6566"
) -> FeastHTTPClient:
    """
    Get or create singleton Feast HTTP client instance.

    Args:
        feature_server_url: URL of the Feast feature server

    Returns:
        FeastHTTPClient instance
    """
    global _feast_client_instance
    if _feast_client_instance is None:
        _feast_client_instance = FeastHTTPClient(feature_server_url)
    return _feast_client_instance

