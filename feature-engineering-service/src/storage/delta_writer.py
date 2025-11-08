"""Delta Lake writer for offline features."""

from typing import Dict, Any
from pathlib import Path
import pandas as pd
from datetime import datetime
import pytz
from deltalake import write_deltalake
from ..utils import StructuredLogger
from ..exceptions import FeastWriteError
from ..config import config

logger = StructuredLogger(__name__)


class DeltaLakeWriter:
    """Write features to Delta Lake offline store."""

    def __init__(self, delta_path: str = "/data/delta/semantic_groups"):
        """Initialize Delta Lake writer.
        
        Args:
            delta_path: Path to Delta Lake table
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
        """Write features to Delta Lake.

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

            logger.debug(
                "Prepared feature DataFrame for Delta Lake write",
                group_id=group_id,
                feature_count=len(features),
                columns=list(df.columns),
            )

            # Write to Delta Lake
            # Use mode='append' to add to existing table or create new one
            write_deltalake(
                table_or_uri=str(self.delta_path),
                data=df,
                mode="append",
                engine="rust",
            )

            logger.info(
                "Features written to Delta Lake",
                group_id=group_id,
                feature_count=len(features),
                delta_path=self.delta_path,
                timestamp=timestamp,
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

        Args:
            group_id: Semantic group ID

        Returns:
            Feature dictionary
        """
        try:
            # Read from Delta Lake
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
            
            # Get latest record (by timestamp)
            latest = group_df.sort_values("timestamp").iloc[-1]
            
            logger.info(
                "Features read from Delta Lake",
                group_id=group_id,
                delta_path=self.delta_path,
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
            df = pd.read_parquet(str(self.delta_path))
            
            stats = {
                "row_count": len(df),
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

