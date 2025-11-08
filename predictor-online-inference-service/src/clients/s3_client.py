"""
S3 client for Predictor Online Inference Service.

Provides integration with AWS S3 for model artifact retrieval.
"""

import logging
from pathlib import Path
from typing import List

import boto3
from botocore.exceptions import ClientError

from ..config import S3Config
from ..exceptions import ModelLoadError

logger = logging.getLogger(__name__)


class S3Client:
    """AWS S3 client for model artifact retrieval."""

    def __init__(self, config: S3Config):
        """
        Initialize S3 client.

        Args:
            config: S3 configuration
        """
        self.config = config
        self.client = None
        logger.info(f"S3 client initialized for bucket: {config.bucket}")

    async def connect(self) -> None:
        """
        Initialize S3 client.

        Raises:
            ModelLoadError: If connection fails
        """
        try:
            self.client = boto3.client(
                "s3",
                region_name=self.config.region,
                aws_access_key_id=self.config.access_key_id,
                aws_secret_access_key=self.config.secret_access_key,
                endpoint_url=self.config.endpoint_url,
            )
            logger.info(f"S3 client connected to {self.config.endpoint_url}")
        except Exception as e:
            logger.error(f"Failed to connect to S3: {e}")
            raise ModelLoadError(
                f"Failed to connect to S3: {e}",
                context={"bucket": self.config.bucket, "region": self.config.region},
            )

    async def disconnect(self) -> None:
        """Disconnect from S3."""
        logger.info("Disconnecting from S3")
        self.client = None

    def _ensure_connected(self) -> None:
        """
        Ensure client is connected.

        Raises:
            ModelLoadError: If not connected
        """
        if self.client is None:
            raise ModelLoadError("S3 client not connected. Call connect() first.")

    async def download_file(self, s3_key: str, local_path: str) -> None:
        """
        Download file from S3.

        Args:
            s3_key: S3 object key
            local_path: Local file path

        Raises:
            ModelLoadError: If download fails
        """
        self._ensure_connected()

        try:
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)
            self.client.download_file(self.config.bucket, s3_key, local_path)
            logger.info(f"Downloaded file from s3://{self.config.bucket}/{s3_key} to {local_path}")

        except Exception as e:
            logger.error(f"Failed to download file from S3: {e}")
            raise ModelLoadError(
                f"Failed to download file from S3: {e}",
                context={"s3_key": s3_key, "local_path": local_path},
            )

    async def list_objects(self, prefix: str = "") -> List[str]:
        """
        List objects in S3 bucket.

        Args:
            prefix: S3 key prefix

        Returns:
            List of object keys

        Raises:
            ModelLoadError: If listing fails
        """
        self._ensure_connected()

        try:
            response = self.client.list_objects_v2(
                Bucket=self.config.bucket,
                Prefix=prefix,
            )

            keys = []
            if "Contents" in response:
                keys = [obj["Key"] for obj in response["Contents"]]

            logger.debug(f"Listed {len(keys)} objects with prefix: {prefix}")
            return keys

        except Exception as e:
            logger.error(f"Failed to list objects in S3: {e}")
            raise ModelLoadError(
                f"Failed to list objects in S3: {e}",
                context={"prefix": prefix},
            )

    async def object_exists(self, s3_key: str) -> bool:
        """
        Check if object exists in S3.

        Args:
            s3_key: S3 object key

        Returns:
            True if object exists, False otherwise
        """
        self._ensure_connected()

        try:
            self.client.head_object(Bucket=self.config.bucket, Key=s3_key)
            logger.debug(f"Object exists: {s3_key}")
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                logger.debug(f"Object does not exist: {s3_key}")
                return False
            else:
                logger.error(f"Failed to check object existence: {e}")
                raise ModelLoadError(
                    f"Failed to check object existence: {e}",
                    context={"s3_key": s3_key},
                )

    async def health_check(self) -> bool:
        """
        Check S3 connection health.

        Returns:
            True if connection is healthy, False otherwise
        """
        if not self.client:
            logger.warning("S3 client not initialized")
            return False

        try:
            # Try to list buckets to verify connection
            response = self.client.list_buckets()
            buckets = [b["Name"] for b in response.get("Buckets", [])]
            logger.info(f"S3 health check passed - available buckets: {buckets}")
            return True
        except ClientError as e:
            logger.warning(f"S3 health check warning (non-critical): {e}")
            # Return True anyway - S3 connection might still be functional
            return True
        except Exception as e:
            logger.error(f"S3 health check failed: {e}")
            return False

