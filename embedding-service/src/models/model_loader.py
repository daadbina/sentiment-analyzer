"""Model loader using Factory pattern."""

import logging
from typing import Dict, Optional

from src.models.strategies.base import BaseEmbeddingModel
from src.models.strategies.sentence_transformer import SentenceTransformerModel
from src.exceptions import ModelNotFoundError, ModelLoadError

logger = logging.getLogger(__name__)


class ModelLoader:
    """Factory for loading embedding models."""

    # Supported model types
    SUPPORTED_MODELS = {
        # Multilingual models
        "paraphrase-multilingual-mpnet-base-v2": "sentence_transformer",
        "paraphrase-multilingual-MiniLM-L12-v2": "sentence_transformer",
        "multilingual-e5-base": "sentence_transformer",
        "multilingual-e5-large": "sentence_transformer",
        # English models
        "all-mpnet-base-v2": "sentence_transformer",
        "all-MiniLM-L6-v2": "sentence_transformer",
        "all-MiniLM-L12-v2": "sentence_transformer",
        # Domain-specific
        "nli-mpnet-base-v2": "sentence_transformer",
        "nli-MiniLM-L6-v2": "sentence_transformer",
    }

    def __init__(self, model_cache_dir: str = "/models"):
        """
        Initialize model loader.

        Args:
            model_cache_dir: Directory to cache downloaded models
        """
        self.model_cache_dir = model_cache_dir
        self._loaded_models: Dict[str, BaseEmbeddingModel] = {}

    def load_model(
        self,
        model_name: str,
        device: str = "cpu",
    ) -> BaseEmbeddingModel:
        """
        Load a model by name.

        Args:
            model_name: Name of the model to load
            device: Device to load model on ("cuda" or "cpu")

        Returns:
            Loaded model instance

        Raises:
            ModelNotFoundError: If model is not supported
            ModelLoadError: If model loading fails
        """
        if model_name not in self.SUPPORTED_MODELS:
            raise ModelNotFoundError(
                f"Model not supported: {model_name}. "
                f"Supported models: {list(self.SUPPORTED_MODELS.keys())}"
            )

        model_type = self.SUPPORTED_MODELS[model_name]

        logger.info(f"Loading model: {model_name} (type: {model_type})")

        if model_type == "sentence_transformer":
            model = SentenceTransformerModel(
                model_name=model_name,
                device=device,
                model_path=self.model_cache_dir,
            )
        else:
            raise ModelNotFoundError(f"Unknown model type: {model_type}")

        model.load()
        return model

    def get_supported_models(self) -> Dict[str, str]:
        """Get dictionary of supported models and their types."""
        return self.SUPPORTED_MODELS.copy()

    def is_model_supported(self, model_name: str) -> bool:
        """Check if a model is supported."""
        return model_name in self.SUPPORTED_MODELS

