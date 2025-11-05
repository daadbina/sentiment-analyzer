"""Delta Lake writer for ground truth labels."""

import time
from datetime import datetime
from typing import Any, Dict, List, Optional
import pandas as pd
from deltalake import write_deltalake

from src.config import config
from src.exceptions import StorageError
from src.utils.trace import get_logger
from src.metrics import get_metrics


logger = get_logger(__name__, config.logging.log_level)
metrics = get_metrics(config.metrics.prometheus_port)


class DeltaLakeWriter:
    """Write labels to Delta Lake."""

    def __init__(self, path: str = None):
        """Initialize Delta Lake writer."""
        self.path = path or config.storage.delta_lake_path
        logger.info(
            f"Initializing Delta Lake writer",
            operation="init_delta_writer",
            path=self.path
        )

    def _sanitize_labels(self, labels: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sanitize labels for Delta Lake (no nullable types)."""
        import json
        sanitized = []

        for label in labels:
            sanitized_label = {}
            for key, value in label.items():
                if value is None:
                    # Replace None with appropriate defaults
                    sanitized_label[key] = ""
                elif isinstance(value, dict):
                    # Convert dicts to JSON strings
                    sanitized_label[key] = json.dumps(value)
                elif isinstance(value, (list, tuple)):
                    # Convert lists/tuples to JSON strings
                    sanitized_label[key] = json.dumps(value)
                elif isinstance(value, bool):
                    # Convert bool to string
                    sanitized_label[key] = str(value)
                elif isinstance(value, (int, float)):
                    # Convert numbers to string
                    sanitized_label[key] = str(value)
                else:
                    # Everything else as string
                    sanitized_label[key] = str(value)

            sanitized.append(sanitized_label)

        return sanitized

    async def write_labels(self, labels: List[Dict[str, Any]]) -> bool:
        """
        Write labels to Delta Lake.

        Returns:
            True if successful, False otherwise
        """
        if not labels:
            logger.warning(
                "No labels to write",
                operation="write_labels"
            )
            return True

        start_time = time.time()

        try:
            # Sanitize labels
            sanitized_labels = self._sanitize_labels(labels)

            # Create DataFrame
            df = pd.DataFrame(sanitized_labels)

            # Add metadata
            df["written_at"] = datetime.utcnow().isoformat()
            df["batch_size"] = str(len(labels))

            # Write to Delta Lake
            write_deltalake(
                self.path,
                df,
                mode="append",
                engine="rust"
            )

            duration_seconds = time.time() - start_time
            metrics.record_storage("delta_lake", duration_seconds)

            logger.info(
                f"Successfully wrote {len(labels)} labels to Delta Lake",
                operation="write_labels",
                label_count=len(labels),
                duration_seconds=duration_seconds
            )

            return True

        except Exception as e:
            logger.error(
                f"Failed to write labels to Delta Lake: {str(e)}",
                operation="write_labels",
                error_type=type(e).__name__,
                label_count=len(labels)
            )
            raise StorageError("delta_lake", "write_labels", str(e))

    async def write_reconciliation_results(
        self,
        results: List[Dict[str, Any]]
    ) -> bool:
        """Write reconciliation results to Delta Lake."""
        if not results:
            return True

        start_time = time.time()

        try:
            # Sanitize results
            sanitized_results = self._sanitize_labels(results)

            # Create DataFrame
            df = pd.DataFrame(sanitized_results)

            # Add metadata
            df["reconciled_at"] = datetime.utcnow().isoformat()

            # Write to Delta Lake
            reconciliation_path = f"{self.path}/reconciliation"
            write_deltalake(
                reconciliation_path,
                df,
                mode="append",
                engine="rust"
            )

            duration_seconds = time.time() - start_time
            metrics.record_storage("delta_lake_reconciliation", duration_seconds)

            logger.info(
                f"Successfully wrote {len(results)} reconciliation results to Delta Lake",
                operation="write_reconciliation_results",
                result_count=len(results),
                duration_seconds=duration_seconds
            )

            return True

        except Exception as e:
            logger.error(
                f"Failed to write reconciliation results to Delta Lake: {str(e)}",
                operation="write_reconciliation_results",
                error_type=type(e).__name__
            )
            raise StorageError("delta_lake", "write_reconciliation_results", str(e))

    async def write_validation_results(
        self,
        valid_labels: List[Dict[str, Any]],
        invalid_labels: List[Dict[str, Any]]
    ) -> bool:
        """Write validation results to Delta Lake."""
        start_time = time.time()

        try:
            # Write valid labels to separate validation table
            if valid_labels:
                sanitized_valid = self._sanitize_labels(valid_labels)
                df_valid = pd.DataFrame(sanitized_valid)
                df_valid["validation_status"] = "valid"
                df_valid["validated_at"] = datetime.utcnow().isoformat()

                validation_path = f"{self.path}/validation"
                write_deltalake(
                    validation_path,
                    df_valid,
                    mode="append",
                    engine="rust"
                )

            # Write invalid labels
            if invalid_labels:
                sanitized_invalid = self._sanitize_labels(invalid_labels)
                df_invalid = pd.DataFrame(sanitized_invalid)
                df_invalid["validation_status"] = "invalid"
                df_invalid["validated_at"] = datetime.utcnow().isoformat()

                validation_path = f"{self.path}/validation"
                write_deltalake(
                    validation_path,
                    df_invalid,
                    mode="append",
                    engine="rust"
                )

            duration_seconds = time.time() - start_time
            metrics.record_storage("delta_lake_validation", duration_seconds)

            logger.info(
                f"Successfully wrote validation results to Delta Lake",
                operation="write_validation_results",
                valid_count=len(valid_labels),
                invalid_count=len(invalid_labels),
                duration_seconds=duration_seconds
            )

            return True

        except Exception as e:
            logger.error(
                f"Failed to write validation results to Delta Lake: {str(e)}",
                operation="write_validation_results",
                error_type=type(e).__name__
            )
            raise StorageError("delta_lake", "write_validation_results", str(e))

