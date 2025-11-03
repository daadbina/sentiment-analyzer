"""Language detection with consensus logic."""

import logging
from typing import Tuple, Optional
from src.language.langdetect_strategy import LangdetectStrategy
from src.language.fasttext_strategy import FastTextStrategy
from src.language.transformer_strategy import TransformerStrategy
from src.config import get_config

logger = logging.getLogger(__name__)


class LanguageDetector:
    """Detects language using multi-model consensus."""

    def __init__(self):
        """Initialize language detector."""
        self.config = get_config()
        self.langdetect_strategy = LangdetectStrategy()
        self.fasttext_strategy = FastTextStrategy()
        self.transformer_strategy = TransformerStrategy()

    def detect_with_fasttext(self, text: str) -> Tuple[Optional[str], float]:
        """Detect language using FastText.

        Args:
            text: Text to detect

        Returns:
            Tuple of (language_code, confidence)
        """
        if not self.fasttext_strategy.is_available():
            return None, 0.0

        return self.fasttext_strategy.detect(text)

    def detect_with_transformer(self, text: str) -> Tuple[Optional[str], float]:
        """Detect language using Transformer.

        Args:
            text: Text to detect

        Returns:
            Tuple of (language_code, confidence)
        """
        if not self.transformer_strategy.is_available():
            return None, 0.0

        return self.transformer_strategy.detect(text)

    def detect_consensus(
        self,
        text: str,
        source_type: str = "full_article",
    ) -> Tuple[Optional[str], float, str]:
        """Detect language using consensus of available models.

        Args:
            text: Text to detect
            source_type: Type of source ("rss_summary", "full_article", etc.)

        Returns:
            Tuple of (language_code, confidence, method)
        """
        # Get threshold based on source type
        if source_type == "rss_summary":
            threshold = self.config.language.confidence_threshold_rss
        elif source_type == "full_article":
            threshold = self.config.language.confidence_threshold_full
        else:
            threshold = self.config.language.confidence_threshold_default

        logger.debug(f"Detect consensus: source_type={source_type}, threshold={threshold}, text_len={len(text)}")

        # Try Langdetect first (lightweight, always available)
        ld_lang, ld_conf = self.langdetect_strategy.detect(text)
        logger.debug(f"Langdetect result: lang={ld_lang}, conf={ld_conf}")

        if ld_lang and ld_conf >= threshold:
            logger.debug(f"Langdetect detected {ld_lang} with confidence {ld_conf:.2f}")
            return ld_lang, ld_conf, "langdetect"

        # Try FastText (if available)
        ft_lang, ft_conf = self.detect_with_fasttext(text)

        if ft_lang and ft_conf >= threshold:
            logger.debug(f"FastText detected {ft_lang} with confidence {ft_conf:.2f}")
            return ft_lang, ft_conf, "fasttext"

        # Try Transformer (if available)
        tr_lang, tr_conf = self.detect_with_transformer(text)

        if tr_lang and tr_conf >= threshold:
            logger.debug(
                f"Transformer detected {tr_lang} with confidence {tr_conf:.2f}"
            )
            return tr_lang, tr_conf, "transformer"

        # Fallback to best result
        if ld_lang and ld_conf > 0:
            logger.debug(f"Fallback to Langdetect: {ld_lang} ({ld_conf:.2f})")
            return ld_lang, ld_conf, "langdetect"

        if ft_lang and ft_conf > 0:
            logger.debug(f"Fallback to FastText: {ft_lang} ({ft_conf:.2f})")
            return ft_lang, ft_conf, "fasttext"

        if tr_lang and tr_conf > 0:
            logger.debug(f"Fallback to Transformer: {tr_lang} ({tr_conf:.2f})")
            return tr_lang, tr_conf, "transformer"

        logger.warning("Language detection failed for all models")
        return None, 0.0, "none"

    def detect(
        self,
        text: str,
        source_type: str = "full_article",
    ) -> Tuple[Optional[str], float, str]:
        """Detect language (main entry point).

        Args:
            text: Text to detect
            source_type: Type of source

        Returns:
            Tuple of (language_code, confidence, method)
        """
        if not text or not isinstance(text, str):
            return None, 0.0, "none"

        try:
            return self.detect_consensus(text, source_type)
        except Exception as e:
            logger.error(f"Language detection error: {e}")
            return None, 0.0, "error"
