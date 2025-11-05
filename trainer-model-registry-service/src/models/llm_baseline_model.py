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
            "model": config.llm.model_name,
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
        Make predictions using LLM.

        Args:
            X: Features for prediction (should contain text)

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

                predictions = []
                for idx, row in X.iterrows():
                    # Extract text from row (assuming 'text' column)
                    text = row.get("text", "")
                    if not text:
                        predictions.append(0)
                        continue

                    # Call LLM
                    sentiment = self._classify_with_llm(text)
                    predictions.append(1 if sentiment == "positive" else 0)

                logger.debug(f"Made predictions for {len(X)} samples")
                return np.array(predictions)

            except Exception as e:
                logger.error(f"LLM prediction failed: {e}")
                raise TrainingError(
                    f"LLM prediction failed: {e}",
                    model_name=self.model_name,
                )

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """
        Get prediction probabilities using LLM.

        Args:
            X: Features for prediction

        Returns:
            Prediction probabilities

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

                probabilities = []
                for idx, row in X.iterrows():
                    text = row.get("text", "")
                    if not text:
                        probabilities.append([1.0, 0.0])
                        continue

                    # Call LLM with confidence
                    sentiment, confidence = self._classify_with_confidence(text)
                    if sentiment == "positive":
                        probabilities.append([confidence, 1 - confidence])
                    else:
                        probabilities.append([1 - confidence, confidence])

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
