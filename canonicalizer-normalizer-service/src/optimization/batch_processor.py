"""Batch processing for improved throughput."""

import logging
import asyncio
from typing import Callable, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class BatchResult:
    """Result of batch processing."""

    total_items: int
    successful_items: int
    failed_items: int
    results: list[Any]
    errors: list[str]

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_items == 0:
            return 0.0
        return self.successful_items / self.total_items


class BatchProcessor:
    """Process items in batches for improved throughput."""

    def __init__(self, batch_size: int = 100, max_workers: int = 4):
        """Initialize batch processor.

        Args:
            batch_size: Number of items per batch
            max_workers: Maximum concurrent workers
        """
        self.batch_size = batch_size
        self.max_workers = max_workers

    async def process_batch(
        self,
        items: list[Any],
        processor_func: Callable,
        *args,
        **kwargs
    ) -> BatchResult:
        """Process items in batches.

        Args:
            items: Items to process
            processor_func: Async function to process each item
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments

        Returns:
            Batch processing result
        """
        if not items:
            return BatchResult(
                total_items=0,
                successful_items=0,
                failed_items=0,
                results=[],
                errors=[],
            )

        total_items = len(items)
        successful_items = 0
        failed_items = 0
        results = []
        errors = []

        # Process in batches
        for i in range(0, len(items), self.batch_size):
            batch = items[i:i + self.batch_size]

            # Process batch with concurrent workers
            tasks = [
                processor_func(item, *args, **kwargs)
                for item in batch
            ]

            try:
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)

                for result in batch_results:
                    if isinstance(result, Exception):
                        failed_items += 1
                        errors.append(str(result))
                    else:
                        successful_items += 1
                        results.append(result)
            except Exception as e:
                logger.error(f"Error processing batch: {e}")
                failed_items += len(batch)
                errors.append(str(e))

        return BatchResult(
            total_items=total_items,
            successful_items=successful_items,
            failed_items=failed_items,
            results=results,
            errors=errors,
        )

    async def process_batch_sequential(
        self,
        items: list[Any],
        processor_func: Callable,
        *args,
        **kwargs
    ) -> BatchResult:
        """Process items sequentially in batches.

        Args:
            items: Items to process
            processor_func: Async function to process each item
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments

        Returns:
            Batch processing result
        """
        if not items:
            return BatchResult(
                total_items=0,
                successful_items=0,
                failed_items=0,
                results=[],
                errors=[],
            )

        total_items = len(items)
        successful_items = 0
        failed_items = 0
        results = []
        errors = []

        for item in items:
            try:
                result = await processor_func(item, *args, **kwargs)
                successful_items += 1
                results.append(result)
            except Exception as e:
                logger.error(f"Error processing item: {e}")
                failed_items += 1
                errors.append(str(e))

        return BatchResult(
            total_items=total_items,
            successful_items=successful_items,
            failed_items=failed_items,
            results=results,
            errors=errors,
        )


class DatabaseBatchOperations:
    """Batch database operations for improved performance."""

    def __init__(self, db_client, batch_size: int = 100):
        """Initialize database batch operations.

        Args:
            db_client: Database client
            batch_size: Batch size for operations
        """
        self.db_client = db_client
        self.batch_size = batch_size

    async def batch_insert(self, table: str, records: list[dict]) -> int:
        """Insert multiple records in batches.

        Args:
            table: Table name
            records: Records to insert

        Returns:
            Number of records inserted
        """
        if not records:
            return 0

        inserted = 0
        for i in range(0, len(records), self.batch_size):
            batch = records[i:i + self.batch_size]
            try:
                # Placeholder for actual batch insert
                inserted += len(batch)
            except Exception as e:
                logger.error(f"Error batch inserting: {e}")

        return inserted

    async def batch_update(self, table: str, updates: list[dict]) -> int:
        """Update multiple records in batches.

        Args:
            table: Table name
            updates: Updates to apply

        Returns:
            Number of records updated
        """
        if not updates:
            return 0

        updated = 0
        for i in range(0, len(updates), self.batch_size):
            batch = updates[i:i + self.batch_size]
            try:
                # Placeholder for actual batch update
                updated += len(batch)
            except Exception as e:
                logger.error(f"Error batch updating: {e}")

        return updated


class RedisBatchOperations:
    """Batch Redis operations for improved performance."""

    def __init__(self, redis_client, batch_size: int = 100):
        """Initialize Redis batch operations.

        Args:
            redis_client: Redis client
            batch_size: Batch size for operations
        """
        self.redis_client = redis_client
        self.batch_size = batch_size

    async def batch_set(self, key_values: dict[str, Any], ttl: Optional[int] = None) -> int:
        """Set multiple key-value pairs in batches.

        Args:
            key_values: Dictionary of key-value pairs
            ttl: Optional TTL for all keys

        Returns:
            Number of keys set
        """
        if not key_values:
            return 0

        set_count = 0
        items = list(key_values.items())

        for i in range(0, len(items), self.batch_size):
            batch = items[i:i + self.batch_size]
            try:
                for key, value in batch:
                    if ttl:
                        await self.redis_client.setex(key, ttl, str(value))
                    else:
                        await self.redis_client.set(key, str(value))
                    set_count += 1
            except Exception as e:
                logger.error(f"Error batch setting Redis keys: {e}")

        return set_count

    async def batch_delete(self, keys: list[str]) -> int:
        """Delete multiple keys in batches.

        Args:
            keys: Keys to delete

        Returns:
            Number of keys deleted
        """
        if not keys:
            return 0

        deleted = 0
        for i in range(0, len(keys), self.batch_size):
            batch = keys[i:i + self.batch_size]
            try:
                for key in batch:
                    await self.redis_client.delete(key)
                    deleted += 1
            except Exception as e:
                logger.error(f"Error batch deleting Redis keys: {e}")

        return deleted

