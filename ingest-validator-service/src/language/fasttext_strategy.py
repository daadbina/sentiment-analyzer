"""FastText language detection strategy."""

import logging
from typing import Tuple, Optional
import os

logger = logging.getLogger(__name__)

# Try to import fasttext, but handle gracefully if not available
try:
    import fasttext
    FASTTEXT_AVAILABLE = True
except ImportError:
    FASTTEXT_AVAILABLE = False
    logger.debug("fasttext not available, will use fallback language detection")


class FastTextStrategy:
    """Language detection using FastText."""

    # Model URL (pre-trained)
    MODEL_URL = "https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.ftz"
    MODEL_PATH = "/tmp/lid.176.ftz"  # nosec - temporary directory for model cache

    def __init__(self):
        """Initialize FastText strategy."""
        self.model = None
        self._load_model()

    def _load_model(self) -> None:
        """Load FastText model."""
        if not FASTTEXT_AVAILABLE:
            logger.debug("FastText not available, model will not be loaded")
            self.model = None
            return

        try:
            # Check if model exists locally
            if not os.path.exists(self.MODEL_PATH):
                logger.info(f"Downloading FastText model to {self.MODEL_PATH}")
                import urllib.request

                urllib.request.urlretrieve(self.MODEL_URL, self.MODEL_PATH)  # nosec - trusted source

            # Load model
            self.model = fasttext.load_model(self.MODEL_PATH)
            logger.info("FastText model loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load FastText model: {e}")
            self.model = None

    def detect(self, text: str) -> Tuple[Optional[str], float]:
        """Detect language using FastText.

        Args:
            text: Text to detect

        Returns:
            Tuple of (language_code, confidence)
        """
        if not self.model or not text:
            return None, 0.0

        try:
            # FastText returns language as __label__xx
            predictions = self.model.predict(text.replace("\n", " "), k=1)

            if predictions and predictions[0] and predictions[1]:
                lang_label = predictions[0][0]  # e.g., '__label__en'
                confidence = float(predictions[1][0])

                # Extract language code
                lang_code = lang_label.replace("__label__", "")

                return lang_code, confidence

            return None, 0.0

        except Exception as e:
            logger.error(f"FastText detection error: {e}")
            return None, 0.0

    def is_available(self) -> bool:
        """Check if model is available."""
        return self.model is not None
