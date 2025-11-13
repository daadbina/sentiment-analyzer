"""BTC features writer for saving historical BTC data with technical indicators."""

import logging
import pandas as pd
import os
from typing import List, Dict, Any
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class BtcFeaturesWriter:
    """Writer for BTC features parquet file."""

    def __init__(self, output_path: str = None):
        """Initialize BTC features writer.

        Args:
            output_path: Path to output parquet file (optional, defaults to centralized location)
        """
        if output_path is None:
            # Calculate path to centralized offline store (same pattern as FeastWriter)
            current_file = Path(__file__).resolve()
            # Go up from src/storage/btc_writer.py to feature-engineering-service
            repo_abs_path = current_file.parent.parent.parent
            # Go to repository root and then to feast/offline_store
            self.output_path = repo_abs_path.parent / "feast" / "offline_store" / "btc_features.parquet"
        else:
            self.output_path = Path(output_path)

        logger.info(f"BtcFeaturesWriter initialized: output_path={self.output_path}")

    def write_features(self, features_list: List[Dict[str, Any]]) -> None:
        """Write BTC features to parquet file.
        
        Args:
            features_list: List of feature dictionaries
        """
        if not features_list:
            logger.warning("No BTC features to write")
            return

        try:
            # Convert to DataFrame
            df = pd.DataFrame(features_list)
            
            # Ensure timestamp is datetime
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Sort by timestamp (most recent first)
            df = df.sort_values('timestamp', ascending=False)
            
            # Ensure output directory exists
            os.makedirs(self.output_path.parent, exist_ok=True)

            # Write to parquet
            df.to_parquet(str(self.output_path), index=False, engine='pyarrow')
            
            logger.info(
                f"✓ Wrote {len(df)} BTC feature records to {self.output_path} "
                f"(columns: {len(df.columns)}, "
                f"time_range: {df['timestamp'].min()} to {df['timestamp'].max()})"
            )
            
        except Exception as e:
            logger.error(f"Failed to write BTC features to parquet: {e}", exc_info=True)
            raise

    def read_features(self) -> pd.DataFrame:
        """Read BTC features from parquet file.

        Returns:
            DataFrame with BTC features
        """
        if not self.output_path.exists():
            logger.warning(f"BTC features file does not exist: {self.output_path}")
            return pd.DataFrame()

        try:
            df = pd.read_parquet(str(self.output_path))
            logger.info(f"Read {len(df)} BTC feature records from {self.output_path}")
            return df
        except Exception as e:
            logger.error(f"Failed to read BTC features from parquet: {e}", exc_info=True)
            raise

    def get_latest_timestamp(self) -> datetime:
        """Get the timestamp of the most recent BTC record.

        Returns:
            Latest timestamp or None if file doesn't exist
        """
        if not self.output_path.exists():
            return None

        try:
            df = pd.read_parquet(str(self.output_path), columns=['timestamp'])
            if len(df) > 0:
                return df['timestamp'].max()
            return None
        except Exception as e:
            logger.error(f"Failed to get latest timestamp: {e}")
            return None

    def close(self):
        """Close writer (no-op for parquet writer)."""
        pass

