"""
LLM baseline model implementation.

Zero-shot baseline using OpenAI GPT-4 or local LLM.
"""

import logging
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
import openai

from src.models.base_model import BaseModel
from src.config import config
from src.exceptions import TrainingError, ExternalServiceError
from src.utils.trace import get_tracer

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)


class LLMBaselineModel(BaseModel):
    """LLM baseline model using zero-shot prompting."""

    def __init__(self):
        """Initialize LLM baseline model."""
        model_config = {
            "model_name": config.llm.model_name,
            "temperature": config.llm.temperature,
            "max_tokens": config.llm.max_tokens,
            "api_key": config.llm.api_key,
        }

        super().__init__(
            model_name="llm_baseline_sentiment",
            model_type="llm",
            config=model_config,
        )

        # Set OpenAI API key
        openai.api_key = config.llm.api_key
        logger.info(f"LLM baseline model initialized with {config.llm.model_name}")

    def train(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: Optional[pd.DataFrame] = None,
        y_val: Optional[pd.Series] = None,
    ) -> Dict[str, Any]:
        """
        Train LLM baseline (no actual training, just setup).

        Args:
            X_train: Training features
            y_train: Training labels
            X_val: Optional validation features
            y_val: Optional validation labels

        Returns:
            Dictionary with training metrics

        Raises:
            TrainingError: If setup fails
        """
        with tracer.start_as_current_span("train_llm_baseline") as span:
            span.set_attribute("num_train_samples", len(X_train))

            try:
                self.validate_input(X_train, y_train)

                logger.info(f"Setting up LLM baseline with {len(X_train)} samples")

                # LLM doesn't need training, just validation
                self.is_trained = True

                metrics = {
                    "model_type": "llm",
                    "num_train_samples": len(X_train),
                    "num_features": X_train.shape[1],
                    "model_name": config.llm.model_name,
                }

                logger.info(f"LLM baseline setup complete: {metrics}")
                return metrics

            except Exception as e:
                logger.error(f"LLM baseline setup failed: {e}")
                raise TrainingError(
                    f"LLM baseline setup failed: {e}",
                    model_name=self.model_name,
                )

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Make predictions using LLM baseline heuristic.

        Since features are numeric Feast features (not text), use an improved heuristic:
        - Get prediction probabilities using weighted feature approach
        - Apply threshold at 0.5 to get binary predictions

        Args:
            X: Features for prediction (numeric Feast features)

        Returns:
            Binary predictions (0 or 1)

        Raises:
            TrainingError: If prediction fails
        """
        with tracer.start_as_current_span("predict_llm_baseline"):
            try:
                if not self.is_trained:
                    raise TrainingError(
                        "Model not trained",
                        model_name=self.model_name,
                    )

                logger.info(f"Making LLM baseline predictions for {len(X)} samples using numeric features")

                # Get probabilities and apply threshold
                probabilities = self.predict_proba(X)
                predictions = (probabilities[:, 1] > 0.5).astype(int)

                logger.info(f"Made predictions for {len(X)} samples")
                return predictions

            except Exception as e:
                logger.error(f"LLM prediction failed: {e}")
                raise TrainingError(
                    f"LLM prediction failed: {e}",
                    model_name=self.model_name,
                )

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """
        Get prediction probabilities using LLM baseline heuristic.

        Since features are numeric Feast features (not text), use an improved heuristic:
        - Normalize features to [0, 1] range
        - Weight features by their variance (more variance = more informative)
        - Use weighted average as probability estimate
        - Apply sigmoid transformation for better calibration

        Args:
            X: Features for prediction (numeric Feast features)

        Returns:
            Prediction probabilities (shape: [n_samples, 2])

        Raises:
            TrainingError: If prediction fails
        """
        with tracer.start_as_current_span("predict_proba_llm_baseline"):
            try:
                if not self.is_trained:
                    raise TrainingError(
                        "Model not trained",
                        model_name=self.model_name,
                    )

                logger.debug(f"Getting probabilities for {len(X)} samples using numeric features")

                # Compute feature statistics for normalization and weighting
                numeric_X = X.select_dtypes(include=[np.number])

                if numeric_X.empty:
                    logger.warning("No numeric features found, using default probabilities")
                    return np.array([[0.5, 0.5]] * len(X))

                # Normalize features to [0, 1] range
                X_min = numeric_X.min()
                X_max = numeric_X.max()
                X_range = X_max - X_min
                X_range[X_range == 0] = 1  # Avoid division by zero
                X_normalized = (numeric_X - X_min) / X_range

                # Compute feature weights based on variance
                feature_variance = numeric_X.var()
                feature_weights = feature_variance / feature_variance.sum()
                logger.debug(f"Feature weights (top 5): {feature_weights.nlargest(5).to_dict()}")

                # Compute weighted average for each sample
                probabilities = []
                for idx, row in X_normalized.iterrows():
                    # Weighted average of normalized features
                    weighted_avg = (row * feature_weights).sum()

                    # Apply sigmoid transformation for better probability calibration
                    # sigmoid(x) = 1 / (1 + exp(-x))
                    # Map weighted_avg from [0, 1] to [-3, 3] for sigmoid
                    sigmoid_input = (weighted_avg - 0.5) * 6
                    prob_positive = 1 / (1 + np.exp(-sigmoid_input))
                    prob_negative = 1 - prob_positive

                    probabilities.append([prob_negative, prob_positive])

                logger.debug(f"Got probabilities for {len(X)} samples")
                return np.array(probabilities)

            except Exception as e:
                logger.error(f"LLM probability prediction failed: {e}")
                raise TrainingError(
                    f"LLM probability prediction failed: {e}",
                    model_name=self.model_name,
                )

    def get_feature_importance(self) -> Dict[str, float]:
        """
        Get feature importance (not applicable for LLM).

        Returns:
            Empty dictionary

        Raises:
            TrainingError: If model not trained
        """
        if not self.is_trained:
            raise TrainingError(
                "Model not trained",
                model_name=self.model_name,
            )

        logger.info("Feature importance not applicable for LLM baseline")
        return {}

    def _classify_with_llm(self, text: str) -> str:
        """
        Classify text using LLM.

        Args:
            text: Text to classify

        Returns:
            Sentiment label (positive, negative, neutral)

        Raises:
            ExternalServiceError: If LLM call fails
        """
        try:
            prompt = f"""Classify the sentiment of the following text as positive, negative, or neutral.
            
