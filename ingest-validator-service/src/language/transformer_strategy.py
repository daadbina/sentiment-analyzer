"""Transformer-based language detection strategy."""

import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

# Try to import transformers, but handle gracefully if not available
try:
    from transformers import pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logger.debug("transformers not available, will use fallback language detection")


class TransformerStrategy:
    """Language detection using XLM-RoBERTa transformer."""

    # Model name
    MODEL_NAME = "xlm-roberta-base"

    def __init__(self):
        """Initialize Transformer strategy."""
        self.classifier = None
        self._load_model()

    def _load_model(self) -> None:
        """Load transformer model."""
        if not TRANSFORMERS_AVAILABLE:
            logger.debug("Transformers not available, model will not be loaded")
            self.classifier = None
            return

        try:
            # Load zero-shot classification pipeline
            # This uses XLM-RoBERTa for multilingual support
            self.classifier = pipeline(
                "zero-shot-classification",
                model="facebook/bart-large-mnli",
                device=-1,  # CPU
            )
            logger.info("Transformer model loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load transformer model: {e}")
            self.classifier = None

    def detect(self, text: str) -> Tuple[Optional[str], float]:
        """Detect language using transformer.

        Args:
            text: Text to detect

        Returns:
            Tuple of (language_code, confidence)
        """
        if not self.classifier or not text:
            return None, 0.0

        try:
            # Language candidates
            languages = [
                "English",
                "Persian",
                "Russian",
                "Chinese",
                "Arabic",
                "Spanish",
                "French",
                "German",
                "Italian",
                "Portuguese",
            ]

            # Classify
            result = self.classifier(
                text[:512],  # Limit to 512 chars for efficiency
                languages,
                multi_class=False,
            )

            if result and result.get("labels"):
                top_label = result["labels"][0]
                confidence = float(result["scores"][0])

                # Map language name to code
                lang_map = {
                    "English": "en",
                    "Persian": "fa",
                    "Russian": "ru",
                    "Chinese": "zh",
                    "Arabic": "ar",
                    "Spanish": "es",
                    "French": "fr",
                    "German": "de",
                    "Italian": "it",
                    "Portuguese": "pt",
                }

                lang_code = lang_map.get(top_label, top_label.lower()[:2])

                return lang_code, confidence

            return None, 0.0

        except Exception as e:
            logger.error(f"Transformer detection error: {e}")
            return None, 0.0

    def is_available(self) -> bool:
        """Check if model is available."""
        return self.classifier is not None
