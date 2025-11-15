"""
Parquet data loader for training features.

Loads features directly from parquet files instead of Feast.
"""

import logging
import pandas as pd
from pathlib import Path
from typing import Tuple, List
import numpy as np

logger = logging.getLogger(__name__)


class ParquetDataLoader:
    """Loads training data from parquet files."""

    def __init__(self, root_path: str = "."):
        """
        Initialize parquet data loader.

        Args:
            root_path: Root path to the project
        """
        self.root_path = Path(root_path)
        self.btc_features_path = self.root_path / "development" / "btc_price_prediction_dataset.parquet"
        self.semantic_groups_path = self.root_path / "development" / "conflict_prediction_training_data.parquet"
        logger.info(f"ParquetDataLoader initialized with root: {self.root_path}")

    def load_btc_features(self) -> pd.DataFrame:
        """
        Load BTC features from parquet file.

        Returns:
            DataFrame with BTC features
        """
        try:
            logger.info(f"Loading BTC features from {self.btc_features_path}")
            df = pd.read_parquet(self.btc_features_path)
            logger.info(f"Loaded BTC features: {df.shape[0]} rows, {df.shape[1]} columns")
            logger.info(f"Columns: {list(df.columns)}")
            return df
        except Exception as e:
            logger.error(f"Failed to load BTC features: {e}")
            raise

    def load_semantic_groups(self) -> pd.DataFrame:
        """
        Load semantic groups features from parquet file.

        Returns:
            DataFrame with semantic group features
        """
        try:
            logger.info(f"Loading semantic groups from {self.semantic_groups_path}")
            df = pd.read_parquet(self.semantic_groups_path)
            logger.info(f"Loaded semantic groups: {df.shape[0]} rows, {df.shape[1]} columns")
            logger.info(f"Columns: {list(df.columns)}")
            return df
        except Exception as e:
            logger.error(f"Failed to load semantic groups: {e}")
            raise

    def prepare_btc_training_data(self) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Prepare BTC training data for 10h percent change prediction.

        Uses technical indicators as features and change_pct_10h as target.

        Returns:
            Tuple of (features DataFrame, target Series)
        """
        try:
            df = self.load_btc_features()

            # Define feature columns (technical indicators)
            feature_cols = [
                'close', 'open', 'high', 'low', 'volume',
                'volatility_score', 'atr_14', 'ema_slope_12',
                'rsi_14', 'macd', 'macd_signal', 'macd_histogram', 'bb_width'
            ]

            # Target column
            target_col = 'change_pct_10h'

            # Filter to only rows with valid target
            df_valid = df[df[target_col].notna()].copy()

            logger.info(f"BTC data: {len(df_valid)} valid samples with target")
            logger.info(f"Target distribution: min={df_valid[target_col].min():.4f}, "
                       f"max={df_valid[target_col].max():.4f}, "
                       f"mean={df_valid[target_col].mean():.4f}, "
                       f"std={df_valid[target_col].std():.4f}")

            X = df_valid[feature_cols].copy()
            y = df_valid[target_col].copy()

            # Check for nulls
            null_counts = X.isnull().sum()
            if null_counts.sum() > 0:
                logger.warning(f"Found null values in features:\n{null_counts[null_counts > 0]}")
                # Fill nulls with median
                X = X.fillna(X.median())
                logger.info("Filled null values with median")

            logger.info(f"BTC training data prepared: X={X.shape}, y={y.shape}")
            return X, y

        except Exception as e:
            logger.error(f"Failed to prepare BTC training data: {e}")
            raise

    def prepare_conflict_training_data(self) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Prepare conflict prediction training data.

        Uses sentiment and entity features to predict conflict probability.
        Uses the has_conflict column from the parquet file as the label.

        IMPORTANT: Only uses reconciled groups (has_conflict IS NOT NULL).
        - has_conflict = True → conflict event (label=1)
        - has_conflict = False → non-conflict event (label=0)
        - has_conflict = None → unreconciled (EXCLUDED from training)

        Returns:
            Tuple of (features DataFrame, target Series)
        """
        try:
            df = self.load_semantic_groups()

            # Use the has_conflict column directly from the parquet file
            if 'has_conflict' not in df.columns:
                raise ValueError("has_conflict column not found in semantic_groups.parquet")

            # FILTER: Only use reconciled groups (has_conflict IS NOT NULL)
            df_reconciled = df[df['has_conflict'].notna()].copy()

            logger.info(f"Total groups: {len(df)}")
            logger.info(f"Reconciled groups (has_conflict IS NOT NULL): {len(df_reconciled)}")
            logger.info(f"Unreconciled groups (has_conflict IS NULL): {len(df) - len(df_reconciled)}")

            if len(df_reconciled) == 0:
                raise ValueError("No reconciled groups found for training. All groups have has_conflict=None.")

            # Extract number of countries from the countries column
            if 'countries' in df_reconciled.columns:
                # Countries are stored as comma-separated strings (e.g., "BG,CA,CN")
                # Count the number of countries by splitting on comma
                df_reconciled['num_countries'] = df_reconciled['countries'].apply(
                    lambda x: len(str(x).split(',')) if pd.notna(x) and str(x).strip() else 0
                )
                logger.info(f"Added num_countries feature: min={df_reconciled['num_countries'].min()}, "
                           f"max={df_reconciled['num_countries'].max()}, "
                           f"mean={df_reconciled['num_countries'].mean():.2f}")
            else:
                logger.warning("'countries' column not found in data, setting num_countries=0")
                df_reconciled['num_countries'] = 0

            # Define feature columns (semantic features)
            feature_cols = [
                'num_sources', 'source_credibility_avg', 'source_credibility_std',
                'source_diversity_score', 'time_span_hours', 'publication_velocity',
                'temporal_concentration', 'days_since_first_article',
                'sentiment_mean', 'sentiment_std', 'sentiment_polarity_ratio',
                'sentiment_volatility', 'entity_count', 'entity_diversity',
                'entity_prominence', 'entity_concentration', 'avg_word_count',
                'avg_title_length', 'language_diversity', 'domain_diversity',
                'centroid_magnitude', 'intra_cluster_similarity_mean',
                'intra_cluster_similarity_std', 'embedding_drift_score',
                'num_countries'  # Number of countries involved (derived from countries column)
            ]

            # Convert boolean has_conflict to int (0/1) for model training
            df_reconciled['conflict_label'] = df_reconciled['has_conflict'].astype(int)

            logger.info(f"Conflict labels: {df_reconciled['conflict_label'].value_counts().to_dict()}")
            logger.info(f"Conflict rate: {df_reconciled['conflict_label'].mean():.2%}")

            X = df_reconciled[feature_cols].copy()
            y = df_reconciled['conflict_label'].copy()

            # Check for nulls
            null_counts = X.isnull().sum()
            if null_counts.sum() > 0:
                logger.warning(f"Found null values in features:\n{null_counts[null_counts > 0]}")
                # Fill nulls with median for numeric, 0 for others
                X = X.fillna(X.median())
                logger.info("Filled null values with median")

            logger.info(f"Conflict training data prepared: X={X.shape}, y={y.shape}")
            return X, y

        except Exception as e:
            logger.error(f"Failed to prepare conflict training data: {e}")
            raise

