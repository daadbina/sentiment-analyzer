"""
Data preprocessing for model training.

Handles missing values, scaling, feature selection, and feature engineering.
"""

import logging
from typing import Tuple, Optional, List
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.impute import SimpleImputer
from sklearn.feature_selection import SelectKBest, f_classif

from src.config import config
from src.exceptions import DataPreparationError
from src.utils.trace import get_tracer
from src.data.feature_engineer import FeatureEngineer

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)


class DataPreprocessor:
    """Preprocesses data for model training."""

    def __init__(self, scaling_method: str = "standard", enable_feature_engineering: bool = True):
        """
        Initialize data preprocessor.

        Args:
            scaling_method: Scaling method (standard or minmax)
            enable_feature_engineering: Whether to enable feature engineering
        """
        self.scaling_method = scaling_method
        self.scaler = None
        self.imputer = None
        self.feature_selector = None
        self.feature_engineer = None
        self.enable_feature_engineering = enable_feature_engineering
        self.constant_features_ = None  # Store constant features identified during fit

        if enable_feature_engineering:
            self.feature_engineer = FeatureEngineer(
                enable_interaction_features=config.feature_engineering.enable_interaction_features,
                enable_polynomial_features=config.feature_engineering.enable_polynomial_features,
                polynomial_degree=config.feature_engineering.polynomial_degree,
            )

        logger.info(
            f"Data preprocessor initialized with {scaling_method} scaling, "
            f"feature_engineering={enable_feature_engineering}"
        )

    def preprocess(
        self,
        X: pd.DataFrame,
        y: Optional[pd.Series] = None,
        fit: bool = True,
    ) -> Tuple[pd.DataFrame, Optional[pd.Series]]:
        """
        Preprocess features and labels.

        Args:
            X: Feature dataframe
            y: Optional label series
            fit: Whether to fit transformers

        Returns:
            Tuple of (preprocessed X, y)

        Raises:
            DataPreparationError: If preprocessing fails
        """
        with tracer.start_as_current_span("preprocess") as span:
            span.set_attribute("num_rows", len(X))
            span.set_attribute("num_features", X.shape[1])

            try:
                logger.info(
                    f"Preprocessing {X.shape[0]} rows with {X.shape[1]} features"
                )
                logger.debug(f"Input feature columns: {list(X.columns)}")
                logger.debug(f"Input feature dtypes:\n{X.dtypes}")

                # Convert object columns to numeric (handles Feast returning features as object dtype)
                object_cols = X.select_dtypes(include=['object']).columns.tolist()
                if object_cols:
                    logger.info(f"Converting object columns to numeric: {object_cols}")
                    for col in object_cols:
                        X[col] = pd.to_numeric(X[col], errors='coerce')
                    logger.debug(f"Dtypes after conversion:\n{X.dtypes}")

                # Filter to only numeric columns (exclude entity IDs and other non-numeric columns)
                numeric_cols = X.select_dtypes(include=['number']).columns.tolist()
                if len(numeric_cols) < X.shape[1]:
                    non_numeric_cols = [col for col in X.columns if col not in numeric_cols]
                    logger.info(f"Excluding non-numeric columns: {non_numeric_cols}")
                    X = X[numeric_cols]

                logger.info(f"Using {len(numeric_cols)} numeric features for training")

                # Check for null values before preprocessing
                null_before = X.isnull().sum()
                if null_before.sum() > 0:
                    logger.warning(f"Null values before preprocessing:\n{null_before[null_before > 0]}")
                else:
                    logger.info("No null values in input features")

                # Handle missing values
                X = self._handle_missing_values(X, fit=fit)
                logger.debug(f"Shape after handling missing values: {X.shape}")

                # Feature engineering (before scaling)
                if self.enable_feature_engineering and self.feature_engineer is not None:
                    X_before_fe = X.shape[1]
                    X = self.feature_engineer.engineer_features(X, fit=fit)
                    logger.info(f"Feature engineering: {X_before_fe} → {X.shape[1]} features")
                    logger.debug(f"Shape after feature engineering: {X.shape}")

                # Scale features
                X = self._scale_features(X, fit=fit)
                logger.debug(f"Shape after scaling: {X.shape}")

                # Remove constant features
                X = self._remove_constant_features(X, fit=fit)
                logger.debug(f"Shape after removing constant features: {X.shape}")

                # Log final statistics
                logger.info(f"Preprocessing complete: {X.shape}")
                logger.debug(f"Output feature statistics:\n{X.describe()}")

                # Check for any remaining issues
                if X.isnull().sum().sum() > 0:
                    logger.error("Null values still present after preprocessing!")
                if (X == np.inf).sum().sum() > 0 or (X == -np.inf).sum().sum() > 0:
                    logger.error("Infinite values found in preprocessed data!")

                return X, y

            except Exception as e:
                logger.error(f"Preprocessing failed: {e}", exc_info=True)
                raise DataPreparationError(
                    f"Preprocessing failed: {e}",
                    stage="preprocessing",
                    details={"num_rows": len(X), "num_features": X.shape[1]},
                )

    def _handle_missing_values(
        self,
        X: pd.DataFrame,
        fit: bool = True,
    ) -> pd.DataFrame:
        """
        Handle missing values using mean imputation.

        Args:
            X: Feature dataframe
            fit: Whether to fit imputer

        Returns:
            Dataframe with missing values handled
        """
        with tracer.start_as_current_span("handle_missing_values"):
            try:
                null_counts = X.isnull().sum()
                if null_counts.sum() > 0:
                    logger.info(f"Found {null_counts.sum()} missing values")
                    logger.debug(
                        f"Missing values per column: {null_counts[null_counts > 0]}"
                    )

                    # Check for columns with all NaN values
                    all_nan_cols = null_counts[null_counts == len(X)].index.tolist()
                    if all_nan_cols:
                        logger.warning(f"Columns with all NaN values (will be filled with 0): {all_nan_cols}")
                        # Fill all-NaN columns with 0 (default value for missing BTC features)
                        for col in all_nan_cols:
                            X[col] = 0.0

                    # Now handle remaining missing values with imputer
                    null_counts_after = X.isnull().sum()
                    if null_counts_after.sum() > 0:
                        if fit:
                            self.imputer = SimpleImputer(strategy="mean")
                            X_imputed = self.imputer.fit_transform(X)
                        else:
                            if self.imputer is None:
                                raise DataPreparationError(
                                    "Imputer not fitted",
                                    stage="missing_values",
                                )
                            X_imputed = self.imputer.transform(X)

                        X = pd.DataFrame(X_imputed, columns=X.columns, index=X.index)
                        logger.info("Missing values handled")

                return X

            except Exception as e:
                logger.error(f"Failed to handle missing values: {e}")
                raise DataPreparationError(
                    f"Failed to handle missing values: {e}",
                    stage="missing_values",
                )

    def _scale_features(
        self,
        X: pd.DataFrame,
        fit: bool = True,
    ) -> pd.DataFrame:
        """
        Scale features using specified method.

        Args:
            X: Feature dataframe
            fit: Whether to fit scaler

        Returns:
            Scaled dataframe
        """
        with tracer.start_as_current_span("scale_features"):
            try:
                if self.scaling_method == "standard":
                    if fit:
                        self.scaler = StandardScaler()
                        X_scaled = self.scaler.fit_transform(X)
                    else:
                        if self.scaler is None:
                            raise DataPreparationError(
                                "Scaler not fitted",
                                stage="scaling",
                            )
                        X_scaled = self.scaler.transform(X)

                elif self.scaling_method == "minmax":
                    if fit:
                        self.scaler = MinMaxScaler()
                        X_scaled = self.scaler.fit_transform(X)
                    else:
                        if self.scaler is None:
                            raise DataPreparationError(
                                "Scaler not fitted",
                                stage="scaling",
                            )
                        X_scaled = self.scaler.transform(X)
                else:
                    raise ValueError(f"Unknown scaling method: {self.scaling_method}")

                X = pd.DataFrame(X_scaled, columns=X.columns)
                logger.info(f"Features scaled using {self.scaling_method} method")
                return X

            except Exception as e:
                logger.error(f"Failed to scale features: {e}")
                raise DataPreparationError(
                    f"Failed to scale features: {e}",
                    stage="scaling",
                )

    def _remove_constant_features(self, X: pd.DataFrame, fit: bool = True) -> pd.DataFrame:
        """
        Remove constant features (zero variance).

        Args:
            X: Feature dataframe
            fit: Whether to identify constant features (True) or use previously identified ones (False)

        Returns:
            Dataframe with constant features removed
        """
        with tracer.start_as_current_span("remove_constant_features"):
            try:
                if fit:
                    # Calculate variance and identify constant features
                    variances = X.var()
                    constant_features = variances[variances == 0].index.tolist()

                    # Store for later use during inference
                    self.constant_features_ = constant_features

                    logger.info(f"Feature variance analysis: {len(X.columns)} total features")
                    logger.debug(f"Feature variances:\n{variances}")

                    if constant_features:
                        logger.warning(
                            f"Removing {len(constant_features)} constant features: {constant_features}"
                        )
                        logger.warning(f"Constant feature values:\n{X[constant_features].iloc[0] if len(X) > 0 else 'N/A'}")
                        X = X.drop(columns=constant_features)
                    else:
                        logger.info("No constant features found")

                    logger.info(f"After constant feature removal: {X.shape[1]} features remaining")
                    logger.debug(f"Remaining features: {list(X.columns)}")
                else:
                    # Use previously identified constant features
                    if self.constant_features_ is not None and len(self.constant_features_) > 0:
                        # Only drop features that exist in current dataframe
                        features_to_drop = [f for f in self.constant_features_ if f in X.columns]
                        if features_to_drop:
                            logger.info(f"Removing {len(features_to_drop)} constant features identified during training")
                            X = X.drop(columns=features_to_drop)
                        else:
                            logger.info("No constant features to remove (none found in current data)")
                    else:
                        logger.info("No constant features were identified during training")

                return X

            except Exception as e:
                logger.error(f"Failed to remove constant features: {e}")
                raise DataPreparationError(
                    f"Failed to remove constant features: {e}",
                    stage="feature_removal",
                )

    def select_features(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        k: int = 20,
        fit: bool = True,
    ) -> pd.DataFrame:
        """
        Select top k features using SelectKBest.

        Args:
            X: Feature dataframe
            y: Label series
            k: Number of features to select
            fit: Whether to fit selector

        Returns:
            Dataframe with selected features

        Raises:
            DataPreparationError: If selection fails
        """
        with tracer.start_as_current_span("select_features") as span:
            span.set_attribute("k", k)

            try:
                if fit:
                    self.feature_selector = SelectKBest(f_classif, k=min(k, X.shape[1]))
                    X_selected = self.feature_selector.fit_transform(X, y)
                    selected_features = X.columns[
                        self.feature_selector.get_support()
                    ].tolist()
                else:
                    if self.feature_selector is None:
                        raise DataPreparationError(
                            "Feature selector not fitted",
                            stage="feature_selection",
                        )
                    X_selected = self.feature_selector.transform(X)
                    selected_features = X.columns[
                        self.feature_selector.get_support()
                    ].tolist()

                X = pd.DataFrame(X_selected, columns=selected_features)
                logger.info(f"Selected {len(selected_features)} features")
                logger.debug(f"Selected features: {selected_features}")

                return X

            except Exception as e:
                logger.error(f"Feature selection failed: {e}")
                raise DataPreparationError(
                    f"Feature selection failed: {e}",
                    stage="feature_selection",
                    details={"k": k},
                )
