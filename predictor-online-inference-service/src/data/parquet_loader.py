"""
Parquet data loader for prediction features.

Loads features directly from parquet files instead of Feast online store.
"""

import logging
import pandas as pd
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ParquetFeatureLoader:
    """Loads prediction features from parquet files."""

    def __init__(self, root_path: str = ".."):
        """
        Initialize parquet feature loader.

        Args:
            root_path: Root path to the project (relative to predictor service)
        """
        self.root_path = Path(root_path)
        self.btc_features_path = self.root_path / "feast" / "offline_store" / "btc_features.parquet"
        self.semantic_groups_path = self.root_path / "feast" / "offline_store" / "semantic_groups.parquet"
        
        # Cache dataframes in memory for fast lookups
        self._btc_df: Optional[pd.DataFrame] = None
        self._semantic_groups_df: Optional[pd.DataFrame] = None
        
        logger.info(f"ParquetFeatureLoader initialized with root: {self.root_path}")
        logger.info(f"BTC features path: {self.btc_features_path}")
        logger.info(f"Semantic groups path: {self.semantic_groups_path}")

    def _load_btc_features(self) -> pd.DataFrame:
        """Load BTC features from parquet file (cached)."""
        if self._btc_df is None:
            logger.info(f"Loading BTC features from {self.btc_features_path}")
            self._btc_df = pd.read_parquet(self.btc_features_path)
            logger.info(f"Loaded BTC features: {self._btc_df.shape[0]} rows, {self._btc_df.shape[1]} columns")
        return self._btc_df

    def _load_semantic_groups(self) -> pd.DataFrame:
        """Load semantic groups features from parquet file (cached)."""
        if self._semantic_groups_df is None:
            logger.info(f"Loading semantic groups from {self.semantic_groups_path}")
            self._semantic_groups_df = pd.read_parquet(self.semantic_groups_path)
            logger.info(f"Loaded semantic groups: {self._semantic_groups_df.shape[0]} rows, {self._semantic_groups_df.shape[1]} columns")
        return self._semantic_groups_df

    def get_btc_features(self, timestamp: Optional[pd.Timestamp] = None) -> Dict[str, Any]:
        """
        Get BTC features for prediction.
        
        Args:
            timestamp: Optional timestamp to get features for. If None, uses latest.
            
        Returns:
            Dictionary with BTC feature values
        """
        try:
            df = self._load_btc_features()
            
            # Get the latest row or row closest to timestamp
            if timestamp is None:
                row = df.iloc[-1]  # Latest row
            else:
                # Find closest timestamp
                df['time_diff'] = abs(df['timestamp'] - timestamp)
                row = df.loc[df['time_diff'].idxmin()]
            
            # Return features as dict
            features = {
                'close': float(row['close']),
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'volume': float(row['volume']),
                'change_pct_10h': float(row['change_pct_10h']),
                'volatility_score': float(row['volatility_score']),
                'label_spike': int(row['label_spike']),
                'atr_14': float(row['atr_14']),
                'ema_slope_12': float(row['ema_slope_12']),
                'rsi_14': float(row['rsi_14']),
                'macd': float(row['macd']),
                'macd_signal': float(row['macd_signal']),
                'macd_histogram': float(row['macd_histogram']),
                'bb_width': float(row['bb_width']),
            }
            
            logger.debug(f"Retrieved BTC features for timestamp {row['timestamp']}")
            return features
            
        except Exception as e:
            logger.error(f"Failed to get BTC features: {e}")
            raise

    def get_semantic_group_features(self, group_id: str) -> Dict[str, Any]:
        """
        Get semantic group features for prediction.
        
        Args:
            group_id: Semantic group ID
            
        Returns:
            Dictionary with semantic group feature values
        """
        try:
            df = self._load_semantic_groups()
            
            # Find row with matching group_id
            row = df[df['group_id'] == group_id]
            
            if row.empty:
                raise ValueError(f"Group ID {group_id} not found in semantic groups")
            
            row = row.iloc[0]
            
            # Return all features as dict (excluding group_id and timestamp)
            features = row.to_dict()
            features.pop('group_id', None)
            features.pop('timestamp', None)
            
            # Convert numpy types to Python types
            features = {k: (int(v) if isinstance(v, (pd.Int64Dtype, pd.Int32Dtype)) or str(type(v)).startswith("<class 'numpy.int") 
                           else float(v) if str(type(v)).startswith("<class 'numpy.float") 
                           else v) 
                       for k, v in features.items()}
            
            logger.debug(f"Retrieved semantic group features for group_id {group_id}")
            return features
            
        except Exception as e:
            logger.error(f"Failed to get semantic group features for {group_id}: {e}")
            raise

    def reload_data(self):
        """Reload parquet files from disk (clears cache)."""
        logger.info("Reloading parquet data from disk")
        self._btc_df = None
        self._semantic_groups_df = None

