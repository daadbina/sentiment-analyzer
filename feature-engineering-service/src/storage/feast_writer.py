"""Feast writer for online and offline features using HTTP client."""

from typing import Dict, Any
import pandas as pd
from datetime import datetime
import asyncio
import sys
import os

# Add shared directory to path to import FeastHTTPClient
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../shared"))
from feast_http_client import FeastHTTPClient

from ..utils import StructuredLogger
from ..exceptions import FeastWriteError
from ..config import FeastHTTPConfig

logger = StructuredLogger(__name__)


class FeastWriter:
    """Write features to Feast online and offline stores via HTTP."""

    def __init__(self):
        """Initialize writer with HTTP client."""
        config = FeastHTTPConfig()
        self.client = FeastHTTPClient(
            feature_server_url=config.server_url,
            timeout=config.timeout,
            max_retries=config.max_retries
        )
        self.push_source_name = config.push_source_name
        logger.info(
            "Feast HTTP writer initialized",
            server_url=config.server_url,
            push_source=self.push_source_name
        )

    def write_features(
        self,
        group_id: str,
        features: Dict[str, Any],
        to: str = "online_and_offline"
    ) -> bool:
        """Write features to Feast online and/or offline stores.

        Args:
            group_id: Semantic group ID
            features: Feature dictionary
            to: Target store - "online", "offline", or "online_and_offline"

        Returns:
            True if successful
        """
        try:
            # Prepare feature data with required fields
            timestamp = datetime.utcnow()

            # Create DataFrame with all required fields
            feature_data = pd.DataFrame([{
                "group_id": group_id,
                "event_timestamp": timestamp,
                "created_at": timestamp,
                **features,
            }])

            # Push features to Feast via HTTP
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If event loop is already running, create a task
                future = asyncio.ensure_future(
                    self.client.push_features(
                        push_source_name=self.push_source_name,
                        df=feature_data,
                        to=to
                    )
                )
                # Wait for completion
                result = loop.run_until_complete(future)
            else:
                # If no event loop, run directly
                result = asyncio.run(
                    self.client.push_features(
                        push_source_name=self.push_source_name,
                        df=feature_data,
                        to=to
                    )
                )

            logger.info(
                "Features written to Feast via HTTP",
                group_id=group_id,
                feature_count=len(features),
                target_store=to,
                result=result
            )

            return True

        except Exception as e:
            logger.error(
                "Error writing features to Feast",
                group_id=group_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise FeastWriteError(f"Error writing features to Feast: {str(e)}")

    def close(self):
        """Close connection (no-op for HTTP client)."""
        logger.info("Feast HTTP writer closed")

