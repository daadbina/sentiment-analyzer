"""gRPC client for deduplication service."""

import logging
from typing import Optional
from datetime import datetime
import grpc
from src.config import get_config
from src.exceptions import DuplicateDetectionError
from src.utils.circuit_breaker import get_circuit_breaker_manager
from src.deduplication.dedup_engine import DeduplicationEngine

logger = logging.getLogger(__name__)


class DedupGrpcClient:
    """gRPC client for deduplication service.

    Uses local DeduplicationEngine with MinHash + LSH for duplicate detection.
    In production, this would connect to a remote gRPC service.
    """

    def __init__(self):
        """Initialize dedup gRPC client."""
        self.config = get_config()
        self.channel: Optional[grpc.aio.Channel] = None
        self.stub = None
        self.circuit_breaker = get_circuit_breaker_manager().get_or_create(
            "dedup_service"
        )
        # Local deduplication engine with MinHash + LSH
        self.dedup_engine = DeduplicationEngine(
            num_perm=128,
            similarity_threshold=self.config.deduplication.similarity_threshold,
            time_window_hours=self.config.deduplication.time_window_hours,
        )

    async def initialize(self) -> None:
        """Initialize gRPC channel."""
        try:
            # dedup_service is a string like "localhost:50051"
            self.channel = grpc.aio.secure_channel(
                self.config.dedup_service,
                grpc.ssl_channel_credentials(),
            )
            logger.info("Dedup gRPC channel initialized")
        except Exception as e:
            logger.debug(f"gRPC channel initialization skipped (optional component): {e}")
            # gRPC service is optional - service continues without it
            self.channel = None

    async def check_duplicate(
        self,
        checksum: str,
        content: str = "",
        published_at: Optional[datetime] = None,
    ) -> bool:
        """Check if article is duplicate.

        Args:
            checksum: Article checksum (SHA-256)
            content: Article content (title + body) for near-duplicate detection
            published_at: Publication timestamp for temporal filtering

        Returns:
            True if duplicate, False otherwise
        """
        try:
            # Use circuit breaker
            result = await self.circuit_breaker.call(
                self._check_duplicate_impl,
                checksum,
                content,
                published_at,
            )
            return result
        except Exception as e:
            logger.debug(f"Duplicate check failed (optional component): {e}")
            return False

    async def _check_duplicate_impl(
        self,
        checksum: str,
        content: str = "",
        published_at: Optional[datetime] = None,
    ) -> bool:
        """Implementation of duplicate check using local dedup engine.

        Args:
            checksum: Article checksum
            content: Article content for near-duplicate detection
            published_at: Publication timestamp

        Returns:
            True if duplicate
        """
        try:
            # Use local deduplication engine
            if not published_at:
                published_at = datetime.utcnow()

            result = self.dedup_engine.check_duplicate(
                checksum=checksum,
                content=content or "",
                published_at=published_at,
            )

            logger.debug(
                f"Duplicate check result: is_duplicate={result.is_duplicate}, "
                f"match_type={result.match_type}, similarity={result.similarity_score:.2f}"
            )

            return result.is_duplicate

        except Exception as e:
            logger.debug(f"Dedup engine error (optional component): {e}")
            return False

    async def register_article(
        self,
        checksum: str,
        article_id: str,
        content: str = "",
        published_at: Optional[datetime] = None,
    ) -> bool:
        """Register article in dedup service.

        Args:
            checksum: Article checksum
            article_id: Article ID
            content: Article content for indexing
            published_at: Publication timestamp

        Returns:
            True if successful
        """
        try:
            result = await self.circuit_breaker.call(
                self._register_article_impl,
                checksum,
                article_id,
                content,
                published_at,
            )
            return result
        except Exception as e:
            logger.debug(f"Article registration failed (optional): {e}")
            return False

    async def _register_article_impl(
        self,
        checksum: str,
        article_id: str,
        content: str = "",
        published_at: Optional[datetime] = None,
    ) -> bool:
        """Implementation of article registration using local dedup engine.

        Args:
            checksum: Article checksum
            article_id: Article ID
            content: Article content
            published_at: Publication timestamp

        Returns:
            True if successful
        """
        try:
            if not published_at:
                published_at = datetime.utcnow()

            self.dedup_engine.add_article(
                article_id=article_id,
                checksum=checksum,
                content=content or "",
                published_at=published_at,
            )

            logger.debug(f"Registered article {article_id} with checksum {checksum}")
            return True

        except Exception as e:
            logger.debug(f"Dedup engine registration error: {e}")
            return False

    async def close(self) -> None:
        """Close gRPC channel."""
        if self.channel:
            try:
                await self.channel.close()
                logger.info("Dedup gRPC channel closed")
            except Exception as e:
                logger.error(f"Error closing gRPC channel: {e}")
