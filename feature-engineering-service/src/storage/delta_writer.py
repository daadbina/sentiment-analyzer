"""Delta Lake writer for offline features."""

from typing import Dict, Any
from pathlib import Path
import pandas as pd
from datetime import datetime
import pytz
import os
from deltalake import write_deltalake, DeltaTable
from ..utils import StructuredLogger
from ..exceptions import FeastWriteError
from ..config import config

logger = StructuredLogger(__name__)


class DeltaLakeWriter:
    """Write features to Delta Lake offline store."""

    def __init__(self, delta_path: str = "C:/data/features"):
        """Initialize Delta Lake writer.

        Args:
            delta_path: Path to Delta Lake table for computed features
        """
        self.delta_path = delta_path
        self.path = Path(delta_path)
        
        # Ensure directory exists
        self.path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(
            "Delta Lake writer initialized",
            delta_path=delta_path,
        )

    def write_features(
        self,
        group_id: str,
        features: Dict[str, Any],
    ) -> bool:
        """Write features to Delta Lake using append mode.

        Uses append mode instead of UPSERT to avoid loading entire table into memory.
        Deduplication is handled at read time by selecting the latest record per group_id.
        This approach is more scalable and memory-efficient.

        Args:
            group_id: Semantic group ID
            features: Feature dictionary

        Returns:
            True if successful
        """
        try:
            # Prepare feature data with metadata
            timestamp = datetime.now(pytz.UTC).isoformat()
            feature_data = {
                "group_id": group_id,
                "timestamp": timestamp,
                **features,
            }

            # Create DataFrame
            df = pd.DataFrame([feature_data])

            # Convert None values to pd.NA for proper nullable type handling
            # Delta Lake/PyArrow doesn't support Python None directly
            for col in df.columns:
                if df[col].iloc[0] is None:
                    # For boolean columns with None, use nullable boolean type
                    if col == 'has_conflict':
                        df[col] = df[col].astype('boolean')  # pandas nullable boolean
                    else:
                        df[col] = pd.NA

            logger.debug(
                "Prepared feature DataFrame for Delta Lake write",
                group_id=group_id,
                feature_count=len(features),
                columns=list(df.columns),
                dtypes={col: str(dtype) for col, dtype in df.dtypes.items()},
            )

            # Write to Delta Lake with append mode
            from pathlib import Path as PathlibPath
            import shutil

            table_exists = PathlibPath(self.delta_path).exists() and len(list(PathlibPath(self.delta_path).glob("*.parquet"))) > 0

            logger.debug(
                "Delta Lake write parameters",
                table_exists=table_exists,
                delta_path=self.delta_path,
                mode="append" if table_exists else "overwrite",
            )

            # Determine write mode
            mode = "append" if table_exists else "overwrite"

            # Try writing with pyarrow engine first (more memory-efficient)
            try:
                write_deltalake(
                    table_or_uri=str(self.delta_path),
                    data=df,
                    mode=mode,
                    engine="pyarrow",  # Use pyarrow instead of rust for better memory efficiency
                )
                logger.debug(
                    "Successfully wrote to Delta Lake with pyarrow engine",
                    group_id=group_id,
                    mode=mode,
                )
            except OSError as os_error:
                # Handle resource exhaustion errors (paging file too small, etc.)
                if "os error 1455" in str(os_error).lower() or "paging file" in str(os_error).lower():
                    logger.warning(
                        "Resource exhaustion detected, retrying with minimal settings",
                        error=str(os_error),
                        group_id=group_id,
                    )
                    # Retry with rust engine but with error handling
                    try:
                        write_deltalake(
                            table_or_uri=str(self.delta_path),
                            data=df,
                            mode=mode,
                            engine="rust",
                        )
                        logger.info(
                            "Successfully wrote to Delta Lake with rust engine after retry",
                            group_id=group_id,
                        )
                    except Exception as retry_error:
                        logger.error(
                            "Failed to write to Delta Lake after retry",
                            error=str(retry_error),
                            group_id=group_id,
                        )
                        raise
                else:
                    raise
            except Exception as write_error:
                # Handle schema mismatch by recreating table
                if "Schema of data does not match table schema" in str(write_error):
                    logger.warning(
                        "Schema mismatch detected, recreating Delta Lake table",
                        delta_path=self.delta_path,
                        error=str(write_error),
                    )
                    # Delete existing table
                    if PathlibPath(self.delta_path).exists():
                        shutil.rmtree(self.delta_path)
                    # Recreate with overwrite
                    write_deltalake(
                        table_or_uri=str(self.delta_path),
                        data=df,
                        mode="overwrite",
                        engine="pyarrow",
                    )
                    logger.info("Delta Lake table recreated successfully")
                else:
                    raise

            logger.info(
                "Features written to Delta Lake (APPEND)",
                group_id=group_id,
                feature_count=len(features),
                delta_path=self.delta_path,
                timestamp=timestamp,
                mode=mode,
            )
            return True

        except Exception as e:
            logger.error(
                "Error writing features to Delta Lake",
                group_id=group_id,
                error=str(e),
                error_type=type(e).__name__,
                delta_path=self.delta_path,
            )
            raise FeastWriteError(f"Error writing features to Delta Lake: {str(e)}")

    def read_features(self, group_id: str) -> Dict[str, Any]:
        """Read features for a group from Delta Lake.

        Handles deduplication by selecting the latest record per group_id.
        This works with the append-mode write strategy.

        Args:
            group_id: Semantic group ID

        Returns:
            Feature dictionary
        """
        try:
            # Read from Delta Lake using DeltaTable for better performance
            try:
                dt = DeltaTable(self.delta_path)
                df = dt.to_pandas()
            except Exception:
                # Fallback to parquet if Delta table not available
                df = pd.read_parquet(str(self.delta_path))

            # Filter for group_id
            group_df = df[df["group_id"] == group_id]

            if len(group_df) == 0:
                logger.warning(
                    "No features found for group",
                    group_id=group_id,
                    delta_path=self.delta_path,
                )
                return {}

            # Get latest record (by timestamp) - handles duplicates from append mode
            latest = group_df.sort_values("timestamp").iloc[-1]

            logger.info(
                "Features read from Delta Lake",
                group_id=group_id,
                delta_path=self.delta_path,
                duplicate_count=len(group_df) - 1,
            )

            return latest.to_dict()

        except Exception as e:
            logger.error(
                "Error reading features from Delta Lake",
                group_id=group_id,
                error=str(e),
                error_type=type(e).__name__,
                delta_path=self.delta_path,
            )
            raise FeastWriteError(f"Error reading features from Delta Lake: {str(e)}")

    def get_table_stats(self) -> Dict[str, Any]:
        """Get statistics about Delta Lake table.

        Returns:
            Table statistics
        """
        try:
            # Use DeltaTable for better performance
            try:
                dt = DeltaTable(self.delta_path)
                df = dt.to_pandas()
            except Exception:
                df = pd.read_parquet(str(self.delta_path))

            # Calculate duplicate statistics
            duplicate_count = len(df) - df['group_id'].nunique() if 'group_id' in df.columns else 0

            stats = {
                "row_count": len(df),
                "unique_groups": df['group_id'].nunique() if 'group_id' in df.columns else 0,
                "duplicate_count": duplicate_count,
                "column_count": len(df.columns),
                "columns": list(df.columns),
                "memory_usage_mb": df.memory_usage(deep=True).sum() / 1024 / 1024,
            }

            logger.info(
                "Retrieved Delta Lake table statistics",
                delta_path=self.delta_path,
                stats=stats,
            )

            return stats

        except Exception as e:
            logger.warning(
                "Error retrieving Delta Lake table statistics",
                error=str(e),
                delta_path=self.delta_path,
            )
            return {}

    def compact_table(self) -> bool:
        """Compact Delta Lake table by removing duplicate group_ids.

        Keeps only the latest record for each group_id to reduce storage and improve performance.
        This should be run periodically (e.g., daily) to clean up duplicates from append mode.

        Returns:
            True if successful
        """
        try:
            from pathlib import Path as PathlibPath

            if not PathlibPath(self.delta_path).exists():
                logger.warning(
                    "Delta Lake table does not exist, skipping compaction",
                    delta_path=self.delta_path,
                )
                return False

            logger.info(
                "Starting Delta Lake table compaction",
                delta_path=self.delta_path,
            )

            # Read current data
            dt = DeltaTable(self.delta_path)
            df = dt.to_pandas()

            initial_rows = len(df)

            # Keep only latest record per group_id
            if 'group_id' in df.columns and 'timestamp' in df.columns:
                df_deduplicated = df.sort_values('timestamp').drop_duplicates(
                    subset=['group_id'],
                    keep='last'
                )

                removed_rows = initial_rows - len(df_deduplicated)

                if removed_rows > 0:
                    # Overwrite with deduplicated data
                    write_deltalake(
                        table_or_uri=str(self.delta_path),
                        data=df_deduplicated,
                        mode="overwrite",
                        engine="pyarrow",
                    )

                    logger.info(
                        "Delta Lake table compacted successfully",
                        delta_path=self.delta_path,
                        initial_rows=initial_rows,
                        final_rows=len(df_deduplicated),
                        removed_rows=removed_rows,
                    )
                else:
                    logger.info(
                        "No duplicates found, skipping compaction",
                        delta_path=self.delta_path,
                        row_count=initial_rows,
                    )
            else:
                logger.warning(
                    "Required columns not found for compaction",
                    delta_path=self.delta_path,
                    columns=list(df.columns),
                )
                return False

            return True

        except Exception as e:
            logger.error(
                "Error compacting Delta Lake table",
                error=str(e),
                error_type=type(e).__name__,
                delta_path=self.delta_path,
            )
            return False

