"""
BTC Feature Builder for Predictor Service.

Builds 17 BTC features for BTC prediction models:
- 4 features from feature-engineering-service (via Redis)
- 13 features calculated from btc_truth table

This matches the feature set used during BTC model training.
"""

import logging
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from ..clients.postgres_client import PostgresClient

logger = logging.getLogger(__name__)


class BtcFeatureBuilder:
    """
    Build BTC features for prediction.

    Combines features from feature-engineering-service with features
    calculated from btc_truth table to create the 17-feature vector
    expected by BTC prediction models.
    """

    def __init__(self, postgres_client: PostgresClient, parquet_loader: Optional[Any] = None):
        """
        Initialize BTC feature builder.

        Args:
            postgres_client: PostgreSQL client for btc_truth queries
            parquet_loader: Optional ParquetFeatureLoader for fallback BTC data
        """
        self.postgres_client = postgres_client
        self.parquet_loader = parquet_loader

        # Cache for BTC parquet dataframe
        self._btc_parquet_df: Optional[pd.DataFrame] = None
        self._btc_parquet_path = Path(__file__).parent.parent.parent.parent / "feast" / "offline_store" / "btc_features.parquet"

        logger.info("Initialized BTC feature builder")
        if parquet_loader:
            logger.info("BTC feature builder has parquet loader for fallback")
        else:
            logger.info(f"BTC feature builder will use direct parquet access: {self._btc_parquet_path}")

    async def build_btc_features(
        self,
        general_features: dict[str, Any],
        timestamp: datetime | None = None,
    ) -> dict[str, Any]:
        """
        Build 17 BTC features for prediction.

        Extracts 4 BTC features from general_features (from feature-engineering):
        - btc_change_pct_10h (backward)
        - btc_volatility_score
        - btc_volume
        - btc_label_spike

        Calculates 13 additional features from btc_truth table:
        - btc_close, btc_high, btc_low, btc_open (price OHLC)
        - btc_price_range_pct, btc_body_size_pct, btc_close_position_in_range, btc_is_bullish
        - btc_change_pct_10h_backward, btc_momentum_strength
        - btc_hour_sin, btc_hour_cos, btc_day_sin, btc_day_cos

        Args:
            general_features: Features from feature-engineering-service (28 features)
            timestamp: Timestamp for BTC data lookup (defaults to current time)

        Returns:
            Dictionary with 17 BTC features
        """
        try:
            # Use provided timestamp or current time
            if timestamp is None:
                timestamp = datetime.utcnow()

            logger.info(
                f"Building BTC features: timestamp={timestamp.isoformat()}, "
                f"general_feature_count={len(general_features)}"
            )

            # Extract 4 BTC features from feature-engineering-service
            # Remove the "semantic_group_features:" prefix if present
            btc_volume_raw = general_features.get("semantic_group_features:btc_volume") or general_features.get("btc_volume", 0.0)
            btc_volatility = general_features.get("semantic_group_features:btc_volatility_score") or general_features.get("btc_volatility_score", 0.0)
            btc_label_spike = general_features.get("semantic_group_features:btc_label_spike") or general_features.get("btc_label_spike", 0)
            btc_change_backward = general_features.get("semantic_group_features:btc_change_pct_10h") or general_features.get("btc_change_pct_10h", 0.0)

            # ============================================================================
            # TEMPORARY WORKAROUND: Fallback to BTC parquet file when features are zero
            # This compensates for the feature-engineering-service bug where 31% of
            # semantic groups have zero BTC features due to failed timestamp joins.
            # TODO: Remove this once feature-engineering-service is fixed to properly
            # join BTC features using time-window matching instead of exact timestamps.
            # ============================================================================
            if btc_volume_raw == 0.0 and btc_volatility == 0.0 and btc_change_backward == 0.0:
                logger.warning(
                    f"BTC features are all zero (likely missing from semantic_groups.parquet). "
                    f"Attempting fallback to btc_features.parquet for timestamp={timestamp.isoformat()}"
                )

                # Try to fetch from parquet file
                parquet_features = self._fetch_from_btc_parquet(timestamp)
                if parquet_features:
                    btc_volume_raw = parquet_features.get('volume', 0.0)
                    btc_volatility = parquet_features.get('volatility_score', 0.0)
                    btc_change_backward = parquet_features.get('change_pct_10h', 0.0)
                    btc_label_spike = parquet_features.get('label_spike', 0)

                    logger.info(
                        f"Successfully fetched BTC features from parquet fallback: "
                        f"volume={btc_volume_raw}, volatility={btc_volatility}, "
                        f"change_pct_10h={btc_change_backward}"
                    )
                else:
                    logger.warning(
                        f"Fallback to btc_features.parquet failed. "
                        f"Will proceed with zeros (may impact prediction quality)."
                    )
            # ============================================================================

            # Fetch BTC OHLC data from btc_truth table
            # Get the most recent BTC record at or before the timestamp
            query = """
                SELECT
                    open,
                    high,
                    low,
                    close,
                    volume,
                    timestamp
                FROM btc_truth
                WHERE timestamp <= $1
                AND event_id LIKE 'binance_BTCUSDT_%'
                ORDER BY timestamp DESC
                LIMIT 1
            """

            row = await self.postgres_client.fetch_one(query, timestamp)

            if not row:
                logger.warning(
                    f"No BTC data found in btc_truth table: timestamp={timestamp.isoformat()}"
                )

                # ============================================================================
                # TEMPORARY WORKAROUND: Try to get OHLC data from parquet as fallback
                # ============================================================================
                parquet_features = self._fetch_from_btc_parquet(timestamp)
                if parquet_features:
                    logger.info("Using BTC OHLC data from parquet fallback (btc_truth table empty)")
                    return self._build_features_from_parquet(
                        parquet_features,
                        btc_volume_raw,
                        btc_volatility,
                        btc_label_spike,
                        btc_change_backward,
                        timestamp,
                    )
                # ============================================================================

                # Return features with zeros for missing data
                return self._build_default_features(
                    btc_volume_raw,
                    btc_volatility,
                    btc_label_spike,
                    btc_change_backward,
                    timestamp,
                )

            # Extract OHLC prices
            open_price = float(row['open']) if row['open'] is not None else 0.0
            high_price = float(row['high']) if row['high'] is not None else 0.0
            low_price = float(row['low']) if row['low'] is not None else 0.0
            close_price = float(row['close']) if row['close'] is not None else 0.0
            db_timestamp = row['timestamp']

            logger.info(
                f"Fetched BTC OHLC data: timestamp={db_timestamp.isoformat()}, "
                f"close={close_price}, high={high_price}, low={low_price}, open={open_price}"
            )

            # Calculate derived features (same as trainer service)
            price_range_pct = ((high_price - low_price) / close_price * 100.0) if close_price > 0 and high_price > low_price else 0.0
            body_size_pct = (abs(close_price - open_price) / close_price * 100.0) if close_price > 0 else 0.0
            is_bullish = 1 if close_price > open_price else 0

            # Price position in range
            price_range = high_price - low_price if high_price > low_price else 0.0
            close_position_in_range = ((close_price - low_price) / price_range) if price_range > 0 else 0.5

            # Momentum features
            momentum_strength = abs(btc_change_backward)

            # Volume normalization (same as trainer)
            volume_normalized = btc_volume_raw / 1000000.0 if btc_volume_raw > 0 else 0.0

            # Cyclical time encoding
            hour_sin = math.sin(2 * math.pi * db_timestamp.hour / 24)
            hour_cos = math.cos(2 * math.pi * db_timestamp.hour / 24)
            day_sin = math.sin(2 * math.pi * db_timestamp.weekday() / 7)
            day_cos = math.cos(2 * math.pi * db_timestamp.weekday() / 7)

            # Build 17-feature vector (same order as trainer)
            btc_features = {
                # Core price features (4)
                'btc_close': close_price,
                'btc_high': high_price,
                'btc_low': low_price,
                'btc_open': open_price,
                # Key derived features (4)
                'btc_price_range_pct': price_range_pct,
                'btc_body_size_pct': body_size_pct,
                'btc_close_position_in_range': close_position_in_range,
                'btc_is_bullish': is_bullish,
                # Momentum features (2)
                'btc_change_pct_10h_backward': btc_change_backward,
                'btc_momentum_strength': momentum_strength,
                # Volume and volatility (3)
                'btc_volume': volume_normalized,
                'btc_volatility_score': btc_volatility,
                'btc_label_spike': int(btc_label_spike),
                # Cyclical time features (4)
                'btc_hour_sin': hour_sin,
                'btc_hour_cos': hour_cos,
                'btc_day_sin': day_sin,
                'btc_day_cos': day_cos,
            }

            logger.info(
                f"Built BTC features successfully: feature_count={len(btc_features)}, "
                f"sample_features={dict(list(btc_features.items())[:5])}"
            )

            return btc_features

        except Exception as e:
            logger.error(f"Failed to build BTC features: {e}", exc_info=True)
            # Return default features on error
            return self._build_default_features(
                btc_volume_raw if 'btc_volume_raw' in locals() else 0.0,
                btc_volatility if 'btc_volatility' in locals() else 0.0,
                btc_label_spike if 'btc_label_spike' in locals() else 0,
                btc_change_backward if 'btc_change_backward' in locals() else 0.0,
                timestamp,
            )

    def _fetch_from_btc_parquet(self, timestamp: datetime) -> Optional[dict[str, Any]]:
        """
        TEMPORARY WORKAROUND: Fetch BTC features from parquet file as fallback.

        This method loads BTC features directly from the btc_features.parquet file
        when the semantic_groups.parquet file has zero values (due to failed joins
        in the feature-engineering-service).

        Args:
            timestamp: Timestamp to find nearest BTC data for

        Returns:
            Dictionary with BTC features from parquet, or None if unavailable
        """
        try:
            # Load BTC parquet file (cached)
            if self._btc_parquet_df is None:
                if not self._btc_parquet_path.exists():
                    logger.warning(f"BTC parquet file not found: {self._btc_parquet_path}")
                    return None

                logger.info(f"Loading BTC features from parquet: {self._btc_parquet_path}")
                self._btc_parquet_df = pd.read_parquet(self._btc_parquet_path)
                logger.info(f"Loaded {len(self._btc_parquet_df)} BTC records from parquet")

            df = self._btc_parquet_df

            # Convert timestamp to pandas Timestamp for comparison
            pd_timestamp = pd.Timestamp(timestamp)

            # Find the closest timestamp (within 2 hours window)
            df['time_diff'] = abs(df['timestamp'] - pd_timestamp)
            closest_idx = df['time_diff'].idxmin()
            closest_row = df.loc[closest_idx]

            # Check if the closest timestamp is within acceptable range (2 hours)
            time_diff_hours = closest_row['time_diff'].total_seconds() / 3600
            if time_diff_hours > 2.0:
                logger.warning(
                    f"Closest BTC data is {time_diff_hours:.1f} hours away from target timestamp. "
                    f"Target: {timestamp.isoformat()}, Closest: {closest_row['timestamp']}"
                )

            # Extract features from parquet row
            features = {
                'close': float(closest_row['close']),
                'open': float(closest_row['open']),
                'high': float(closest_row['high']),
                'low': float(closest_row['low']),
                'volume': float(closest_row['volume']),
                'change_pct_10h': float(closest_row['change_pct_10h']),
                'volatility_score': float(closest_row['volatility_score']),
                'label_spike': int(closest_row['label_spike']),
                'atr_14': float(closest_row['atr_14']),
                'ema_slope_12': float(closest_row['ema_slope_12']),
                'rsi_14': float(closest_row['rsi_14']),
                'macd': float(closest_row['macd']),
                'macd_signal': float(closest_row['macd_signal']),
                'macd_histogram': float(closest_row['macd_histogram']),
                'bb_width': float(closest_row['bb_width']),
                'timestamp': closest_row['timestamp'],
            }

            logger.debug(
                f"Fetched BTC features from parquet: timestamp={closest_row['timestamp']}, "
                f"close={features['close']}, volume={features['volume']}"
            )

            return features

        except Exception as e:
            logger.error(f"Failed to fetch BTC features from parquet: {e}", exc_info=True)
            return None

    def _build_features_from_parquet(
        self,
        parquet_features: dict[str, Any],
        btc_volume_raw: float,
        btc_volatility: float,
        btc_label_spike: int,
        btc_change_backward: float,
        timestamp: datetime,
    ) -> dict[str, Any]:
        """
        TEMPORARY WORKAROUND: Build BTC features using OHLC from parquet file.

        This method builds the full 17-feature vector using OHLC data from the
        btc_features.parquet file when btc_truth table is empty.

        Args:
            parquet_features: Features fetched from btc_features.parquet
            btc_volume_raw: Volume (from parquet or feature-engineering)
            btc_volatility: Volatility score (from parquet or feature-engineering)
            btc_label_spike: Label spike (from parquet or feature-engineering)
            btc_change_backward: Backward change (from parquet or feature-engineering)
            timestamp: Timestamp for cyclical encoding

        Returns:
            Dictionary with 17 BTC features built from parquet data
        """
        # Extract OHLC from parquet
        open_price = parquet_features.get('open', 0.0)
        high_price = parquet_features.get('high', 0.0)
        low_price = parquet_features.get('low', 0.0)
        close_price = parquet_features.get('close', 0.0)
        parquet_timestamp = parquet_features.get('timestamp', timestamp)

        # Use parquet values if the feature-engineering values are zero
        if btc_volume_raw == 0.0:
            btc_volume_raw = parquet_features.get('volume', 0.0)
        if btc_volatility == 0.0:
            btc_volatility = parquet_features.get('volatility_score', 0.0)
        if btc_change_backward == 0.0:
            btc_change_backward = parquet_features.get('change_pct_10h', 0.0)
        if btc_label_spike == 0:
            btc_label_spike = parquet_features.get('label_spike', 0)

        # Calculate derived features (same as main flow)
        price_range_pct = ((high_price - low_price) / close_price * 100.0) if close_price > 0 and high_price > low_price else 0.0
        body_size_pct = (abs(close_price - open_price) / close_price * 100.0) if close_price > 0 else 0.0
        is_bullish = 1 if close_price > open_price else 0

        # Price position in range
        price_range = high_price - low_price if high_price > low_price else 0.0
        close_position_in_range = ((close_price - low_price) / price_range) if price_range > 0 else 0.5

        # Momentum features
        momentum_strength = abs(btc_change_backward)

        # Volume normalization
        volume_normalized = btc_volume_raw / 1000000.0 if btc_volume_raw > 0 else 0.0

        # Cyclical time encoding (use parquet timestamp if available)
        if isinstance(parquet_timestamp, pd.Timestamp):
            parquet_timestamp = parquet_timestamp.to_pydatetime()

        hour_sin = math.sin(2 * math.pi * parquet_timestamp.hour / 24)
        hour_cos = math.cos(2 * math.pi * parquet_timestamp.hour / 24)
        day_sin = math.sin(2 * math.pi * parquet_timestamp.weekday() / 7)
        day_cos = math.cos(2 * math.pi * parquet_timestamp.weekday() / 7)

        # Build 17-feature vector
        return {
            # Core price features (4)
            'btc_close': close_price,
            'btc_high': high_price,
            'btc_low': low_price,
            'btc_open': open_price,
            # Key derived features (4)
            'btc_price_range_pct': price_range_pct,
            'btc_body_size_pct': body_size_pct,
            'btc_close_position_in_range': close_position_in_range,
            'btc_is_bullish': is_bullish,
            # Momentum features (2)
            'btc_change_pct_10h_backward': btc_change_backward,
            'btc_momentum_strength': momentum_strength,
            # Volume and volatility (3)
            'btc_volume': volume_normalized,
            'btc_volatility_score': btc_volatility,
            'btc_label_spike': int(btc_label_spike),
            # Cyclical time features (4)
            'btc_hour_sin': hour_sin,
            'btc_hour_cos': hour_cos,
            'btc_day_sin': day_sin,
            'btc_day_cos': day_cos,
        }

    def _build_default_features(
        self,
        btc_volume: float,
        btc_volatility: float,
        btc_label_spike: int,
        btc_change_backward: float,
        timestamp: datetime,
    ) -> dict[str, Any]:
        """
        Build default BTC features when btc_truth data is unavailable.

        Args:
            btc_volume: Volume from feature-engineering
            btc_volatility: Volatility score from feature-engineering
            btc_label_spike: Label spike from feature-engineering
            btc_change_backward: Backward change from feature-engineering
            timestamp: Timestamp for cyclical encoding

        Returns:
            Dictionary with 17 BTC features (with zeros for missing data)
        """
        # Cyclical time encoding
        hour_sin = math.sin(2 * math.pi * timestamp.hour / 24)
        hour_cos = math.cos(2 * math.pi * timestamp.hour / 24)
        day_sin = math.sin(2 * math.pi * timestamp.weekday() / 7)
        day_cos = math.cos(2 * math.pi * timestamp.weekday() / 7)

        volume_normalized = btc_volume / 1000000.0 if btc_volume > 0 else 0.0
        momentum_strength = abs(btc_change_backward)

        return {
            # Core price features (zeros when unavailable)
            'btc_close': 0.0,
            'btc_high': 0.0,
            'btc_low': 0.0,
            'btc_open': 0.0,
            # Key derived features (zeros when unavailable)
            'btc_price_range_pct': 0.0,
            'btc_body_size_pct': 0.0,
            'btc_close_position_in_range': 0.5,
            'btc_is_bullish': 0,
            # Momentum features
            'btc_change_pct_10h_backward': btc_change_backward,
            'btc_momentum_strength': momentum_strength,
            # Volume and volatility
            'btc_volume': volume_normalized,
            'btc_volatility_score': btc_volatility,
            'btc_label_spike': int(btc_label_spike),
            # Cyclical time features
            'btc_hour_sin': hour_sin,
            'btc_hour_cos': hour_cos,
            'btc_day_sin': day_sin,
            'btc_day_cos': day_cos,
        }

