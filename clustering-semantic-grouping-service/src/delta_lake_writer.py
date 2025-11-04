"""Delta Lake writer for ACID-compliant cluster storage."""

import logging
from datetime import datetime
from typing import List, Dict
import pandas as pd
import numpy as np
from deltalake import write_deltalake, DeltaTable

logger = logging.getLogger(__name__)


class DeltaLakeWriter:
    """Writes cluster data to Delta Lake with ACID guarantees."""

    def __init__(self, table_path: str = "/data/delta/semantic_groups"):
        """
        Initialize Delta Lake writer.

        Args:
            table_path: Path to Delta Lake table
        """
        self.table_path = table_path
        logger.info(f"Initialized DeltaLakeWriter: {table_path}")

    def _sanitize_clusters(self, clusters: List[Dict]) -> List[Dict]:
        """
        Sanitize cluster data to remove NULL values and ensure proper types.

        Args:
            clusters: List of cluster dictionaries

        Returns:
            Sanitized list of cluster dictionaries
        """
        sanitized = []
        for cluster in clusters:
            sanitized_cluster = {}
            for key, value in cluster.items():
                # Replace None with appropriate default values
                if value is None:
                    if isinstance(key, str):
                        if "id" in key or "label" in key or "model" in key or "algorithm" in key or "version" in key or "type" in key:
                            sanitized_cluster[key] = ""
                        elif "count" in key or "score" in key or "avg" in key or "min" in key or "max" in key or "std" in key:
                            sanitized_cluster[key] = 0.0
                        elif isinstance(value, list):
                            sanitized_cluster[key] = []
                        else:
                            sanitized_cluster[key] = ""
                    else:
                        sanitized_cluster[key] = ""
                # Handle lists with None values
                elif isinstance(value, list):
                    sanitized_cluster[key] = [v if v is not None else "" for v in value]
                # Handle dicts with None values
                elif isinstance(value, dict):
                    sanitized_cluster[key] = {k: (v if v is not None else "") for k, v in value.items()}
                else:
                    sanitized_cluster[key] = value
            sanitized.append(sanitized_cluster)
        return sanitized

    def write_clusters(
        self,
        clusters: List[Dict],
        mode: str = "append",
    ) -> bool:
        """
        Write clusters to Delta Lake.

        Args:
            clusters: List of cluster dictionaries
            mode: "append" or "overwrite"

        Returns:
            True if successful
        """
        if not clusters:
            logger.warning("No clusters to write")
            return False

        try:
            # Sanitize clusters to remove NULL values
            sanitized_clusters = self._sanitize_clusters(clusters)

            # Convert to DataFrame
            df = pd.DataFrame(sanitized_clusters)

            # Add metadata columns
            df["written_at"] = datetime.utcnow().isoformat()
            df["version"] = 1

            # Ensure no NULL values in DataFrame
            df = df.fillna("")

            # Replace NaN with empty string or 0 depending on column type
            for col in df.columns:
                if df[col].dtype == 'object':
                    df[col] = df[col].fillna("")
                elif df[col].dtype in ['float64', 'int64']:
                    df[col] = df[col].fillna(0)

            logger.debug(f"DataFrame dtypes:\n{df.dtypes}")
            logger.debug(f"DataFrame null counts:\n{df.isnull().sum()}")

            # Write to Delta Lake
            write_deltalake(
                self.table_path,
                df,
                mode=mode,
                overwrite_schema=False,
            )

            logger.info(
                f"Wrote {len(clusters)} clusters to Delta Lake "
                f"(mode: {mode}, path: {self.table_path})"
            )

            return True

        except Exception as e:
            logger.error(f"Error writing to Delta Lake: {e}", exc_info=True)
            return False

    def read_clusters(
        self,
        filters: Dict = None,
    ) -> pd.DataFrame:
        """
        Read clusters from Delta Lake.

        Args:
            filters: Optional filter conditions

        Returns:
            DataFrame of clusters
        """
        try:
            dt = DeltaTable(self.table_path)
            df = dt.to_pandas()

            logger.info(f"Read {len(df)} clusters from Delta Lake")

            return df

        except Exception as e:
            logger.error(f"Error reading from Delta Lake: {e}", exc_info=True)
            return pd.DataFrame()

    def get_table_version(self) -> int:
        """Get current version of Delta Lake table."""
        try:
            dt = DeltaTable(self.table_path)
            return dt.version()
        except Exception as e:
            logger.error(f"Error getting table version: {e}", exc_info=True)
            return -1

    def get_table_history(self, limit: int = 10) -> List[Dict]:
        """Get table history."""
        try:
            dt = DeltaTable(self.table_path)
            history = dt.history(limit=limit)
            return history
        except Exception as e:
            logger.error(f"Error getting table history: {e}", exc_info=True)
            return []

