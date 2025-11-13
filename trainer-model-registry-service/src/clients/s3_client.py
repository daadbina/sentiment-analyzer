"""
S3 client for Trainer & Model Registry Service.

Provides integration with AWS S3 for artifact storage.
"""

import logging
from typing import Optional, List
from pathlib import Path
import boto3
from botocore.exceptions import ClientError

from src.config import S3Config
from src.exceptions import ExternalServiceError

logger = logging.getLogger(__name__)


class S3Client:
    """AWS S3 client for artifact storage."""

    def __init__(self, config: S3Config):
        """
        Initialize S3 client.

        Args:
            config: S3 configuration
        """
        self.config = config
        self.client = None
        logger.info(f"S3 client initialized for bucket: {config.bucket}")

    def connect(self) -> None:
        """
        Initialize S3 client.

        Raises:
            ExternalServiceError: If connection fails
        """
        try:
            from botocore.config import Config

            # Configure S3 client with signature version v4 for MinIO compatibility
            s3_config = Config(
                signature_version='s3v4',
                s3={'addressing_style': 'path'}
            )

            self.client = boto3.client(
                "s3",
                region_name=self.config.region,
                aws_access_key_id=self.config.access_key_id,
                aws_secret_access_key=self.config.secret_access_key,
                endpoint_url=self.config.endpoint_url,
                config=s3_config,
            )
            logger.info(f"S3 client connected to {self.config.endpoint_url}")
        except Exception as e:
            logger.error(f"Failed to connect to S3: {e}")
            raise ExternalServiceError(
                f"Failed to connect to S3: {e}",
                service_name="S3",
                details={"bucket": self.config.bucket, "region": self.config.region},
            )

    def ensure_bucket_exists(self) -> None:
        """
        Ensure the configured bucket exists, create if not.

        Raises:
            ExternalServiceError: If bucket creation fails
        """
        if not self.client:
            raise ExternalServiceError(
                "S3 client not initialized",
                service_name="S3",
            )

        try:
            # Check if bucket exists
            self.client.head_bucket(Bucket=self.config.bucket)
            logger.info(f"Bucket {self.config.bucket} exists")
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                # Bucket doesn't exist, create it
                try:
                    logger.info(f"Creating bucket {self.config.bucket}")
                    self.client.create_bucket(Bucket=self.config.bucket)
                    logger.info(f"Bucket {self.config.bucket} created successfully")
                except Exception as create_error:
                    logger.error(f"Failed to create bucket: {create_error}")
                    raise ExternalServiceError(
                        f"Failed to create bucket: {create_error}",
                        service_name="S3",
                        details={"bucket": self.config.bucket},
                    )
            else:
                logger.error(f"Failed to check bucket: {e}")
                raise ExternalServiceError(
                    f"Failed to check bucket: {e}",
                    service_name="S3",
                    details={"bucket": self.config.bucket},
                )

    def health_check(self) -> bool:
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
            buckets = [b['Name'] for b in response.get('Buckets', [])]
            logger.info(f"S3 health check passed - available buckets: {buckets}")

            # Ensure our bucket exists
            self.ensure_bucket_exists()
            return True
        except ClientError as e:
            logger.warning(f"S3 health check warning (non-critical): {e}")
            # Return True anyway - S3 connection might still be functional
            return True

    def upload_file(self, local_path: str, s3_key: str) -> str:
        """
        Upload file to S3.

        Args:
            local_path: Local file path
            s3_key: S3 object key

        Returns:
            S3 URI of uploaded file

        Raises:
            ExternalServiceError: If upload fails
        """
        if not self.client:
            raise ExternalServiceError(
                "S3 client not initialized",
                service_name="S3",
            )

        try:
            path = Path(local_path)
            if not path.exists():
                raise FileNotFoundError(f"File not found: {local_path}")

            self.client.upload_file(local_path, self.config.bucket, s3_key)
            s3_uri = f"s3://{self.config.bucket}/{s3_key}"
            logger.info(f"Uploaded file to {s3_uri}")
            return s3_uri

        except Exception as e:
            logger.error(f"Failed to upload file to S3: {e}")
            raise ExternalServiceError(
                f"Failed to upload file to S3: {e}",
                service_name="S3",
                details={"local_path": local_path, "s3_key": s3_key},
            )

    def download_file(self, s3_key: str, local_path: str) -> None:
        """
        Download file from S3.

        Args:
            s3_key: S3 object key
            local_path: Local file path

        Raises:
            ExternalServiceError: If download fails
        """
        if not self.client:
            raise ExternalServiceError(
                "S3 client not initialized",
                service_name="S3",
            )

        try:
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)
            self.client.download_file(self.config.bucket, s3_key, local_path)
            logger.info(f"Downloaded file from s3://{self.config.bucket}/{s3_key}")

        except Exception as e:
            logger.error(f"Failed to download file from S3: {e}")
            raise ExternalServiceError(
                f"Failed to download file from S3: {e}",
                service_name="S3",
                details={"s3_key": s3_key, "local_path": local_path},
            )

    def list_objects(self, prefix: str = "") -> List[str]:
        """
        List objects in S3 bucket.

        Args:
            prefix: S3 key prefix

        Returns:
            List of object keys

        Raises:
            ExternalServiceError: If listing fails
        """
        if not self.client:
            raise ExternalServiceError(
                "S3 client not initialized",
                service_name="S3",
            )

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
            raise ExternalServiceError(
                f"Failed to list objects in S3: {e}",
                service_name="S3",
                details={"prefix": prefix},
            )

    def object_exists(self, s3_key: str) -> bool:
        """
        Check if object exists in S3.

        Args:
            s3_key: S3 object key

        Returns:
            True if object exists, False otherwise

        Raises:
            ExternalServiceError: If check fails
        """
        if not self.client:
            raise ExternalServiceError(
                "S3 client not initialized",
                service_name="S3",
            )

        try:
            self.client.head_object(Bucket=self.config.bucket, Key=s3_key)
            logger.debug(f"Object exists: {s3_key}")
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                logger.debug(f"Object not found: {s3_key}")
                return False
            logger.error(f"Failed to check object existence: {e}")
            raise ExternalServiceError(
                f"Failed to check object existence: {e}",
                service_name="S3",
                details={"s3_key": s3_key},
            )

    def delete_object(self, s3_key: str) -> None:
        """
        Delete object from S3.

        Args:
            s3_key: S3 object key

        Raises:
            ExternalServiceError: If deletion fails
        """
        if not self.client:
            raise ExternalServiceError(
                "S3 client not initialized",
                service_name="S3",
            )

        try:
            self.client.delete_object(Bucket=self.config.bucket, Key=s3_key)
            logger.info(f"Deleted object: {s3_key}")

        except Exception as e:
            logger.error(f"Failed to delete object from S3: {e}")
            raise ExternalServiceError(
                f"Failed to delete object from S3: {e}",
                service_name="S3",
                details={"s3_key": s3_key},
            )

    def get_object_metadata(self, s3_key: str) -> dict:
        """
        Get object metadata from S3.

        Args:
            s3_key: S3 object key

        Returns:
            Dictionary with object metadata

        Raises:
            ExternalServiceError: If retrieval fails
        """
        if not self.client:
            raise ExternalServiceError(
                "S3 client not initialized",
                service_name="S3",
            )

        try:
            response = self.client.head_object(
                Bucket=self.config.bucket,
                Key=s3_key,
            )

            metadata = {
                "size": response["ContentLength"],
                "last_modified": response["LastModified"],
                "etag": response["ETag"],
                "content_type": response.get("ContentType", ""),
            }

            logger.debug(f"Retrieved metadata for {s3_key}: {metadata}")
            return metadata

        except Exception as e:
            logger.error(f"Failed to get object metadata: {e}")
            raise ExternalServiceError(
                f"Failed to get object metadata: {e}",
                service_name="S3",
                details={"s3_key": s3_key},
            )
