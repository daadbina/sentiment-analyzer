"""
Feature engineering for model training.

Implements interaction features and polynomial features following Strategy pattern.
"""

import logging
from typing import Tuple, Optional, List, Dict, Any
import pandas as pd
import numpy as np
from sklearn.preprocessing import PolynomialFeatures

from ..exceptions import InferenceError

logger = logging.getLogger(__name__)


class FeatureEngineer:
    """Generates interaction and polynomial features."""

    def __init__(
        self,
        enable_interaction_features: bool = True,
        enable_polynomial_features: bool = True,
        polynomial_degree: int = 2,
    ):
        """
        Initialize feature engineer.

        Args:
            enable_interaction_features: Whether to generate interaction features
            enable_polynomial_features: Whether to generate polynomial features
            polynomial_degree: Degree for polynomial features (default: 2)
        """
        self.enable_interaction_features = enable_interaction_features
        self.enable_polynomial_features = enable_polynomial_features
        self.polynomial_degree = polynomial_degree
        self.poly_transformer = None
        self.interaction_feature_names = []
        self.polynomial_feature_names = []
        logger.info(
            f"Feature engineer initialized: "
            f"interactions={enable_interaction_features}, "
            f"polynomials={enable_polynomial_features} (degree={polynomial_degree})"
        )

    def engineer_features(
        self,
        X: pd.DataFrame,
        fit: bool = True,
    ) -> pd.DataFrame:
        """
        Generate interaction and polynomial features.

        Args:
            X: Input feature dataframe
            fit: Whether to fit transformers

        Returns:
            Dataframe with engineered features

        Raises:
            InferenceError: If feature engineering fails
        """
        try:
            logger.info(f"Engineering features from {X.shape[1]} base features")
            X_engineered = X.copy()

            # Generate interaction features
            if self.enable_interaction_features:
                X_engineered = self._generate_interaction_features(X_engineered)
                logger.info(
                    f"Added {len(self.interaction_feature_names)} interaction features"
                )

            # Generate polynomial features
            if self.enable_polynomial_features:
                X_engineered = self._generate_polynomial_features(
                    X_engineered, fit=fit
                )
                logger.info(
                    f"Added {len(self.polynomial_feature_names)} polynomial features"
                )

            logger.info(
                f"Feature engineering complete: {X.shape[1]} → {X_engineered.shape[1]} features"
            )
            return X_engineered

        except Exception as e:
            logger.error(f"Feature engineering failed: {e}")
            raise InferenceError(f"Feature engineering failed: {e}")

    def _generate_interaction_features(self, X: pd.DataFrame) -> pd.DataFrame:
        """
        Generate interaction features between key feature pairs.

        Args:
            X: Input features

        Returns:
            Features with interaction columns added
        """
        try:
            self.interaction_feature_names = []
            X_with_interactions = X.copy()

            # Define interaction pairs based on domain knowledge
            interaction_pairs = [
                ("time_span_hours", "sentiment_volatility"),
                ("num_sources", "entity_diversity"),
                ("publication_velocity", "temporal_concentration"),
                ("sentiment_std", "entity_prominence"),
                ("avg_word_count", "language_diversity"),
                ("source_credibility_avg", "publication_velocity"),
            ]

            for feat1, feat2 in interaction_pairs:
                if feat1 in X.columns and feat2 in X.columns:
                    interaction_name = f"{feat1}_x_{feat2}"
                    X_with_interactions[interaction_name] = X[feat1] * X[feat2]
                    self.interaction_feature_names.append(interaction_name)
                    logger.debug(f"Created interaction feature: {interaction_name}")

            # Add ratio features
            ratio_pairs = [
                ("publication_velocity", "temporal_concentration"),
                ("sentiment_std", "sentiment_mean"),
                ("entity_count", "num_sources"),
            ]

            for feat1, feat2 in ratio_pairs:
                if feat1 in X.columns and feat2 in X.columns:
                    # Avoid division by zero
                    ratio_name = f"{feat1}_div_{feat2}"
                    X_with_interactions[ratio_name] = np.where(
                        X[feat2] != 0,
                        X[feat1] / (X[feat2] + 1e-8),
                        0,
                    )
                    self.interaction_feature_names.append(ratio_name)
                    logger.debug(f"Created ratio feature: {ratio_name}")

            logger.info(
                f"Generated {len(self.interaction_feature_names)} interaction features"
            )
            return X_with_interactions

        except Exception as e:
            logger.error(f"Interaction feature generation failed: {e}")
            raise

    def _generate_polynomial_features(
        self, X: pd.DataFrame, fit: bool = True
    ) -> pd.DataFrame:
        """
        Generate polynomial features.

        Args:
            X: Input features
            fit: Whether to fit the transformer

        Returns:
            Features with polynomial columns added
        """
        try:
            if fit:
                self.poly_transformer = PolynomialFeatures(
                    degree=self.polynomial_degree,
                    include_bias=False,
                    interaction_only=False,
                )
                X_poly = self.poly_transformer.fit_transform(X)
            else:
                if self.poly_transformer is None:
                    raise InferenceError("Polynomial transformer not fitted")
                X_poly = self.poly_transformer.transform(X)

            # Get feature names
            feature_names = self.poly_transformer.get_feature_names_out(
                X.columns
            )
            self.polynomial_feature_names = [
                name for name in feature_names if name not in X.columns
            ]

            X_poly_df = pd.DataFrame(X_poly, columns=feature_names, index=X.index)

            logger.info(
                f"Generated {len(self.polynomial_feature_names)} polynomial features"
            )
            return X_poly_df

        except Exception as e:
            logger.error(f"Polynomial feature generation failed: {e}")
            raise

    def get_feature_names(self) -> Dict[str, List[str]]:
        """
        Get names of engineered features.

        Returns:
            Dictionary with interaction and polynomial feature names
        """
        return {
            "interaction_features": self.interaction_feature_names,
            "polynomial_features": self.polynomial_feature_names,
        }

