"""Label deduplication engine."""

import hashlib
from typing import Dict, List, Any, Tuple
from src.config import config
from src.utils.trace import get_logger


logger = get_logger(__name__, config.logging.log_level)


class DeduplicationEngine:
    """Detect and handle duplicate labels from multiple sources."""

    def __init__(self):
        """Initialize deduplication engine."""
        self.seen_hashes: Dict[str, Dict[str, Any]] = {}
        logger.info(
            "Deduplication engine initialized",
            operation="init"
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
                logger.debug(
                    f"Duplicate label detected",
                    operation="is_duplicate",
                    label_hash=label_hash,
                    existing_confidence=existing.get("confidence", 0.0),
                    new_confidence=label.get("confidence", 0.0)
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

    def register_label(self, label: Dict[str, Any]) -> None:
        """Register label in deduplication cache."""
        try:
            label_hash = self._compute_label_hash(label)

            if label_hash:
                self.seen_hashes[label_hash] = label
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

    def deduplicate_batch(
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

        try:
            # First pass: identify highest confidence for each hash in batch
            for label in labels:
                label_hash = self._compute_label_hash(label)

                if label_hash not in batch_hashes:
                    batch_hashes[label_hash] = label
                else:
                    # Compare confidence
                    existing_conf = batch_hashes[label_hash].get("confidence", 0.0)
                    new_conf = label.get("confidence", 0.0)

                    if new_conf > existing_conf:
                        # Replace with higher confidence
                        batch_hashes[label_hash] = label
                        duplicate_labels.append(batch_hashes[label_hash])
                    else:
                        # Keep existing
                        duplicate_labels.append(label)

            # Second pass: check against cache and register
            for label_hash, label in batch_hashes.items():
                is_dup, existing = self.is_duplicate(label)

                if is_dup:
                    # Compare with cached version
                    existing_conf = existing.get("confidence", 0.0)
                    new_conf = label.get("confidence", 0.0)

                    if new_conf > existing_conf:
                        # Replace in cache
                        self.seen_hashes[label_hash] = label
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
                        logger.debug(
                            f"Duplicate discarded (lower confidence)",
                            operation="deduplicate_batch",
                            existing_confidence=existing_conf,
                            new_confidence=new_conf
                        )
                else:
                    # New label
                    self.register_label(label)
                    unique_labels.append(label)
            
            logger.info(
                f"Batch deduplication completed",
                operation="deduplicate_batch",
                total_labels=len(labels),
                unique_labels=len(unique_labels),
                duplicate_labels=len(duplicate_labels)
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

