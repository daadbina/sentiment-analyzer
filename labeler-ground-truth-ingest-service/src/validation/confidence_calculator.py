"""
Confidence score calculator for ground truth labels.

This module computes dynamic confidence scores based on data quality,
source reliability, and label characteristics. NO hardcoded confidence values.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ConfidenceCalculator:
    """Calculate confidence scores for ground truth labels."""

    # Known reliable news domains (for GDELT)
    RELIABLE_DOMAINS = {
        "reuters.com": 0.95,
        "apnews.com": 0.95,
        "bbc.com": 0.90,
        "cnn.com": 0.85,
        "nytimes.com": 0.90,
        "washingtonpost.com": 0.90,
        "theguardian.com": 0.90,
        "aljazeera.com": 0.85,
        "bloomberg.com": 0.90,
        "ft.com": 0.90,
    }

    # GDELT conflict event codes (higher specificity = higher confidence)
    HIGH_CONFIDENCE_EVENT_CODES = {
        "18", "180", "181", "182", "183", "184", "185", "186",  # Assault
        "19", "190", "191", "192", "193", "194", "195", "196",  # Fight
        "20", "200", "201", "202", "203", "204", "205",  # Mass violence
    }

    def __init__(self):
        """Initialize confidence calculator."""
        logger.info("Confidence calculator initialized")

    def calculate_btc_confidence(
        self,
        change_pct: float,
        volatility_score: float,
        volume: float,
        source: str = "binance"
    ) -> float:
        """
        Calculate confidence for BTC/crypto labels.

        Confidence based on:
        - Price change magnitude (higher = more confident)
        - Volatility (lower = more confident in stable trends)
        - Volume (higher = more confident)
        - Data source (Binance > CCXT)

        Args:
            change_pct: Price change percentage
            volatility_score: Volatility score (0-1)
            volume: Trading volume
            source: Data source (binance, ccxt)

        Returns:
            Confidence score (0.5-1.0)
        """
        try:
            # Base confidence by source
            if source.lower() == "binance":
                base_confidence = 0.85
            elif source.lower() == "ccxt":
                base_confidence = 0.75
            else:
                base_confidence = 0.70

            # Adjust for price change magnitude (0-0.15)
            # Larger changes are more significant and easier to detect
            change_magnitude = abs(change_pct)
            if change_magnitude >= 10.0:
                change_bonus = 0.15
            elif change_magnitude >= 5.0:
                change_bonus = 0.10
            elif change_magnitude >= 2.0:
                change_bonus = 0.05
            else:
                change_bonus = 0.0

            # Adjust for volatility (-0.10 to 0.0)
            # Lower volatility = more confident in the trend
            if volatility_score < 0.3:
                volatility_adjustment = 0.0  # Low volatility, stable trend
            elif volatility_score < 0.6:
                volatility_adjustment = -0.05  # Moderate volatility
            else:
                volatility_adjustment = -0.10  # High volatility, less confident

            # Adjust for volume (0-0.10)
            # Normalize volume to a reasonable scale (assuming volume in millions)
            volume_millions = volume / 1_000_000
            if volume_millions >= 100:
                volume_bonus = 0.10
            elif volume_millions >= 50:
                volume_bonus = 0.05
            elif volume_millions >= 10:
                volume_bonus = 0.02
            else:
                volume_bonus = 0.0

            # Calculate final confidence
            confidence = base_confidence + change_bonus + volatility_adjustment + volume_bonus

            # Clamp to [0.5, 1.0]
            confidence = max(0.5, min(1.0, confidence))

            logger.debug(
                f"BTC confidence calculated: {confidence:.3f} "
                f"(base={base_confidence:.2f}, change={change_bonus:.2f}, "
                f"volatility={volatility_adjustment:.2f}, volume={volume_bonus:.2f})"
            )

            return confidence

        except Exception as e:
            logger.error(f"Failed to calculate BTC confidence: {e}")
            return 0.70  # Fallback to moderate confidence

    def calculate_gdelt_confidence(
        self,
        event_code: Optional[str],
        goldstein_scale: float,
        countries: List[str],
        source_url: str,
        description: Optional[str] = None
    ) -> float:
        """
        Calculate confidence for GDELT event labels.

        Confidence based on:
        - Event code specificity (specific codes = higher confidence)
        - Goldstein scale magnitude (more extreme = higher confidence)
        - NER quality (more countries = better extraction)
        - Source domain reliability

        Args:
            event_code: GDELT event code (e.g., "18", "190")
            goldstein_scale: Goldstein scale (-10 to +10)
            countries: List of extracted countries
            source_url: Source URL
            description: Event description (optional)

        Returns:
            Confidence score (0.5-1.0)
        """
        try:
            # Base confidence
            base_confidence = 0.70

            # Adjust for event code specificity (0-0.15)
            # Convert event_code to string if it's an integer
            event_code_str = str(event_code) if event_code is not None else ""

            if event_code_str and event_code_str in self.HIGH_CONFIDENCE_EVENT_CODES:
                event_code_bonus = 0.15  # High confidence conflict codes
            elif event_code_str and len(event_code_str) >= 3:
                event_code_bonus = 0.10  # Specific 3-digit codes
            elif event_code_str and len(event_code_str) == 2:
                event_code_bonus = 0.05  # General 2-digit codes
            else:
                event_code_bonus = 0.0  # No event code

            # Adjust for Goldstein scale magnitude (0-0.10)
            # More extreme values = more significant events
            goldstein_magnitude = abs(goldstein_scale)
            if goldstein_magnitude >= 8.0:
                goldstein_bonus = 0.10
            elif goldstein_magnitude >= 5.0:
                goldstein_bonus = 0.07
            elif goldstein_magnitude >= 3.0:
                goldstein_bonus = 0.04
            else:
                goldstein_bonus = 0.0

            # Adjust for NER quality (0-0.10)
            # More countries extracted = better NER quality
            logger.debug(
                f"DEBUG: countries type={type(countries).__name__}, value={countries}"
            )

            if isinstance(countries, (list, tuple)):
                num_countries = len(countries)
            elif isinstance(countries, int):
                num_countries = countries
            else:
                num_countries = 0

            if num_countries >= 3:
                ner_bonus = 0.10
            elif num_countries == 2:
                ner_bonus = 0.07
            elif num_countries == 1:
                ner_bonus = 0.04
            else:
                ner_bonus = 0.0  # No countries extracted

            # Adjust for source domain reliability (0-0.15)
            domain_bonus = 0.0
            if source_url:
                for domain, reliability in self.RELIABLE_DOMAINS.items():
                    if domain in source_url.lower():
                        domain_bonus = (reliability - 0.70) * 0.5  # Scale to 0-0.125
                        break

            # Calculate final confidence
            confidence = (
                base_confidence
                + event_code_bonus
                + goldstein_bonus
                + ner_bonus
                + domain_bonus
            )

            # Clamp to [0.5, 1.0]
            confidence = max(0.5, min(1.0, confidence))

            logger.debug(
                f"GDELT confidence calculated: {confidence:.3f} "
                f"(base={base_confidence:.2f}, event_code={event_code_bonus:.2f}, "
                f"goldstein={goldstein_bonus:.2f}, ner={ner_bonus:.2f}, domain={domain_bonus:.2f})"
            )

            return confidence

        except Exception as e:
            import traceback
            logger.error(
                f"Failed to calculate GDELT confidence: {e}\n"
                f"event_code={event_code}, goldstein_scale={goldstein_scale}, "
                f"countries_type={type(countries).__name__}, countries_value={str(countries)[:100]}, "
                f"source_url={source_url[:50] if source_url else None}\n"
                f"Traceback: {traceback.format_exc()}"
            )
            return 0.70  # Fallback to moderate confidence

    def calculate_acled_confidence(
        self,
        event_type: str,
        fatalities: int,
        source_url: Optional[str] = None
    ) -> float:
        """
        Calculate confidence for ACLED event labels.

        Confidence based on:
        - Event type specificity
        - Fatalities count (higher = more significant)
        - Source URL quality

        Args:
            event_type: ACLED event type
            fatalities: Number of fatalities
            source_url: Source URL (optional)

        Returns:
            Confidence score (0.7-1.0)
        """
        try:
            # Base confidence (ACLED is generally high quality)
            base_confidence = 0.80

            # Adjust for event type specificity (0-0.10)
            high_confidence_types = [
                "Violence against civilians",
                "Battles",
                "Explosions/Remote violence"
            ]
            if event_type in high_confidence_types:
                event_type_bonus = 0.10
            elif event_type in ["Protests", "Riots"]:
                event_type_bonus = 0.05
            else:
                event_type_bonus = 0.0

            # Adjust for fatalities (0-0.10)
            # More fatalities = more significant and verifiable event
            if fatalities >= 100:
                fatalities_bonus = 0.10
            elif fatalities >= 50:
                fatalities_bonus = 0.08
            elif fatalities >= 10:
                fatalities_bonus = 0.05
            elif fatalities >= 1:
                fatalities_bonus = 0.02
            else:
                fatalities_bonus = 0.0

            # Calculate final confidence
            confidence = base_confidence + event_type_bonus + fatalities_bonus

            # Clamp to [0.7, 1.0] (ACLED is high quality, minimum 0.7)
            confidence = max(0.70, min(1.0, confidence))

            logger.debug(
                f"ACLED confidence calculated: {confidence:.3f} "
                f"(base={base_confidence:.2f}, event_type={event_type_bonus:.2f}, "
                f"fatalities={fatalities_bonus:.2f})"
            )

            return confidence

        except Exception as e:
            logger.error(f"Failed to calculate ACLED confidence: {e}")
            return 0.80  # Fallback to high confidence (ACLED is reliable)

