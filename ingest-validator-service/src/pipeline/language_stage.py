"""Language detection stage."""

import logging
from src.pipeline.stage import ValidationStage
from src.models import ValidationContext
from src.language.detector import LanguageDetector

logger = logging.getLogger(__name__)


class LanguageDetectionStage(ValidationStage):
    """Detects language using consensus (R2)."""

    def __init__(self):
        """Initialize language detection stage."""
        super().__init__("LanguageDetection")
        self.detector = LanguageDetector()

    async def execute(self, context: ValidationContext) -> ValidationContext:
        """Execute language detection.

        Args:
            context: Validation context

        Returns:
            Updated validation context
        """
        try:
            # Combine title and body for detection
            text_to_detect = f"{context.title} {context.body}"

            logger.debug(f"[{self.name}] Text length: {len(text_to_detect)}, Title: {len(context.title)}, Body: {len(context.body)}")
            logger.debug(f"[{self.name}] Text sample: {text_to_detect[:100]}")

            # Detect language (use rss_summary for RSS feeds, full_article for others)
            # Most data comes from RSS feeds with short summaries
            source_type = "rss_summary" if context.source else "full_article"

            logger.debug(f"[{self.name}] Using source_type: {source_type}")

            lang_code, confidence, method = self.detector.detect(
                text_to_detect,
                source_type=source_type,
            )

            logger.debug(f"[{self.name}] Detection result: lang={lang_code}, conf={confidence}, method={method}")

            if not lang_code:
                self._add_error(context, "Language detection failed")
                context.validation_details.language_detected = False
                logger.warning(f"[{self.name}] Language detection failed for article {context.article_id}")
                return context

            context.language = lang_code
            context.language_confidence = confidence
            context.language_detection_method = method
            context.validation_details.language_detected = True

            logger.debug(
                f"[{self.name}] Detected language {lang_code} "
                f"with confidence {confidence:.2f} using {method}"
            )

            return context

        except Exception as e:
            logger.error(f"[{self.name}] Detection error: {e}")
            self._add_error(context, f"Language detection error: {e}")
            context.validation_details.language_detected = False
            return context
