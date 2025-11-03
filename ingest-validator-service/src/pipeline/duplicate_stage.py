"""Duplicate detection stage."""

import logging
from src.pipeline.stage import ValidationStage
from src.models import ValidationContext
from src.clients.dedup_grpc_client import DedupGrpcClient
from src.cache.redis_manager import RedisCacheManager

logger = logging.getLogger(__name__)


class DuplicateDetectionStage(ValidationStage):
    """Detects duplicate articles (R3)."""

    def __init__(
        self,
        dedup_client: DedupGrpcClient,
        cache_manager: RedisCacheManager,
    ):
        """Initialize duplicate detection stage.

        Args:
            dedup_client: Deduplication gRPC client
            cache_manager: Redis cache manager
        """
        super().__init__("DuplicateDetection")
        self.dedup_client = dedup_client
        self.cache_manager = cache_manager

    async def execute(self, context: ValidationContext) -> ValidationContext:
        """Execute duplicate detection with MinHash + LSH.

        Args:
            context: Validation context

        Returns:
            Updated validation context
        """
        try:
            checksum = context.checksum

            # Skip if no checksum
            if not checksum:
                context.validation_details.not_duplicate = True
                return context

            # Check cache first
            cache_key = self.cache_manager.get_checksum_cache_key(checksum)
            if self.cache_manager.exists(cache_key):
                error_msg = f"Duplicate detected (cached): {checksum}"
                self._add_error(context, error_msg)
                context.validation_details.not_duplicate = False
                logger.info(f"[{self.name}] {error_msg} for {context.article_id}")
                return context

            # Prepare content for near-duplicate detection
            content = f"{context.title} {context.body}".strip()

            # Check dedup service (exact + near-duplicate detection)
            is_duplicate = await self.dedup_client.check_duplicate(
                checksum=checksum,
                content=content,
                published_at=context.source_published_at_utc,
            )

            if is_duplicate:
                error_msg = f"Duplicate detected: {checksum}"
                self._add_error(context, error_msg)
                context.validation_details.not_duplicate = False
                logger.info(f"[{self.name}] {error_msg} for {context.article_id}")
                return context

            # Register article in dedup service for future checks
            await self.dedup_client.register_article(
                checksum=checksum,
                article_id=context.article_id,
                content=content,
                published_at=context.source_published_at_utc,
            )

            # Cache the checksum
            self.cache_manager.set(cache_key, {"article_id": context.article_id})

            context.validation_details.not_duplicate = True
            logger.info(f"[{self.name}] No duplicate found for {context.article_id}")

            return context

        except Exception as e:
            logger.error(f"[{self.name}] Detection error: {e}")
            self._add_warning(context, f"Duplicate detection error: {e}")
            # Don't fail on duplicate detection errors
            context.validation_details.not_duplicate = True
            return context
