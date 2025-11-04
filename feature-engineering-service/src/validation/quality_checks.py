"""Statistical quality checks for features."""

from typing import Dict, Any, List
import math
from scipy import stats
from ..utils import StructuredLogger

logger = StructuredLogger(__name__)


class QualityChecker:
    """Perform statistical quality checks on features."""

    def __init__(self, confidence_level: float = 0.95):
        """Initialize quality checker.

        Args:
            confidence_level: Confidence level for statistical tests
        """
        self.confidence_level = confidence_level
        self.checks_performed: List[str] = []

    def check_distribution(
        self,
        feature_name: str,
        values: List[float],
    ) -> Dict[str, Any]:
        """Check if values follow normal distribution.

        Args:
            feature_name: Name of feature
            values: List of values

        Returns:
            Dictionary with test results
        """
        if len(values) < 3:
            return {"test": "normality", "result": "insufficient_data"}

        try:
            # Shapiro-Wilk test for normality
            statistic, p_value = stats.shapiro(values)

            is_normal = p_value > (1 - self.confidence_level)

            logger.info(
                "Normality test completed",
                feature_name=feature_name,
                is_normal=is_normal,
                p_value=p_value,
            )

            return {
                "test": "normality",
                "feature": feature_name,
                "statistic": statistic,
                "p_value": p_value,
                "is_normal": is_normal,
            }
        except Exception as e:
            logger.error(
                "Error in normality test",
                feature_name=feature_name,
                error=str(e),
            )
            return {"test": "normality", "result": "error", "error": str(e)}

    def check_outliers(
        self,
        feature_name: str,
        values: List[float],
        method: str = "iqr",
    ) -> Dict[str, Any]:
        """Check for outliers using IQR or Z-score method.

        Args:
            feature_name: Name of feature
            values: List of values
            method: "iqr" or "zscore"

        Returns:
            Dictionary with outlier detection results
        """
        if len(values) < 2:
            return {"test": "outliers", "result": "insufficient_data"}

        try:
            if method == "iqr":
                q1 = stats.scoreatpercentile(values, 25)
                q3 = stats.scoreatpercentile(values, 75)
                iqr = q3 - q1
                lower_bound = q1 - 1.5 * iqr
                upper_bound = q3 + 1.5 * iqr
                outliers = [v for v in values if v < lower_bound or v > upper_bound]
            else:  # zscore
                mean = sum(values) / len(values)
                std = math.sqrt(sum((x - mean) ** 2 for x in values) / len(values))
                if std > 0:
                    z_scores = [(v - mean) / std for v in values]
                    outliers = [v for v, z in zip(values, z_scores) if abs(z) > 3]
                else:
                    outliers = []

            outlier_ratio = len(outliers) / len(values) if values else 0

            logger.info(
                "Outlier detection completed",
                feature_name=feature_name,
                outlier_count=len(outliers),
                outlier_ratio=outlier_ratio,
            )

            return {
                "test": "outliers",
                "feature": feature_name,
                "method": method,
                "outlier_count": len(outliers),
                "outlier_ratio": outlier_ratio,
                "outliers": outliers,
            }
        except Exception as e:
            logger.error(
                "Error in outlier detection",
                feature_name=feature_name,
                error=str(e),
            )
            return {"test": "outliers", "result": "error", "error": str(e)}

    def check_correlation(
        self,
        features: Dict[str, List[float]],
    ) -> Dict[str, Any]:
        """Check correlation between numeric features.

        Args:
            features: Dictionary of feature_name -> list of values

        Returns:
            Dictionary with correlation results
        """
        numeric_features = {
            k: v for k, v in features.items()
            if isinstance(v, list) and all(isinstance(x, (int, float)) for x in v)
        }

        if len(numeric_features) < 2:
            return {"test": "correlation", "result": "insufficient_features"}

        try:
            correlations = {}
            feature_names = list(numeric_features.keys())

            for i, feat1 in enumerate(feature_names):
                for feat2 in feature_names[i + 1:]:
                    values1 = numeric_features[feat1]
                    values2 = numeric_features[feat2]

                    if len(values1) == len(values2) and len(values1) > 2:
                        corr, p_value = stats.pearsonr(values1, values2)
                        correlations[f"{feat1}_vs_{feat2}"] = {
                            "correlation": corr,
                            "p_value": p_value,
                        }

            logger.info(
                "Correlation analysis completed",
                correlation_count=len(correlations),
            )

            return {
                "test": "correlation",
                "correlations": correlations,
            }
        except Exception as e:
            logger.error("Error in correlation analysis", error=str(e))
            return {"test": "correlation", "result": "error", "error": str(e)}

