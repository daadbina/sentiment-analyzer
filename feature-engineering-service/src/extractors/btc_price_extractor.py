"""BTC price feature extractor for crypto-related semantic groups."""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
import numpy as np
from .base import FeatureExtractor, SemanticGroup, Article, Actor

logger = logging.getLogger(__name__)


class BtcPriceExtractor(FeatureExtractor):
    """Extract BTC price features from btc_truth table.
    
    Features extracted:
    - btc_change_pct_10h: Percentage change in BTC price over 10 hours
    - btc_volatility_score: Volatility score from btc_truth
    - btc_volume: Trading volume
    - btc_label_spike: Boolean indicating price spike
    
    Temporal alignment: Matches BTC data within ±1 hour of group creation time.
    """

    def __init__(self, postgres_client):
        """Initialize BTC price extractor.
        
        Args:
            postgres_client: PostgreSQL client for querying btc_truth table
        """
        super().__init__("btc_price")
        self.postgres_client = postgres_client
        self.features_extracted = [
            "btc_change_pct_10h",
            "btc_volatility_score",
            "btc_volume",
            "btc_label_spike",
            "btc_timestamp",
            "btc_close",
            "btc_atr_14",
            "btc_ema_slope_12",
            "btc_rsi_14",
            "btc_macd",
            "btc_macd_signal",
            "btc_macd_histogram",
            "btc_bb_width",
        ]
        self.temporal_window_hours = 1  # ±1 hour alignment window
        self.lookback_periods = 50  # Number of historical periods for indicators (need 35+ for MACD)
        
        logger.info(
            f"BtcPriceExtractor initialized: extractor={self.name}, "
            f"features={self.features_extracted}, temporal_window_hours={self.temporal_window_hours}"
        )

    async def extract(
        self,
        group: SemanticGroup,
        articles: List[Article],
        actors: List[Actor],
    ) -> Dict[str, Any]:
        """Extract BTC price features for semantic group.

        Args:
            group: Semantic group
            articles: Articles in group (not used for BTC features)
            actors: Actors mentioned in articles (not used for BTC features)

        Returns:
            Dictionary of BTC price features
        """
        logger.info("BTC extractor extract() method called")
        group_id = self.get_group_id(group)
        logger.info(f"BTC extractor processing group: {group_id}")

        # Get group creation timestamp
        logger.info("BTC extractor: Getting group timestamp")
        created_at = self._get_group_timestamp(group)
        logger.info(f"BTC extractor: Got timestamp: {created_at}")
        if not created_at:
            logger.warning(
                f"No timestamp found for group, using default BTC features: group_id={group_id}"
            )
            return self._get_default_features()

        # Query BTC data from btc_truth table with temporal alignment
        logger.info(f"BTC extractor: Fetching BTC data for timestamp: {created_at.isoformat()}")
        btc_data = await self._fetch_btc_data(created_at)
        logger.info(f"BTC extractor: Fetched BTC data: {btc_data}")

        if not btc_data:
            logger.debug(
                f"No BTC data found for group timestamp, using default features: group_id={group_id}, timestamp={created_at.isoformat()}"
            )
            return self._get_default_features()

        # Fetch historical data for technical indicators
        logger.info(f"Fetching historical BTC data for timestamp: {btc_data['timestamp']}")
        historical_data = await self._fetch_historical_btc_data(btc_data["timestamp"])
        logger.info(f"Historical BTC data fetched: {len(historical_data)} records")

        # Calculate technical indicators
        indicators = self._calculate_technical_indicators(historical_data)
        logger.info(f"Technical indicators calculated: {indicators}")

        # Extract features from BTC data
        # Note: btc_label_spike converted to int (0/1) for Avro schema compatibility
        features = {
            "btc_change_pct_10h": float(btc_data.get("change_pct_10h", 0.0)),
            "btc_volatility_score": float(btc_data.get("volatility_score", 0.0)),
            "btc_volume": float(btc_data.get("volume", 0.0)),
            "btc_label_spike": int(btc_data.get("label_spike", False)),  # Convert bool to int
            "btc_timestamp": btc_data["timestamp"].isoformat() if btc_data.get("timestamp") else created_at.isoformat(),
            "btc_close": float(btc_data.get("close", 0.0)),  # BTC close price
        }

        # Add technical indicators
        features.update(indicators)

        logger.info(
            f"BTC price features extracted: group_id={group_id}, timestamp={created_at.isoformat()}, "
            f"btc_change_pct_10h={features['btc_change_pct_10h']}, "
            f"btc_volatility_score={features['btc_volatility_score']}, "
            f"btc_volume={features['btc_volume']}, btc_label_spike={features['btc_label_spike']}, "
            f"btc_atr_14={features.get('btc_atr_14', 0.0)}, btc_rsi_14={features.get('btc_rsi_14', 0.0)}"
        )

        return features

    def _get_group_timestamp(self, group: SemanticGroup) -> Optional[datetime]:
        """Extract timestamp from semantic group.
        
        Args:
            group: Semantic group
            
        Returns:
            Datetime object or None
        """
        try:
            if isinstance(group, dict):
                created_at_str = group.get("created_at") or group.get("embed_created_at")
            else:
                created_at_str = getattr(group, "created_at", None) or getattr(group, "embed_created_at", None)
            
            if not created_at_str:
                return None
            
            # Parse ISO timestamp
            if isinstance(created_at_str, str):
                # Handle both with and without timezone
                created_at_str = created_at_str.replace("Z", "+00:00")
                dt = datetime.fromisoformat(created_at_str)
                # Ensure timezone-aware
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            elif isinstance(created_at_str, datetime):
                # Ensure timezone-aware
                if created_at_str.tzinfo is None:
                    created_at_str = created_at_str.replace(tzinfo=timezone.utc)
                return created_at_str

            return None
            
        except Exception as e:
            logger.error(
                f"Failed to parse group timestamp: {str(e)}",
                error_type=type(e).__name__
            )
            return None

    async def _fetch_btc_data(self, timestamp: datetime) -> Optional[Dict[str, Any]]:
        """Fetch BTC data from btc_truth table with temporal alignment.

        Args:
            timestamp: Group creation timestamp

        Returns:
            Dictionary of BTC data or None
        """
        try:
            # Calculate time window (±1 hour)
            start_time = timestamp - timedelta(hours=self.temporal_window_hours)
            end_time = timestamp + timedelta(hours=self.temporal_window_hours)

            # Convert to timezone-naive for PostgreSQL compatibility
            # (btc_truth.timestamp column is TIMESTAMP without timezone)
            start_time_naive = start_time.replace(tzinfo=None) if start_time.tzinfo else start_time
            end_time_naive = end_time.replace(tzinfo=None) if end_time.tzinfo else end_time
            timestamp_naive = timestamp.replace(tzinfo=None) if timestamp.tzinfo else timestamp

            # Query btc_truth table
            # Note: Using $1, $2, etc. placeholders for asyncpg
            # Filter for Bitcoin only (close > 10000) to exclude ETH and other coins
            query = """
                SELECT
                    change_pct_10h,
                    volatility_score,
                    volume,
                    label_spike,
                    timestamp,
                    close
                FROM btc_truth
                WHERE timestamp >= $1 AND timestamp <= $2
                AND close > 10000
                ORDER BY ABS(EXTRACT(EPOCH FROM (timestamp - $3)))
                LIMIT 1
            """

            # Execute query asynchronously
            result = await self.postgres_client.execute_query(
                query,
                start_time_naive,
                end_time_naive,
                timestamp_naive
            )

            if result and len(result) > 0:
                row = result[0]
                btc_data = {
                    "change_pct_10h": row["change_pct_10h"],
                    "volatility_score": row["volatility_score"],
                    "volume": row["volume"],
                    "label_spike": row["label_spike"],
                    "timestamp": row["timestamp"],
                    "close": row["close"]
                }

                logger.debug(
                    f"BTC data fetched from database: query_timestamp={timestamp.isoformat()}, "
                    f"btc_timestamp={row['timestamp'].isoformat() if row['timestamp'] else None}, btc_close={row['close']}"
                )

                return btc_data

            return None

        except Exception as e:
            logger.error(
                f"Failed to fetch BTC data: error_type={type(e).__name__}, timestamp={timestamp.isoformat()}, error={str(e)}"
            )
            return None

    def _get_default_features(self) -> Dict[str, Any]:
        """Get default BTC features when data is not available.

        Returns:
            Dictionary of default BTC features
        """
        return {
            "btc_change_pct_10h": 0.0,
            "btc_volatility_score": 0.0,
            "btc_volume": 0.0,
            "btc_label_spike": 0,  # int (0/1) for Avro schema compatibility
            "btc_timestamp": datetime.utcnow().isoformat(),
            "btc_close": 0.0,
            "btc_atr_14": 0.0,
            "btc_ema_slope_12": 0.0,
            "btc_rsi_14": 50.0,  # Neutral RSI
            "btc_macd": 0.0,
            "btc_macd_signal": 0.0,
            "btc_macd_histogram": 0.0,
            "btc_bb_width": 0.0,
        }

    async def _fetch_historical_btc_data(self, timestamp: datetime) -> List[Dict[str, Any]]:
        """Fetch historical BTC data for technical indicator calculation.

        Args:
            timestamp: Current timestamp

        Returns:
            List of historical BTC data points (OHLCV)
        """
        try:
            # Convert to timezone-naive for PostgreSQL compatibility
            # (btc_truth.timestamp column is TIMESTAMP without timezone)
            timestamp_naive = timestamp.replace(tzinfo=None) if timestamp.tzinfo else timestamp

            # Fetch last N periods before timestamp
            # Filter for Bitcoin only (close > 10000) to exclude ETH and other coins
            query = """
                SELECT
                    timestamp,
                    open,
                    high,
                    low,
                    close,
                    volume
                FROM btc_truth
                WHERE timestamp <= $1
                AND close > 10000
                ORDER BY timestamp DESC
                LIMIT $2
            """

            result = await self.postgres_client.execute_query(
                query,
                timestamp_naive,
                self.lookback_periods
            )

            if not result or len(result) < 2:
                logger.warning(
                    f"Insufficient historical BTC data for indicators: timestamp={timestamp.isoformat()}, rows={len(result) if result else 0}"
                )
                return []

            # Reverse to chronological order (oldest first)
            return list(reversed(result))

        except Exception as e:
            logger.error(
                f"Failed to fetch historical BTC data: error_type={type(e).__name__}, timestamp={timestamp.isoformat()}, error={str(e)}"
            )
            return []

    def _calculate_technical_indicators(self, historical_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate technical indicators from historical BTC data.

        Args:
            historical_data: List of OHLCV data points

        Returns:
            Dictionary of technical indicators
        """
        if not historical_data or len(historical_data) < 14:
            # Not enough data for indicators
            return {
                "btc_atr_14": 0.0,
                "btc_ema_slope_12": 0.0,
                "btc_rsi_14": 50.0,
                "btc_macd": 0.0,
                "btc_macd_signal": 0.0,
                "btc_macd_histogram": 0.0,
                "btc_bb_width": 0.0,
            }

        try:
            # Extract price arrays
            closes = np.array([d["close"] for d in historical_data])
            highs = np.array([d["high"] for d in historical_data])
            lows = np.array([d["low"] for d in historical_data])

            # ATR (Average True Range) - 14 period
            atr_14 = self._calculate_atr(highs, lows, closes, period=14)

            # EMA Slope - 12 period
            ema_slope_12 = self._calculate_ema_slope(closes, period=12)

            # RSI (Relative Strength Index) - 14 period
            rsi_14 = self._calculate_rsi(closes, period=14)

            # MACD (Moving Average Convergence Divergence)
            macd, macd_signal, macd_histogram = self._calculate_macd(closes)

            # Bollinger Bands Width - 20 period
            bb_width = self._calculate_bb_width(closes, period=20)

            return {
                "btc_atr_14": float(atr_14),
                "btc_ema_slope_12": float(ema_slope_12),
                "btc_rsi_14": float(rsi_14),
                "btc_macd": float(macd),
                "btc_macd_signal": float(macd_signal),
                "btc_macd_histogram": float(macd_histogram),
                "btc_bb_width": float(bb_width),
            }

        except Exception as e:
            logger.error(
                f"Failed to calculate technical indicators: error_type={type(e).__name__}, error={str(e)}"
            )
            return {
                "btc_atr_14": 0.0,
                "btc_ema_slope_12": 0.0,
                "btc_rsi_14": 50.0,
                "btc_macd": 0.0,
                "btc_macd_signal": 0.0,
                "btc_macd_histogram": 0.0,
                "btc_bb_width": 0.0,
            }

    def _calculate_atr(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> float:
        """Calculate Average True Range (ATR).

        Args:
            highs: Array of high prices
            lows: Array of low prices
            closes: Array of close prices
            period: ATR period (default 14)

        Returns:
            ATR value
        """
        if len(closes) < period + 1:
            return 0.0

        # True Range = max(high - low, abs(high - prev_close), abs(low - prev_close))
        tr = np.maximum(
            highs[1:] - lows[1:],
            np.maximum(
                np.abs(highs[1:] - closes[:-1]),
                np.abs(lows[1:] - closes[:-1])
            )
        )

        # ATR is the moving average of TR
        atr = np.mean(tr[-period:])
        return atr

    def _calculate_ema_slope(self, closes: np.ndarray, period: int = 12) -> float:
        """Calculate EMA slope (rate of change).

        Args:
            closes: Array of close prices
            period: EMA period (default 12)

        Returns:
            EMA slope (percentage change per period)
        """
        if len(closes) < period + 1:
            return 0.0

        # Calculate EMA
        alpha = 2 / (period + 1)
        ema = np.zeros(len(closes))
        ema[0] = closes[0]

        for i in range(1, len(closes)):
            ema[i] = alpha * closes[i] + (1 - alpha) * ema[i - 1]

        # Slope = (current EMA - previous EMA) / previous EMA * 100
        if ema[-2] != 0:
            slope = (ema[-1] - ema[-2]) / ema[-2] * 100
        else:
            slope = 0.0

        return slope

    def _calculate_rsi(self, closes: np.ndarray, period: int = 14) -> float:
        """Calculate Relative Strength Index (RSI).

        Args:
            closes: Array of close prices
            period: RSI period (default 14)

        Returns:
            RSI value (0-100)
        """
        if len(closes) < period + 1:
            return 50.0  # Neutral

        # Calculate price changes
        deltas = np.diff(closes)

        # Separate gains and losses
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        # Calculate average gains and losses
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])

        # Calculate RS and RSI
        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def _calculate_macd(self, closes: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple:
        """Calculate MACD (Moving Average Convergence Divergence).

        Args:
            closes: Array of close prices
            fast: Fast EMA period (default 12)
            slow: Slow EMA period (default 26)
            signal: Signal line period (default 9)

        Returns:
            Tuple of (MACD, Signal, Histogram)
        """
        if len(closes) < slow + signal:
            logger.debug(f"Insufficient data for MACD: need {slow + signal}, have {len(closes)}")
            return 0.0, 0.0, 0.0

        # Calculate fast and slow EMAs
        alpha_fast = 2 / (fast + 1)
        alpha_slow = 2 / (slow + 1)

        ema_fast = np.zeros(len(closes))
        ema_slow = np.zeros(len(closes))
        ema_fast[0] = closes[0]
        ema_slow[0] = closes[0]

        for i in range(1, len(closes)):
            ema_fast[i] = alpha_fast * closes[i] + (1 - alpha_fast) * ema_fast[i - 1]
            ema_slow[i] = alpha_slow * closes[i] + (1 - alpha_slow) * ema_slow[i - 1]

        # MACD line
        macd_line = ema_fast - ema_slow

        # Signal line (EMA of MACD)
        alpha_signal = 2 / (signal + 1)
        signal_line = np.zeros(len(macd_line))
        signal_line[0] = macd_line[0]

        for i in range(1, len(macd_line)):
            signal_line[i] = alpha_signal * macd_line[i] + (1 - alpha_signal) * signal_line[i - 1]

        # Histogram
        histogram = macd_line - signal_line

        return macd_line[-1], signal_line[-1], histogram[-1]

    def _calculate_bb_width(self, closes: np.ndarray, period: int = 20, num_std: float = 2.0) -> float:
        """Calculate Bollinger Bands Width.

        Args:
            closes: Array of close prices
            period: BB period (default 20)
            num_std: Number of standard deviations (default 2.0)

        Returns:
            BB width as percentage of middle band
        """
        if len(closes) < period:
            return 0.0

        # Calculate middle band (SMA)
        sma = np.mean(closes[-period:])

        # Calculate standard deviation
        std = np.std(closes[-period:])

        # Upper and lower bands
        upper_band = sma + (num_std * std)
        lower_band = sma - (num_std * std)

        # Width as percentage of middle band
        if sma != 0:
            width = ((upper_band - lower_band) / sma) * 100
        else:
            width = 0.0

        return width

    async def generate_historical_btc_features(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """Generate BTC features for historical data.

        Fetches the last N BTC records from btc_truth table and calculates
        all technical indicators for each record.

        Args:
            limit: Number of historical records to fetch

        Returns:
            List of feature dictionaries with all BTC features
        """
        logger.info(f"Generating historical BTC features for last {limit} records")

        # Fetch historical BTC data
        query = """
            SELECT
                timestamp,
                close,
                open,
                high,
                low,
                volume,
                change_pct_10h,
                volatility_score,
                label_spike
            FROM btc_truth
            WHERE close > 10000  -- Filter for Bitcoin only
            ORDER BY timestamp DESC
            LIMIT $1
        """

        result = await self.postgres_client.execute_query(query, limit)

        if not result:
            logger.warning("No BTC records found in database")
            return []

        logger.info(f"Fetched {len(result)} BTC records from database")

        # Reverse to chronological order and convert to dicts
        btc_records = [dict(record) for record in reversed(result)]

        features_list = []

        for i, record_dict in enumerate(btc_records):
            # Get historical data for this record (all records up to and including this one)
            historical_data = btc_records[:i+1]

            # Base features from database
            features = {
                "timestamp": record_dict["timestamp"].isoformat() if hasattr(record_dict["timestamp"], 'isoformat') else str(record_dict["timestamp"]),
                "close": float(record_dict.get("close", 0) or 0),
                "open": float(record_dict.get("open", 0) or 0),
                "high": float(record_dict.get("high", 0) or 0),
                "low": float(record_dict.get("low", 0) or 0),
                "volume": float(record_dict.get("volume", 0) or 0),
                "change_pct_10h": float(record_dict.get("change_pct_10h", 0) or 0),
                "volatility_score": float(record_dict.get("volatility_score", 0) or 0),
                "label_spike": int(record_dict.get("label_spike", False) or False),
            }

            # Calculate technical indicators
            # Extract price arrays from historical data
            closes = np.array([d["close"] for d in historical_data])
            highs = np.array([d.get("high", d["close"]) for d in historical_data])
            lows = np.array([d.get("low", d["close"]) for d in historical_data])

            if len(historical_data) >= 14:
                features["atr_14"] = float(self._calculate_atr(highs, lows, closes, period=14))
            else:
                features["atr_14"] = 0.0

            if len(historical_data) >= 12:
                features["ema_slope_12"] = float(self._calculate_ema_slope(closes, period=12))
            else:
                features["ema_slope_12"] = 0.0

            if len(historical_data) >= 14:
                features["rsi_14"] = float(self._calculate_rsi(closes, period=14))
            else:
                features["rsi_14"] = 0.0

            if len(historical_data) >= 35:
                macd_line, signal_line, histogram = self._calculate_macd(closes)
                features["macd"] = float(macd_line)
                features["macd_signal"] = float(signal_line)
                features["macd_histogram"] = float(histogram)
            else:
                features["macd"] = 0.0
                features["macd_signal"] = 0.0
                features["macd_histogram"] = 0.0

            if len(historical_data) >= 20:
                features["bb_width"] = float(self._calculate_bb_width(closes, period=20))
            else:
                features["bb_width"] = 0.0

            features_list.append(features)

            if (i + 1) % 100 == 0:
                logger.info(f"Processed {i + 1}/{len(btc_records)} BTC records")

        logger.info(f"Generated features for {len(features_list)} BTC records")
        return features_list

