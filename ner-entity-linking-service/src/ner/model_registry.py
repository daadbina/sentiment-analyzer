"""NER model registry and factory."""

import logging
from typing import Dict, Optional
from src.ner.base_strategy import NERStrategy
from src.ner.spacy_strategy import SpacyNERStrategy
from src.ner.huggingface_strategy import HuggingFaceNERStrategy
from src.exceptions import UnsupportedLanguageError

logger = logging.getLogger(__name__)


class NERModelRegistry:
    """Registry for NER models by language.

    Optimized to share the same model instance across languages when they use
    the same underlying model (e.g., xlm-roberta-large for all languages).
    """

    # Language to model mapping (all using HuggingFace - publicly available NER-specific models)
    LANGUAGE_MODELS = {
        "en": ("huggingface", "xlm-roberta-large-finetuned-conll03-english"),
        "fa": ("huggingface", "xlm-roberta-large-finetuned-conll03-english"),
        "ru": ("huggingface", "xlm-roberta-large-finetuned-conll03-english"),
        "zh": ("huggingface", "xlm-roberta-large-finetuned-conll03-english"),
        "ar": ("huggingface", "xlm-roberta-large-finetuned-conll03-english"),
        "de": ("huggingface", "xlm-roberta-large-finetuned-conll03-english"),
        "fr": ("huggingface", "xlm-roberta-large-finetuned-conll03-english"),
        "es": ("huggingface", "xlm-roberta-large-finetuned-conll03-english"),
        "ja": ("huggingface", "xlm-roberta-large-finetuned-conll03-english"),
        "ko": ("huggingface", "xlm-roberta-large-finetuned-conll03-english"),
        "it": ("huggingface", "xlm-roberta-large-finetuned-conll03-english"),
        "pt": ("huggingface", "xlm-roberta-large-finetuned-conll03-english"),
        "tr": ("huggingface", "xlm-roberta-large-finetuned-conll03-english"),
        "hi": ("huggingface", "xlm-roberta-large-finetuned-conll03-english"),
    }

    def __init__(self, max_models: int = 5):
        """
        Initialize model registry.

        Args:
            max_models: Maximum number of models to keep in memory
        """
        self.max_models = max_models
        self.models: Dict[str, NERStrategy] = {}  # language -> strategy
        self.model_usage_order: list = []
        # Cache for actual model instances by model_name to avoid loading same model multiple times
        self._model_instances: Dict[str, NERStrategy] = {}  # model_name -> strategy instance

    def get_model(self, language: str) -> NERStrategy:
        """
        Get NER model for language.

        Optimized to share the same model instance across languages when they use
        the same underlying model (e.g., xlm-roberta-large for all languages).

        Args:
            language: Language code

        Returns:
            NER strategy instance

        Raises:
            UnsupportedLanguageError: If language not supported
        """
        if language not in self.LANGUAGE_MODELS:
            raise UnsupportedLanguageError(language)

        # Return cached model if available
        if language in self.models:
            self.model_usage_order.remove(language)
            self.model_usage_order.append(language)
            logger.debug(f"Using cached model for language: {language}")
            return self.models[language]

        # Get model configuration
        model_type, model_name = self.LANGUAGE_MODELS[language]

        # Check if we already have this model loaded for another language
        if model_name in self._model_instances:
            logger.info(f"Reusing existing model instance '{model_name}' for language: {language}")
            strategy = self._model_instances[model_name]
            self.models[language] = strategy
            self.model_usage_order.append(language)
            return strategy

        # Load new model
        logger.info(f"Loading NER model for {language}: {model_name}")

        if model_type == "spacy":
            strategy = SpacyNERStrategy(language, model_name)
        elif model_type == "huggingface":
            strategy = HuggingFaceNERStrategy(language, model_name)
        else:
            raise ValueError(f"Unknown model type: {model_type}")

        strategy.load_model()
        self.models[language] = strategy
        self._model_instances[model_name] = strategy
        self.model_usage_order.append(language)

        # Evict least recently used model if cache full
        # Note: We only evict if we have too many UNIQUE models, not language mappings
        if len(self._model_instances) > self.max_models:
            # Find the LRU language that uses a unique model
            for lru_language in self.model_usage_order:
                lru_model_type, lru_model_name = self.LANGUAGE_MODELS[lru_language]
                # Check if this model is only used by this language
                languages_using_model = [
                    lang for lang in self.models.keys()
                    if self.LANGUAGE_MODELS[lang][1] == lru_model_name
                ]
                if len(languages_using_model) == 1:
                    # This is the only language using this model, safe to evict
                    logger.info(f"Evicting LRU model for language: {lru_language} (model: {lru_model_name})")
                    self.models[lru_language].unload_model()
                    del self.models[lru_language]
                    del self._model_instances[lru_model_name]
                    self.model_usage_order.remove(lru_language)
                    break

        return strategy

    def unload_all(self) -> None:
        """Unload all cached models."""
        for language, strategy in self.models.items():
            logger.info(f"Unloading model for language: {language}")
            strategy.unload_model()
        self.models.clear()
        self.model_usage_order.clear()

    def get_supported_languages(self) -> list:
        """Get list of supported languages."""
        return list(self.LANGUAGE_MODELS.keys())

    def is_language_supported(self, language: str) -> bool:
        """Check if language is supported."""
        return language in self.LANGUAGE_MODELS

