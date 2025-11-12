"""
Model manager for loading and managing ML models.

Provides high-level interface for model loading with version management.
Implements circuit breaker pattern and fallback model support.
"""

import asyncio
import logging
import pickle
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd
from mlflow.pyfunc import PyFuncModel

from ..clients import MLflowModelClient, PostgresClient
from ..exceptions import InferenceError, ModelLoadError
from ..features.btc_feature_builder import BtcFeatureBuilder
from ..utils.ab_testing import ABTestingStrategy
from ..utils.trace import trace_span

logger = logging.getLogger(__name__)

# Thread pool for running synchronous model predictions
_thread_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="model_predict")


class ModelManager:
    """
    Manager for ML model loading and inference.

    Handles model versioning, A/B testing, and fallback models.
    """

    def __init__(
        self,
        mlflow_client: MLflowModelClient,
        postgres_client: PostgresClient,
        ab_testing_strategy: ABTestingStrategy | None = None,
    ):
        """
        Initialize model manager.

        Args:
            mlflow_client: MLflow client instance
            postgres_client: PostgreSQL client for BTC feature building
            ab_testing_strategy: Optional A/B testing strategy
        """
        self.mlflow_client = mlflow_client
        self.postgres_client = postgres_client
        self.ab_testing_strategy = ab_testing_strategy
        self._models: dict[str, PyFuncModel] = {}
        self._preprocessors: dict[str, Any] = {}  # Cache preprocessors by model version
        self._model_names: dict[str, str] = {}  # Cache model names by version
        self.btc_feature_builder = BtcFeatureBuilder(postgres_client)

        logger.info("Initialized model manager")

    async def load_model(
        self,
        model_version: str | None = None,
        trace_id: str | None = None,
        domain: str | None = None,
    ) -> PyFuncModel:
        """
        Load model from MLflow registry.

        Args:
            model_version: Model version to load (uses default if None)
            trace_id: Optional trace ID for distributed tracing
            domain: Optional domain filter (btc/conflict/geopolitical) for auto-selection

        Returns:
            Loaded model instance

        Raises:
            ModelLoadError: If model loading fails
        """
        with trace_span(
            "load_model",
            attributes={"model_version": model_version, "trace_id": trace_id, "domain": domain},
        ):
            try:
                # Load model from MLflow
                model = await self.mlflow_client.load_model(
                    model_version=model_version,
                    use_fallback=True,
                    trace_id=trace_id,
                    domain=domain,
                )

                # Cache model
                version = model_version or self.mlflow_client.config.model_version
                self._models[version] = model

                # Store model name for preprocessor loading
                # Get model name from MLflow client's selected model info or config
                if hasattr(self.mlflow_client, '_selected_model_info') and self.mlflow_client._selected_model_info:
                    model_name = self.mlflow_client._selected_model_info.get('model_name')
                else:
                    # Get model name based on domain
                    if domain == "btc":
                        model_name = self.mlflow_client.config.btc_model_name
                    elif domain == "conflict":
                        model_name = self.mlflow_client.config.conflict_model_name
                    else:
                        model_name = None

                if model_name:
                    self._model_names[version] = model_name
                    logger.info(f"Stored model name for version {version}: {model_name}")

                logger.info(
                    f"Model loaded: version={version}",
                    extra={"trace_id": trace_id, "model_version": version},
                )

                return model

            except ModelLoadError:
                raise
            except Exception as e:
                logger.error(
                    f"Failed to load model: version={model_version}, error={e}",
                    exc_info=True,
                    extra={"trace_id": trace_id},
                )
                raise ModelLoadError(
                    f"Failed to load model: {e}",
                    model_version=model_version,
                    trace_id=trace_id,
                )

    async def get_model_for_group(
        self,
        group_id: str,
        trace_id: str | None = None,
        domain: str | None = None,
    ) -> tuple[PyFuncModel, str]:
        """
        Get model for a semantic group using A/B testing strategy.

        Args:
            group_id: Semantic group ID
            trace_id: Optional trace ID for distributed tracing
            domain: Optional domain filter (btc/conflict/geopolitical) for auto-selection

        Returns:
            Tuple of (model, model_version)

        Raises:
            ModelLoadError: If model loading fails
        """
        # Select model version using A/B testing
        if self.ab_testing_strategy:
            model_version = self.ab_testing_strategy.select_variant(group_id)
        else:
            model_version = self.mlflow_client.config.model_version

        # Create cache key that includes domain to avoid loading wrong model
        cache_key = f"{model_version}:{domain}" if domain else model_version

        # Check if model is already loaded
        if cache_key in self._models:
            return self._models[cache_key], model_version

        # Load model
        model = await self.load_model(model_version, trace_id, domain=domain)

        # Cache with domain-aware key
        self._models[cache_key] = model

        return model, model_version

    async def predict_btc(
        self,
        features: dict[str, Any],
        trace_id: str | None = None,
    ) -> dict[str, float]:
        """
        Make BTC price prediction using BTC model and preprocessor.

        Args:
            features: Feature dictionary (24 base features from Feast)
            trace_id: Optional trace ID for distributed tracing

        Returns:
            Dictionary containing:
                - prediction_value: float (predicted BTC price change %)
                - prediction_confidence: float (0.0-1.0)

        Raises:
            InferenceError: If prediction fails
        """
        with trace_span(
            "model_predict_btc",
            attributes={"trace_id": trace_id},
        ):
            try:
                logger.info(
                    f"=== BTC PREDICTION START ===",
                    extra={"trace_id": trace_id, "feature_count": len(features)},
                )

                # Load BTC model
                btc_model = await self.model_loader.lazy_load_model(
                    model_version=None,  # Use latest
                    trace_id=trace_id,
                )
                model_version = self.model_loader.get_model_version()

                # Load BTC preprocessor from MLflow
                btc_preprocessor = await self.model_loader.load_preprocessor(
                    pipeline_name="btc_prediction",
                    preprocessor_version=None,  # Use Production
                    trace_id=trace_id,
                )

                logger.info(
                    f"BTC model and preprocessor loaded: model_version={model_version}",
                    extra={"trace_id": trace_id},
                )

                # Build BTC features (17 features: 4 base + 13 BTC-specific)
                timestamp_str = features.get("semantic_group_features:timestamp") or features.get("timestamp")
                if timestamp_str:
                    try:
                        timestamp = datetime.fromisoformat(str(timestamp_str))
                    except Exception:
                        timestamp = datetime.utcnow()
                else:
                    timestamp = datetime.utcnow()

                btc_features = await self.btc_feature_builder.build_btc_features(
                    features,
                    timestamp=timestamp,
                )

                logger.info(
                    f"Built {len(btc_features)} BTC features",
                    extra={"trace_id": trace_id, "feature_names": list(btc_features.keys())},
                )

                # Preprocess features
                input_data = self._prepare_input(btc_features, btc_preprocessor)

                logger.info(
                    f"Preprocessed BTC features: shape={input_data.shape}",
                    extra={"trace_id": trace_id},
                )

                # Make prediction (regression model)
                prediction = btc_model.predict(input_data)
                predicted_value = float(prediction[0]) if isinstance(prediction, np.ndarray) else float(prediction)

                # Calculate confidence (for regression, use a simple heuristic)
                confidence = 0.7  # Default confidence for regression

                result = {
                    "prediction_value": predicted_value,
                    "prediction_confidence": confidence,
                }

                logger.info(
                    f"=== BTC PREDICTION COMPLETE: value={predicted_value:.4f}, confidence={confidence:.4f} ===",
                    extra={"trace_id": trace_id},
                )

                return result

            except Exception as e:
                logger.error(
                    f"BTC prediction failed: {e}",
                    extra={"trace_id": trace_id},
                    exc_info=True,
                )
                raise InferenceError(
                    message=f"BTC prediction failed: {str(e)}",
                    details={"trace_id": trace_id},
                ) from e

    async def predict_conflict(
        self,
        features: dict[str, Any],
        trace_id: str | None = None,
    ) -> dict[str, float]:
        """
        Make conflict prediction using conflict model and preprocessor.

        Args:
            features: Feature dictionary (24 base features from Feast)
            trace_id: Optional trace ID for distributed tracing

        Returns:
            Dictionary containing:
                - prediction_probability: float (0.0-1.0)
                - prediction_confidence: float (0.0-1.0)

        Raises:
            InferenceError: If prediction fails
        """
        with trace_span(
            "model_predict_conflict",
            attributes={"trace_id": trace_id},
        ):
            try:
                logger.info(
                    f"=== CONFLICT PREDICTION START ===",
                    extra={"trace_id": trace_id, "feature_count": len(features)},
                )

                # Load conflict model
                conflict_model = await self.model_loader.lazy_load_model(
                    model_version=None,  # Use latest
                    trace_id=trace_id,
                )
                model_version = self.model_loader.get_model_version()

                # Load conflict preprocessor from MLflow
                conflict_preprocessor = await self.model_loader.load_preprocessor(
                    pipeline_name="conflict_prediction",
                    preprocessor_version=None,  # Use Production
                    trace_id=trace_id,
                )

                logger.info(
                    f"Conflict model and preprocessor loaded: model_version={model_version}",
                    extra={"trace_id": trace_id},
                )

                # Filter to 24 general features (no BTC features)
                general_feature_names = [
                    # Source features (4)
                    "num_sources", "source_credibility_avg", "source_credibility_std", "source_diversity_score",
                    # Temporal features (4)
                    "time_span_hours", "publication_velocity", "temporal_concentration", "days_since_first_article",
                    # Sentiment features (4)
                    "sentiment_mean", "sentiment_std", "sentiment_polarity_ratio", "sentiment_volatility",
                    # Entity features (4)
                    "entity_count", "entity_diversity", "entity_prominence", "entity_concentration",
                    # Content features (4)
                    "avg_word_count", "avg_title_length", "language_diversity", "domain_diversity",
                    # Embedding features (4)
                    "centroid_magnitude", "intra_cluster_similarity_mean", "intra_cluster_similarity_std", "cluster_density",
                ]

                conflict_features = {}
                for feature_name in general_feature_names:
                    prefixed_name = f"semantic_group_features:{feature_name}"
                    if prefixed_name in features:
                        conflict_features[prefixed_name] = features[prefixed_name]
                    elif feature_name in features:
                        conflict_features[f"semantic_group_features:{feature_name}"] = features[feature_name]

                logger.info(
                    f"Filtered to {len(conflict_features)} conflict features",
                    extra={"trace_id": trace_id, "feature_names": list(conflict_features.keys())},
                )

                # Preprocess features
                input_data = self._prepare_input(conflict_features, conflict_preprocessor)

                logger.info(
                    f"Preprocessed conflict features: shape={input_data.shape}",
                    extra={"trace_id": trace_id},
                )

                # Make prediction (classification model)
                if hasattr(conflict_model, 'predict_proba'):
                    prediction_proba = conflict_model.predict_proba(input_data)
                    probability = float(prediction_proba[0][1])
                    confidence = abs(probability - 0.5) * 2.0
                else:
                    # Fallback if not a classifier
                    prediction = conflict_model.predict(input_data)
                    probability = float(prediction[0])
                    confidence = 0.7

                result = {
                    "prediction_probability": probability,
                    "prediction_confidence": confidence,
                }

                logger.info(
                    f"=== CONFLICT PREDICTION COMPLETE: probability={probability:.4f}, confidence={confidence:.4f} ===",
                    extra={"trace_id": trace_id},
                )

                return result

            except Exception as e:
                logger.error(
                    f"Conflict prediction failed: {e}",
                    extra={"trace_id": trace_id},
                    exc_info=True,
                )
                raise InferenceError(
                    message=f"Conflict prediction failed: {str(e)}",
                    details={"trace_id": trace_id},
                ) from e

    async def predict(
        self,
        model: PyFuncModel,
        features: dict[str, Any],
        model_version: str,
        trace_id: str | None = None,
        domain: str | None = None,
    ) -> dict[str, float]:
        """
        Make prediction using model (legacy method - delegates to predict_btc or predict_conflict).

        Args:
            model: Loaded model instance (ignored, loads from MLflow)
            features: Feature dictionary (24 features from Feast)
            model_version: Model version identifier (ignored, uses latest)
            trace_id: Optional trace ID for distributed tracing
            domain: Domain for prediction (btc/conflict/geopolitical)

        Returns:
            Dictionary containing prediction results

        Raises:
            InferenceError: If prediction fails
        """
        # Delegate to domain-specific methods
        if domain and domain.lower() == "btc":
            return await self.predict_btc(features, trace_id)
        else:
            return await self.predict_conflict(features, trace_id)

    async def _predict_legacy(
        self,
        model: PyFuncModel,
        features: dict[str, Any],
        model_version: str,
        trace_id: str | None = None,
        domain: str | None = None,
    ) -> dict[str, float]:
        """
        Legacy prediction method (kept for reference, not used).

        Args:
            model: Loaded model instance
            features: Feature dictionary (28 features from feature-engineering)
            model_version: Model version identifier
            trace_id: Optional trace ID for distributed tracing
            domain: Domain for prediction (btc/conflict/geopolitical)

        Returns:
            Dictionary containing:
                - prediction_probability: float (0.0-1.0)
                - prediction_confidence: float (0.0-1.0)

        Raises:
            InferenceError: If prediction fails
        """
        with trace_span(
            "model_predict",
            attributes={"model_version": model_version, "trace_id": trace_id, "domain": domain},
        ):
            try:
                # Log raw features before preprocessing
                logger.info(
                    f"Raw features before preprocessing: count={len(features)}, domain={domain}",
                    extra={
                        "trace_id": trace_id,
                        "model_version": model_version,
                        "domain": domain,
                        "feature_names": list(features.keys()),
                        "feature_sample": {k: features[k] for k in list(features.keys())[:5]},
                    },
                )

                # Prepare domain-specific features
                domain_features = await self._prepare_domain_features(features, domain, trace_id)

                logger.info(
                    f"Domain-specific features prepared: count={len(domain_features)}, domain={domain}",
                    extra={
                        "trace_id": trace_id,
                        "domain": domain,
                        "feature_count": len(domain_features),
                        "feature_names": list(domain_features.keys()),
                    },
                )

                # Load preprocessor for this model version
                preprocessor = await self._load_preprocessor(model_version, trace_id)

                # Prepare input data with preprocessing
                input_data = self._prepare_input(domain_features, preprocessor)

                # Log prepared input shape
                logger.info(
                    f"Prepared input for model: shape={input_data.shape}",
                    extra={
                        "trace_id": trace_id,
                        "model_version": model_version,
                        "input_shape": input_data.shape,
                        "preprocessor_used": preprocessor is not None,
                    },
                )

                # Make prediction synchronously (model prediction is CPU-bound but fast)
                logger.info(f"Starting model prediction", extra={"trace_id": trace_id})

                # Detect model type: classifier (has predict_proba) vs regressor (only has predict)
                if hasattr(model, 'predict_proba'):
                    # Classification model: use predict_proba to get probabilities
                    prediction_proba = model.predict_proba(input_data)
                    logger.info(f"Classification model prediction completed: shape={prediction_proba.shape}", extra={"trace_id": trace_id})
                    # Binary classification: [[prob_class_0, prob_class_1]]
                    probability = float(prediction_proba[0][1])
                    # Calculate confidence (distance from 0.5)
                    confidence = abs(probability - 0.5) * 2.0

                    result = {
                        "prediction_probability": probability,
                        "prediction_confidence": confidence,
                    }

                    logger.debug(
                        f"Classification prediction made: model_version={model_version}, "
                        f"probability={probability:.4f}, confidence={confidence:.4f}",
                        extra={"trace_id": trace_id, "model_version": model_version},
                    )
                else:
                    # Regression model: use predict to get predicted value
                    prediction = model.predict(input_data)
                    logger.info(f"Regression model prediction completed", extra={"trace_id": trace_id})
                    predicted_value = float(prediction[0]) if isinstance(prediction, np.ndarray) else float(prediction)

                    # For regression, we return the predicted value as "prediction_probability"
                    # and use a normalized confidence based on the model's uncertainty
                    # For now, use a fixed confidence of 0.5 (can be improved with prediction intervals)
                    confidence = 0.5

                    result = {
                        "prediction_probability": predicted_value,
                        "prediction_confidence": confidence,
                    }

                    logger.debug(
                        f"Regression prediction made: model_version={model_version}, "
                        f"predicted_value={predicted_value:.4f}, confidence={confidence:.4f}",
                        extra={"trace_id": trace_id, "model_version": model_version},
                    )

                return result

            except Exception as e:
                logger.error(
                    f"Prediction failed: model_version={model_version}, error={e}",
                    exc_info=True,
                    extra={"trace_id": trace_id},
                )
                raise InferenceError(
                    f"Prediction failed: {e}",
                    model_version=model_version,
                    trace_id=trace_id,
                )

    async def _load_preprocessor(
        self,
        model_version: str,
        trace_id: str | None = None,
    ) -> Any:
        """
        Load preprocessor from MLflow for a specific model version.

        The preprocessor is stored as a separate model in MLflow with the naming convention:
        {pipeline_name}_preprocessor_base (e.g., btc_prediction_preprocessor_base)

        Args:
            model_version: Model version identifier
            trace_id: Optional trace ID for distributed tracing

        Returns:
            Loaded preprocessor instance

        Raises:
            ModelLoadError: If preprocessor loading fails
        """
        # Check cache first
        if model_version in self._preprocessors:
            logger.debug(f"Using cached preprocessor for version {model_version}")
            return self._preprocessors[model_version]

        try:
            logger.info(f"Loading preprocessor for model version {model_version}")

            # Get model name from cache
            model_name = self._model_names.get(model_version)

            if not model_name:
                logger.warning(f"Cannot determine pipeline name - model name not available for version {model_version}")
                return None

            logger.info(f"Model name for version {model_version}: {model_name}")

            # Extract pipeline name from model name
            # Model names follow pattern: {pipeline_name}_{model_type}_base
            # e.g., btc_prediction_xgboost_regressor_base -> btc_prediction
            # conflict_prediction_gradient_boosting_base -> conflict_prediction

            # Remove "_base" suffix first
            if model_name.endswith('_base'):
                name_without_base = model_name[:-5]  # Remove "_base"
            else:
                name_without_base = model_name

            # Now extract pipeline name (everything before the model type)
            # Known model types: xgboost_regressor, gradient_boosting_regressor, random_forest_regressor,
            #                    xgboost, gradient_boosting, random_forest, logistic_regression, voting_ensemble, llm
            model_types = [
                'xgboost_regressor', 'gradient_boosting_regressor', 'random_forest_regressor',
                'xgboost', 'gradient_boosting', 'random_forest', 'logistic_regression', 'voting_ensemble', 'llm'
            ]

            pipeline_name = None
            for model_type in model_types:
                if name_without_base.endswith(f'_{model_type}'):
                    pipeline_name = name_without_base[:-len(f'_{model_type}')]
                    break

            if not pipeline_name:
                logger.warning(f"Cannot parse pipeline name from model name: {model_name}")
                return None

            logger.info(f"Extracted pipeline name: {pipeline_name}")

            # Construct preprocessor model name
            preprocessor_model_name = f"{pipeline_name}_preprocessor_base"
            logger.info(f"Loading preprocessor model: {preprocessor_model_name}")

            # Load preprocessor as a separate model from MLflow
            import mlflow.pyfunc
            preprocessor_uri = f"models:/{preprocessor_model_name}/{model_version}"

            try:
                preprocessor = mlflow.pyfunc.load_model(preprocessor_uri)
                logger.info(f"Preprocessor loaded as MLflow model from {preprocessor_uri}")
            except Exception as e:
                logger.warning(f"Failed to load preprocessor as MLflow model: {e}")
                # Try loading as sklearn model (the preprocessor is a sklearn Pipeline)
                import mlflow.sklearn
                preprocessor = mlflow.sklearn.load_model(preprocessor_uri)
                logger.info(f"Preprocessor loaded as sklearn model from {preprocessor_uri}")

            # Cache it
            self._preprocessors[model_version] = preprocessor

            logger.info(f"Preprocessor loaded successfully for version {model_version}")
            return preprocessor

        except Exception as e:
            logger.warning(
                f"Failed to load preprocessor for version {model_version}: {e}. "
                "Will use raw features without preprocessing."
            )
            # Return None to indicate no preprocessing available
            return None

    async def _prepare_domain_features(
        self,
        features: dict[str, Any],
        domain: str | None,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Prepare domain-specific features from general features.

        For BTC domain:
        - Builds 17 BTC features (4 from feature-engineering + 13 from btc_truth)

        For conflict/geopolitical domains:
        - Filters to 24 general features (excludes BTC features)

        Args:
            features: General features from feature-engineering (28 features)
            domain: Domain for prediction (btc/conflict/geopolitical)
            trace_id: Optional trace ID for distributed tracing

        Returns:
            Domain-specific feature dictionary
        """
        try:
            # Determine domain from model name if not provided
            if not domain:
                domain = "btc"  # Default to BTC

            domain = domain.lower()

            if domain == "btc":
                # Build 17 BTC features
                logger.info(f"Building BTC features for BTC prediction: trace_id={trace_id}")

                # Extract timestamp from features if available
                timestamp_str = features.get("semantic_group_features:timestamp") or features.get("timestamp")
                if timestamp_str:
                    try:
                        timestamp = datetime.fromisoformat(str(timestamp_str))
                    except Exception:
                        timestamp = datetime.utcnow()
                else:
                    timestamp = datetime.utcnow()

                btc_features = await self.btc_feature_builder.build_btc_features(
                    features,
                    timestamp=timestamp,
                )

                logger.info(
                    f"Built {len(btc_features)} BTC features: trace_id={trace_id}, "
                    f"feature_count={len(btc_features)}"
                )

                return btc_features

            else:
                # For conflict/geopolitical: use 24 general features (exclude BTC features)
                logger.info(f"Filtering to 24 general features for {domain} prediction: trace_id={trace_id}")

                # List of 24 general features (exclude BTC features)
                general_feature_names = [
                    # Source features (4)
                    "num_sources",
                    "source_credibility_avg",
                    "source_credibility_std",
                    "source_diversity_score",
                    # Temporal features (4)
                    "time_span_hours",
                    "publication_velocity",
                    "temporal_concentration",
                    "days_since_first_article",
                    # Sentiment features (4)
                    "sentiment_mean",
                    "sentiment_std",
                    "sentiment_polarity_ratio",
                    "sentiment_volatility",
                    # Entity features (4)
                    "entity_count",
                    "entity_diversity",
                    "entity_prominence",
                    "entity_concentration",
                    # Content features (4)
                    "avg_word_count",
                    "avg_title_length",
                    "language_diversity",
                    "domain_diversity",
                    # Embedding features (4)
                    "centroid_magnitude",
                    "intra_cluster_similarity_mean",
                    "intra_cluster_similarity_std",
                    "embedding_drift_score",
                ]

                # Extract general features (handle both with and without prefix)
                # IMPORTANT: Keep the prefix for conflict features because the preprocessor was trained with it
                general_features = {}
                for feature_name in general_feature_names:
                    # Try with prefix first
                    prefixed_name = f"semantic_group_features:{feature_name}"
                    if prefixed_name in features:
                        # Keep the prefix for conflict features
                        general_features[prefixed_name] = features[prefixed_name]
                    elif feature_name in features:
                        # If feature exists without prefix, add prefix
                        general_features[prefixed_name] = features[feature_name]
                    else:
                        # Feature missing - set to 0
                        general_features[prefixed_name] = 0.0
                        logger.warning(
                            f"Missing feature: {feature_name}, trace_id={trace_id}, domain={domain}"
                        )

                logger.info(
                    f"Filtered to {len(general_features)} general features: "
                    f"trace_id={trace_id}, feature_count={len(general_features)}"
                )

                # Drop constant features (features with zero variance identified during training)
                # These 4 features were removed during model training because they had zero variance
                constant_features_to_drop = [
                    "semantic_group_features:num_sources",
                    "semantic_group_features:source_diversity_score",
                    "semantic_group_features:intra_cluster_similarity_std",
                    "semantic_group_features:embedding_drift_score",
                ]

                for feature_name in constant_features_to_drop:
                    if feature_name in general_features:
                        del general_features[feature_name]

                logger.info(
                    f"Dropped {len(constant_features_to_drop)} constant features, "
                    f"remaining: {len(general_features)} features (expected 20 for conflict model)"
                )

                return general_features

        except Exception as e:
            logger.error(f"Failed to prepare domain features: {e}", exc_info=True)
            raise InferenceError(f"Failed to prepare domain features: {e}")

    def _prepare_input(
        self,
        features: dict[str, Any],
        preprocessor: Any = None,
    ) -> np.ndarray:
        """
        Prepare input data for model prediction.

        Args:
            features: Feature dictionary (24 raw features)
            preprocessor: Optional preprocessor instance from training

        Returns:
            NumPy array ready for model input (preprocessed features)
        """
        # Convert features dict to DataFrame with single row
        # Ensure features are in the correct order as expected by the preprocessor
        feature_df = pd.DataFrame([features])

        logger.debug(
            f"Input features shape before preprocessing: {feature_df.shape}",
            extra={"feature_columns": list(feature_df.columns)},
        )

        # Apply preprocessing if available
        if preprocessor is not None:
            try:
                # Apply the same preprocessing pipeline as training:
                # 1. Handle missing values (imputation)
                # 2. Feature engineering (interaction + polynomial features)
                # 3. Scaling
                # 4. Remove constant features
                preprocessed_df, _ = preprocessor.preprocess(feature_df, y=None, fit=False)

                logger.debug(
                    f"Features after preprocessing: shape={preprocessed_df.shape}",
                    extra={"preprocessed_shape": preprocessed_df.shape},
                )

                # Convert to numpy array
                return preprocessed_df.values

            except Exception as e:
                logger.error(f"Preprocessing failed: {e}. Using raw features.", exc_info=True)
                # Fall back to raw features
                return feature_df.values
        else:
            # No preprocessor available, use raw features
            logger.warning("No preprocessor available, using raw features")
            return feature_df.values

    async def get_model_metadata(
        self,
        model_version: str | None = None,
    ) -> dict[str, Any]:
        """
        Get metadata for a model version.

        Args:
            model_version: Model version (uses default if None)

        Returns:
            Dictionary containing model metadata
        """
        return await self.mlflow_client.get_model_metadata(model_version)

    def get_loaded_models(self) -> list[str]:
        """
        Get list of loaded model versions.

        Returns:
            List of model version identifiers
        """
        return list(self._models.keys())