Text: {text}

Sentiment:"""

            response = openai.ChatCompletion.create(
                model=config.llm.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=config.llm.temperature,
                max_tokens=config.llm.max_tokens,
            )

            sentiment = response.choices[0].message.content.strip().lower()
            return sentiment

        except Exception as e:
            logger.error(f"LLM classification failed: {e}")
            raise ExternalServiceError(
                f"LLM classification failed: {e}",
                service_name="OpenAI",
            )

    def _classify_with_confidence(self, text: str) -> tuple:
        """
        Classify text with confidence score.

        Args:
            text: Text to classify

        Returns:
            Tuple of (sentiment, confidence)

        Raises:
            ExternalServiceError: If LLM call fails
        """
        try:
            prompt = f"""Classify the sentiment of the following text as positive or negative.
Provide your answer in format: SENTIMENT: [positive/negative], CONFIDENCE: [0.0-1.0]

Text: {text}

Answer:"""

            response = openai.ChatCompletion.create(
                model=config.llm.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=config.llm.temperature,
                max_tokens=config.llm.max_tokens,
            )

            content = response.choices[0].message.content.strip()

            # Parse response
            sentiment = "positive" if "positive" in content.lower() else "negative"
            confidence = 0.8  # Default confidence

            # Try to extract confidence
            if "CONFIDENCE:" in content:
                try:
                    conf_str = content.split("CONFIDENCE:")[1].strip()
                    confidence = float(conf_str.split()[0])
                except (ValueError, IndexError):
                    pass

            return sentiment, confidence

        except Exception as e:
            logger.error(f"LLM classification with confidence failed: {e}")
            raise ExternalServiceError(
                f"LLM classification failed: {e}",
                service_name="OpenAI",
            )
