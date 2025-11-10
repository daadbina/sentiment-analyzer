"""
Train-test splitting with temporal awareness.

Implements time-based splitting to prevent data leakage.
"""

import logging
from typing import Tuple, Optional
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split

from src.config import config
from src.exceptions import DataPreparationError
from src.utils.trace import get_tracer

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)


class DataSplitter:
    """Splits data into train, validation, and test sets."""

    def __init__(
        self,
        test_size: float = 0.2,
        validation_size: float = 0.1,
        random_state: int = 42,
    ):
        """
        Initialize data splitter.

        Args:
            test_size: Fraction of data for test set
            validation_size: Fraction of data for validation set
            random_state: Random seed for reproducibility
        """
        self.test_size = test_size
        self.validation_size = validation_size
        self.random_state = random_state
        logger.info(
            f"Data splitter initialized: test_size={test_size}, "
            f"validation_size={validation_size}"
        )

    def split_temporal(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        timestamp_column: Optional[str] = None,
    ) -> Tuple[
        Tuple[pd.DataFrame, pd.Series],
        Tuple[pd.DataFrame, pd.Series],
        Tuple[pd.DataFrame, pd.Series],
    ]:
        """
        Split data temporally (time-based split).

        Args:
            X: Feature dataframe
            y: Label series
            timestamp_column: Name of timestamp column

        Returns:
            Tuple of ((X_train, y_train), (X_val, y_val), (X_test, y_test))

        Raises:
            DataPreparationError: If splitting fails
        """
        with tracer.start_as_current_span("split_temporal") as span:
            span.set_attribute("num_rows", len(X))
            span.set_attribute("test_size", self.test_size)
            span.set_attribute("validation_size", self.validation_size)

            try:
                logger.info(
                    f"Splitting {len(X)} rows temporally: "
                    f"test={self.test_size}, validation={self.validation_size}"
                )

                # Sort by timestamp if provided
                if timestamp_column and timestamp_column in X.columns:
                    X = X.sort_values(timestamp_column)
                    y = y.loc[X.index]

                # Calculate split indices
                n = len(X)
                test_idx = int(n * (1 - self.test_size))
                val_idx = int(test_idx * (1 - self.validation_size))

                # Split data
                X_train = X.iloc[:val_idx]
                y_train = y.iloc[:val_idx]

                X_val = X.iloc[val_idx:test_idx]
                y_val = y.iloc[val_idx:test_idx]

                X_test = X.iloc[test_idx:]
                y_test = y.iloc[test_idx:]

                logger.info(
                    f"Split complete: train={len(X_train)}, "
                    f"val={len(X_val)}, test={len(X_test)}"
                )

                return (X_train, y_train), (X_val, y_val), (X_test, y_test)

            except Exception as e:
                logger.error(f"Temporal split failed: {e}")
                raise DataPreparationError(
                    f"Temporal split failed: {e}",
                    stage="splitting",
                    details={"num_rows": len(X)},
                )

    def split_random(
        self,
        X: pd.DataFrame,
        y: pd.Series,
    ) -> Tuple[
        Tuple[pd.DataFrame, pd.Series],
        Tuple[pd.DataFrame, pd.Series],
        Tuple[pd.DataFrame, pd.Series],
    ]:
        """
        Split data randomly (stratified if possible).

        Args:
            X: Feature dataframe
            y: Label series

        Returns:
            Tuple of ((X_train, y_train), (X_val, y_val), (X_test, y_test))

        Raises:
            DataPreparationError: If splitting fails
        """
        with tracer.start_as_current_span("split_random") as span:
            span.set_attribute("num_rows", len(X))

            try:
                logger.info(f"Splitting {len(X)} rows randomly")

                # Set random seed
                np.random.seed(self.random_state)

                # Generate random indices
                indices = np.random.permutation(len(X))

                # Calculate split indices
                n = len(X)
                test_idx = int(n * (1 - self.test_size))
                val_idx = int(test_idx * (1 - self.validation_size))

                # Split indices
                train_indices = indices[:val_idx]
                val_indices = indices[val_idx:test_idx]
                test_indices = indices[test_idx:]

                # Split data
                X_train = X.iloc[train_indices]
                y_train = y.iloc[train_indices]

                X_val = X.iloc[val_indices]
                y_val = y.iloc[val_indices]

                X_test = X.iloc[test_indices]
                y_test = y.iloc[test_indices]

                logger.info(
                    f"Split complete: train={len(X_train)}, "
                    f"val={len(X_val)}, test={len(X_test)}"
                )

                return (X_train, y_train), (X_val, y_val), (X_test, y_test)

            except Exception as e:
                logger.error(f"Random split failed: {e}")
                raise DataPreparationError(
                    f"Random split failed: {e}",
                    stage="splitting",
                    details={"num_rows": len(X)},
                )

    def split_stratified(
        self,
        X: pd.DataFrame,
        y: pd.Series,
    ) -> Tuple[
        Tuple[pd.DataFrame, pd.Series],
        Tuple[pd.DataFrame, pd.Series],
        Tuple[pd.DataFrame, pd.Series],
    ]:
        """
        Split data with stratification to preserve class distribution.

        This method ensures that train, validation, and test sets have
        the same class distribution as the original dataset. This is
        critical for small datasets with class imbalance.

        Args:
            X: Feature dataframe
            y: Label series

        Returns:
            Tuple of ((X_train, y_train), (X_val, y_val), (X_test, y_test))

        Raises:
            DataPreparationError: If splitting fails
        """
        with tracer.start_as_current_span("split_stratified") as span:
            span.set_attribute("num_rows", len(X))

            try:
                logger.info(f"Splitting {len(X)} rows with stratification")

                # Log class distribution before split
                class_counts = y.value_counts().to_dict()
                class_dist = {k: v/len(y) for k, v in class_counts.items()}
                logger.info(f"Original class distribution: {class_dist}")

                # Check minimum samples per class
                min_samples_per_class = min(class_counts.values())
                min_required = max(2, int(1 / min(self.test_size, self.validation_size)))

                if min_samples_per_class < min_required:
                    logger.warning(
                        f"Insufficient samples for stratification: "
                        f"min_samples={min_samples_per_class}, required={min_required}. "
                        f"Falling back to random split."
                    )
                    return self.split_random(X, y)

                # First split: separate test set
                X_temp, X_test, y_temp, y_test = train_test_split(
                    X, y,
                    test_size=self.test_size,
                    random_state=self.random_state,
                    stratify=y
                )

                # Second split: separate validation from training
                # Calculate validation size relative to temp set
                val_size_relative = self.validation_size / (1 - self.test_size)

                X_train, X_val, y_train, y_val = train_test_split(
                    X_temp, y_temp,
                    test_size=val_size_relative,
                    random_state=self.random_state,
                    stratify=y_temp
                )

                # Log split results
                logger.info(
                    f"Split complete: train={len(X_train)}, "
                    f"val={len(X_val)}, test={len(X_test)}"
                )

                # Log class distributions in each split
                train_dist = y_train.value_counts().to_dict()
                val_dist = y_val.value_counts().to_dict()
                test_dist = y_test.value_counts().to_dict()

                logger.info(f"Train class distribution: {train_dist}")
                logger.info(f"Validation class distribution: {val_dist}")
                logger.info(f"Test class distribution: {test_dist}")

                # Validate minimum samples in validation set
                min_val_samples = min(val_dist.values())
                if min_val_samples < 2:
                    logger.warning(
                        f"Validation set has only {min_val_samples} samples for minority class. "
                        f"Metrics may be unreliable."
                    )

                return (X_train, y_train), (X_val, y_val), (X_test, y_test)

            except Exception as e:
                logger.error(f"Stratified split failed: {e}")
                raise DataPreparationError(
                    f"Stratified split failed: {e}",
                    stage="splitting",
                    details={"num_rows": len(X)},
                )

    def validate_split(
        self,
        X_train: pd.DataFrame,
        X_val: pd.DataFrame,
        X_test: pd.DataFrame,
        y_train: pd.Series,
        y_val: pd.Series,
        y_test: pd.Series,
    ) -> bool:
        """
        Validate split integrity.

        Args:
            X_train, X_val, X_test: Feature dataframes
            y_train, y_val, y_test: Label series

        Returns:
            True if split is valid, False otherwise

        Raises:
            DataPreparationError: If validation fails
        """
        with tracer.start_as_current_span("validate_split"):
            try:
                # Check no overlap
                train_idx = set(X_train.index)
                val_idx = set(X_val.index)
                test_idx = set(X_test.index)

                if train_idx & val_idx or train_idx & test_idx or val_idx & test_idx:
                    raise DataPreparationError(
                        "Data leakage detected: overlapping indices",
                        stage="split_validation",
                    )

                # Check sizes
                if len(X_train) == 0 or len(X_test) == 0:
                    raise DataPreparationError(
                        "Empty split detected",
                        stage="split_validation",
                    )

                # Check label alignment
                if (
                    len(y_train) != len(X_train)
                    or len(y_val) != len(X_val)
                    or len(y_test) != len(X_test)
                ):
                    raise DataPreparationError(
                        "Label-feature mismatch",
                        stage="split_validation",
                    )

                logger.info("Split validation passed")
                return True

            except Exception as e:
                logger.error(f"Split validation failed: {e}")
                raise DataPreparationError(
                    f"Split validation failed: {e}",
                    stage="split_validation",
                )
