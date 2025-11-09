"""BTC price feature extractor for crypto-related semantic groups."""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
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
        ]
        self.temporal_window_hours = 1  # ±1 hour alignment window
        
        logger.info(
            f"BtcPriceExtractor initialized: extractor={self.name}, "
            f"features={self.features_extracted}, temporal_window_hours={self.temporal_window_hours}"
        )

    def extract(
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
        group_id = self.get_group_id(group)
        
        # Get group creation timestamp
        created_at = self._get_group_timestamp(group)
        if not created_at:
            logger.warning(
                "No timestamp found for group, using default BTC features",
                group_id=group_id
            )
            return self._get_default_features()
        
        # Query BTC data from btc_truth table with temporal alignment
        btc_data = self._fetch_btc_data(created_at)
        
        if not btc_data:
            logger.debug(
                "No BTC data found for group timestamp, using default features",
                group_id=group_id,
                timestamp=created_at.isoformat()
            )
            return self._get_default_features()
        
        # Extract features from BTC data
        features = {
            "btc_change_pct_10h": float(btc_data.get("change_pct_10h", 0.0)),
            "btc_volatility_score": float(btc_data.get("volatility_score", 0.0)),
            "btc_volume": float(btc_data.get("volume", 0.0)),
            "btc_label_spike": bool(btc_data.get("label_spike", False)),
        }
        
        logger.info(
            f"BTC price features extracted: group_id={group_id}, timestamp={created_at.isoformat()}, "
            f"btc_change_pct_10h={features['btc_change_pct_10h']}, "
            f"btc_volatility_score={features['btc_volatility_score']}, "
            f"btc_volume={features['btc_volume']}, btc_label_spike={features['btc_label_spike']}"
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
                return datetime.fromisoformat(created_at_str)
            elif isinstance(created_at_str, datetime):
                return created_at_str
            
            return None
            
        except Exception as e:
            logger.error(
                f"Failed to parse group timestamp: {str(e)}",
                error_type=type(e).__name__
            )
            return None

    def _fetch_btc_data(self, timestamp: datetime) -> Optional[Dict[str, Any]]:
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
            
            # Query btc_truth table
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
                ORDER BY ABS(EXTRACT(EPOCH FROM (timestamp - $3)))
                LIMIT 1
            """
            
            # Execute query synchronously (postgres_client should support sync queries)
            result = self.postgres_client.execute_query_sync(
                query,
                start_time,
                end_time,
                timestamp
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
                    "BTC data fetched from database",
                    query_timestamp=timestamp.isoformat(),
                    btc_timestamp=row["timestamp"].isoformat() if row["timestamp"] else None,
                    btc_close=row["close"]
                )
                
                return btc_data
            
            return None
            
        except Exception as e:
            logger.error(
                f"Failed to fetch BTC data: {str(e)}",
                error_type=type(e).__name__,
                timestamp=timestamp.isoformat()
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
            "btc_label_spike": False,
        }

