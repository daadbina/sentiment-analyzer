"""Delta Lake writer for ACID-compliant cluster storage."""

import logging
from datetime import datetime
from typing import List, Dict
import pandas as pd
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
            # Convert to DataFrame
            df = pd.DataFrame(clusters)

            # Add metadata columns
            df["written_at"] = datetime.utcnow().isoformat()
            df["version"] = 1

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

