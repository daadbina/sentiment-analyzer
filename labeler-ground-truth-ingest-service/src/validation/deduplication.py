"""Label deduplication engine."""

import hashlib
import json
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime, timedelta
import asyncpg
from src.config import config
from src.utils.trace import get_logger


logger = get_logger(__name__, config.logging.log_level)


class DeduplicationEngine:
    """
    Detect and handle duplicate labels from multiple sources.

    Maintains both in-memory cache and database cache for performance and persistence.
    """

    def __init__(self, db_pool: Optional[asyncpg.Pool] = None):
        """
        Initialize deduplication engine.

        Args:
            db_pool: Optional asyncpg connection pool for persistent cache
        """
        self.seen_hashes: Dict[str, Dict[str, Any]] = {}
        self.db_pool = db_pool
        self.cache_ttl_hours = 24  # TTL for deduplication cache entries
        logger.info(
            "Deduplication engine initialized",
            operation="init",
            db_persistence_enabled=db_pool is not None
        )

    async def load_cache_from_db(self) -> None:
        """Load deduplication cache from database on startup."""
        if not self.db_pool:
            logger.debug("Database pool not available, skipping cache load")
            return

        try:
            async with self.db_pool.acquire() as conn:
                # Load recent cache entries (within TTL)
                cutoff_time = datetime.utcnow() - timedelta(hours=self.cache_ttl_hours)

                rows = await conn.fetch("""
                    SELECT label_hash, label_data
                    FROM deduplication_cache
                    WHERE updated_at > $1
                """, cutoff_time)

                for row in rows:
                    label_hash = row['label_hash']
                    label_data = row['label_data']
                    # Parse JSON if it's a string (from database)
                    if isinstance(label_data, str):
                        label_data = json.loads(label_data)
                    self.seen_hashes[label_hash] = label_data

                logger.info(
                    f"Loaded {len(rows)} deduplication cache entries from database",
                    operation="load_cache_from_db",
                    entries_loaded=len(rows)
                )
        except Exception as e:
            logger.error(
                f"Failed to load deduplication cache from database: {str(e)}",
                operation="load_cache_from_db",
                error_type=type(e).__name__
            )

    async def _save_to_db(self, label_hash: str, label: Dict[str, Any]) -> None:
        """Save label hash to database for persistence."""
        if not self.db_pool:
            return

        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO deduplication_cache
                    (label_hash, event_id, event_date, label_source, label_confidence, label_data, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, CURRENT_TIMESTAMP)
                    ON CONFLICT (label_hash) DO UPDATE SET
                        label_confidence = EXCLUDED.label_confidence,
                        label_data = EXCLUDED.label_data,
                        updated_at = CURRENT_TIMESTAMP
                """,
                    label_hash,
                    label.get("event_id"),
                    label.get("event_date"),
                    label.get("label_source"),
                    label.get("label_confidence") or label.get("confidence"),
                    json.dumps(label)
                )
        except Exception as e:
            logger.error(
                f"Failed to save label hash to database: {str(e)}",
                operation="_save_to_db",
                error_type=type(e).__name__
            )

    async def _batch_save_to_db(self, labels_to_save: List[Tuple[str, Dict[str, Any]]]) -> None:
        """
        Batch save multiple labels to database for persistence.

        This is much more efficient than individual saves as it reduces
        database round trips from N to 1.

        Args:
            labels_to_save: List of (label_hash, label) tuples
        """
        if not self.db_pool or not labels_to_save:
            return

        try:
            async with self.db_pool.acquire() as conn:
                # Prepare batch data
                batch_data = [
                    (
                        label_hash,
                        label.get("event_id"),
                        label.get("event_date"),
                        label.get("label_source"),
                        label.get("label_confidence") or label.get("confidence"),
                        json.dumps(label)
                    )
                    for label_hash, label in labels_to_save
                ]

                # Use executemany for batch insert
                await conn.executemany("""
                    INSERT INTO deduplication_cache
                    (label_hash, event_id, event_date, label_source, label_confidence, label_data, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, CURRENT_TIMESTAMP)
                    ON CONFLICT (label_hash) DO UPDATE SET
                        label_confidence = EXCLUDED.label_confidence,
                        label_data = EXCLUDED.label_data,
                        updated_at = CURRENT_TIMESTAMP
                """, batch_data)

                logger.info(
                    f"Batch saved {len(labels_to_save)} labels to deduplication cache",
                    operation="_batch_save_to_db",
                    batch_size=len(labels_to_save)
                )

        except Exception as e:
            logger.error(
                f"Failed to batch save labels to database: {str(e)}",
                operation="_batch_save_to_db",
                error_type=type(e).__name__,
                batch_size=len(labels_to_save)
            )

    def _compute_label_hash(self, label: Dict[str, Any]) -> str:
        """
        Compute hash of label for deduplication.
        
        Hash is based on event_id, event_date, and source to identify duplicates.
        """
        try:
            # Extract key fields for hashing
            event_id = str(label.get("event_id", ""))
            event_date = str(label.get("event_date", ""))
            source = str(label.get("label_source", ""))
            
            # Create hash string
            hash_input = f"{event_id}:{event_date}:{source}"
            label_hash = hashlib.sha256(hash_input.encode()).hexdigest()
            
            return label_hash
        except Exception as e:
            logger.error(
                f"Failed to compute label hash: {str(e)}",
                operation="compute_label_hash",
                error_type=type(e).__name__
            )
            return ""

    def is_duplicate(self, label: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if label is a duplicate.

        Returns:
            Tuple of (is_duplicate: bool, existing_label: Dict or {})
        """
        try:
            label_hash = self._compute_label_hash(label)

            if not label_hash:
                return False, {}

            if label_hash in self.seen_hashes:
                existing = self.seen_hashes[label_hash]
                # Only log duplicates with different confidence scores (meaningful duplicates)
                # Support both 'label_confidence' and 'confidence' field names
                existing_conf = existing.get("label_confidence") or existing.get("confidence", 0.0)
                new_conf = label.get("label_confidence") or label.get("confidence", 0.0)
                if existing_conf != new_conf:
                    logger.debug(
                        f"Duplicate label detected with different confidence",
                        operation="is_duplicate",
                        existing_confidence=existing_conf,
                        new_confidence=new_conf
                    )
                return True, existing

            return False, {}
        except Exception as e:
            logger.error(
                f"Duplicate check failed: {str(e)}",
                operation="is_duplicate",
                error_type=type(e).__name__
            )
            return False, {}

    async def register_label(self, label: Dict[str, Any]) -> None:
        """
        Register label in deduplication cache (both in-memory and database).

        Args:
            label: Label to register
        """
        try:
            label_hash = self._compute_label_hash(label)

            if label_hash:
                self.seen_hashes[label_hash] = label
                # Save to database for persistence
                await self._save_to_db(label_hash, label)
                # Disabled verbose logging for cleaner output
                # logger.debug(
                #     f"Label registered for deduplication",
                #     operation="register_label",
                #     label_hash=label_hash
                # )
        except Exception as e:
            logger.error(
                f"Failed to register label: {str(e)}",
                operation="register_label",
                error_type=type(e).__name__
            )

    async def deduplicate_batch(
        self,
        labels: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Deduplicate batch of labels.

        Returns:
            Tuple of (unique_labels, duplicate_labels)
        """
        unique_labels = []
        duplicate_labels = []
        batch_hashes = {}  # Track hashes in this batch
        labels_to_save = []  # Collect labels for batch save

        try:
            # First pass: identify highest confidence for each hash in batch
            for label in labels:
                label_hash = self._compute_label_hash(label)

                if label_hash not in batch_hashes:
                    batch_hashes[label_hash] = label
                else:
                    # Compare confidence - support both 'label_confidence' and 'confidence'
                    existing_conf = batch_hashes[label_hash].get("label_confidence") or batch_hashes[label_hash].get("confidence", 0.0)
                    new_conf = label.get("label_confidence") or label.get("confidence", 0.0)

                    if new_conf > existing_conf:
                        # Replace with higher confidence
                        duplicate_labels.append(batch_hashes[label_hash])
                        batch_hashes[label_hash] = label
                    else:
                        # Keep existing
                        duplicate_labels.append(label)

            # Second pass: check against cache and collect labels to save
            for label_hash, label in batch_hashes.items():
                is_dup, existing = self.is_duplicate(label)

                if is_dup:
                    # Compare with cached version - support both field names
                    existing_conf = existing.get("label_confidence") or existing.get("confidence", 0.0)
                    new_conf = label.get("label_confidence") or label.get("confidence", 0.0)

                    if new_conf > existing_conf:
                        # Replace in cache
                        self.seen_hashes[label_hash] = label
                        labels_to_save.append((label_hash, label))
                        unique_labels.append(label)

                        logger.info(
                            f"Duplicate replaced with higher confidence label",
                            operation="deduplicate_batch",
                            old_confidence=existing_conf,
                            new_confidence=new_conf
                        )
                    else:
                        # Keep existing in cache
                        duplicate_labels.append(label)
                        # Removed verbose "Duplicate discarded" log - too noisy for debugging
                else:
                    # New label - add to cache and collect for batch save
                    self.seen_hashes[label_hash] = label
                    labels_to_save.append((label_hash, label))
                    unique_labels.append(label)

            # Batch save all new/updated labels to database
            if labels_to_save:
                await self._batch_save_to_db(labels_to_save)

            logger.info(
                f"Batch deduplication completed",
                operation="deduplicate_batch",
                total_labels=len(labels),
                unique_labels=len(unique_labels),
                duplicate_labels=len(duplicate_labels),
                saved_to_db=len(labels_to_save)
            )

            return unique_labels, duplicate_labels

        except Exception as e:
            logger.error(
                f"Batch deduplication failed: {str(e)}",
                operation="deduplicate_batch",
                error_type=type(e).__name__
            )
            return labels, []

    def clear_cache(self) -> None:
        """Clear deduplication cache."""
        try:
            cache_size = len(self.seen_hashes)
            self.seen_hashes.clear()
            logger.info(
                f"Deduplication cache cleared",
                operation="clear_cache",
                cache_size=cache_size
            )
        except Exception as e:
            logger.error(
                f"Failed to clear cache: {str(e)}",
                operation="clear_cache",
                error_type=type(e).__name__
            )

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get deduplication cache statistics."""
        return {
            "cache_size": len(self.seen_hashes),
            "operation": "get_cache_stats"
        }

