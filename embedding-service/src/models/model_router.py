"""Model router for language and domain-based model selection."""

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class ModelRouter:
    """Routes to appropriate model based on language and domain."""

    # Language to model mapping
    LANGUAGE_MODELS = {
        "en": "all-mpnet-base-v2",
        "es": "paraphrase-multilingual-mpnet-base-v2",
        "fr": "paraphrase-multilingual-mpnet-base-v2",
        "de": "paraphrase-multilingual-mpnet-base-v2",
        "it": "paraphrase-multilingual-mpnet-base-v2",
        "pt": "paraphrase-multilingual-mpnet-base-v2",
        "nl": "paraphrase-multilingual-mpnet-base-v2",
        "ru": "paraphrase-multilingual-mpnet-base-v2",
        "zh": "paraphrase-multilingual-mpnet-base-v2",
        "ja": "paraphrase-multilingual-mpnet-base-v2",
        "ko": "paraphrase-multilingual-mpnet-base-v2",
        "ar": "paraphrase-multilingual-mpnet-base-v2",
        "hi": "paraphrase-multilingual-mpnet-base-v2",
        "tr": "paraphrase-multilingual-mpnet-base-v2",
    }

    # Domain to model mapping (optional, can override language model)
    DOMAIN_MODELS = {
        "news": "all-mpnet-base-v2",
        "social_media": "all-MiniLM-L12-v2",
        "academic": "nli-mpnet-base-v2",
        "legal": "nli-mpnet-base-v2",
    }

    # Fallback model for unsupported languages
    FALLBACK_MODEL = "paraphrase-multilingual-mpnet-base-v2"

    def __init__(self):
        """Initialize model router."""
        self.language_models = self.LANGUAGE_MODELS.copy()
        self.domain_models = self.DOMAIN_MODELS.copy()

    def select_model(
        self,
        language: str,
        domain: Optional[str] = None,
    ) -> str:
        """
        Select appropriate model based on language and domain.

        Args:
            language: Language code (e.g., "en", "es")
            domain: Optional domain (e.g., "news", "academic")

        Returns:
            Model name to use
        """
        # Check domain first if provided
        if domain and domain in self.domain_models:
            model = self.domain_models[domain]
            logger.debug(
                f"Selected model for domain '{domain}': {model}"
            )
            return model

        # Fall back to language
        language_lower = language.lower()
        if language_lower in self.language_models:
            model = self.language_models[language_lower]
            logger.debug(
                f"Selected model for language '{language}': {model}"
            )
            return model

        # Use fallback
        logger.warning(
            f"Language '{language}' not found, using fallback model: "
            f"{self.FALLBACK_MODEL}"
        )
        return self.FALLBACK_MODEL

    def register_language_model(
        self,
        language: str,
        model_name: str,
    ) -> None:
        """Register a model for a language."""
        self.language_models[language.lower()] = model_name
        logger.info(f"Registered model '{model_name}' for language '{language}'")

    def register_domain_model(
        self,
        domain: str,
        model_name: str,
    ) -> None:
        """Register a model for a domain."""
        self.domain_models[domain.lower()] = model_name
        logger.info(f"Registered model '{model_name}' for domain '{domain}'")

    def get_supported_languages(self) -> list:
        """Get list of supported languages."""
        return list(self.language_models.keys())

    def get_supported_domains(self) -> list:
        """Get list of supported domains."""
        return list(self.domain_models.keys())

