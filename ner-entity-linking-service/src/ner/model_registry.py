"""NER model registry and factory."""

import logging
from typing import Dict, Optional
from src.ner.base_strategy import NERStrategy
from src.ner.spacy_strategy import SpacyNERStrategy
from src.ner.huggingface_strategy import HuggingFaceNERStrategy
from src.exceptions import UnsupportedLanguageError

logger = logging.getLogger(__name__)


class NERModelRegistry:
    """Registry for NER models by language."""

    # Language to model mapping (all using HuggingFace)
    LANGUAGE_MODELS = {
        "en": ("huggingface", "dslim/bert-base-uncased-finetuned-ner"),
        "fa": ("huggingface", "HooshvareLab/bert-fa-base-uncased-ner"),
        "ru": ("huggingface", "DeepPavlov/bert-base-multilingual-cased"),
        "zh": ("huggingface", "bert-base-chinese"),
        "ar": ("huggingface", "CAMeL-Lab/bert-base-arabic-camelbert-mix-ner"),
        "de": ("huggingface", "dslim/bert-base-multilingual-cased-finetuned-ner"),
        "fr": ("huggingface", "dslim/bert-base-multilingual-cased-finetuned-ner"),
        "es": ("huggingface", "dslim/bert-base-multilingual-cased-finetuned-ner"),
        "ja": ("huggingface", "dslim/bert-base-multilingual-cased-finetuned-ner"),
        "ko": ("huggingface", "dslim/bert-base-multilingual-cased-finetuned-ner"),
        "it": ("huggingface", "dslim/bert-base-multilingual-cased-finetuned-ner"),
        "pt": ("huggingface", "dslim/bert-base-multilingual-cased-finetuned-ner"),
        "tr": ("huggingface", "dslim/bert-base-multilingual-cased-finetuned-ner"),
        "hi": ("huggingface", "dslim/bert-base-multilingual-cased-finetuned-ner"),
    }

    def __init__(self, max_models: int = 5):
        """
        Initialize model registry.

        Args:
            max_models: Maximum number of models to keep in memory
        """
        self.max_models = max_models
        self.models: Dict[str, NERStrategy] = {}
        self.model_usage_order: list = []

    def get_model(self, language: str) -> NERStrategy:
        """
        Get NER model for language.

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

        # Load new model
        model_type, model_name = self.LANGUAGE_MODELS[language]
        logger.info(f"Loading NER model for {language}: {model_name}")

        if model_type == "spacy":
            strategy = SpacyNERStrategy(language, model_name)
        elif model_type == "huggingface":
            strategy = HuggingFaceNERStrategy(language, model_name)
        else:
            raise ValueError(f"Unknown model type: {model_type}")

        strategy.load_model()
        self.models[language] = strategy
        self.model_usage_order.append(language)

        # Evict least recently used model if cache full
        if len(self.models) > self.max_models:
            lru_language = self.model_usage_order.pop(0)
            logger.info(f"Evicting LRU model for language: {lru_language}")
            self.models[lru_language].unload_model()
            del self.models[lru_language]

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

