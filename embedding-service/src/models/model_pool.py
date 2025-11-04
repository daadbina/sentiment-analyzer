"""Model pool with LRU caching using Object Pool pattern."""

import logging
from collections import OrderedDict
from typing import Dict, Optional

from src.models.model_loader import ModelLoader
from src.models.strategies.base import BaseEmbeddingModel
from src.exceptions import ModelNotFoundError
from src.metrics import embedding_models_loaded, embedding_cache_hit_rate

logger = logging.getLogger(__name__)


class ModelPool:
    """LRU cache for embedding models."""

    def __init__(
        self,
        model_loader: ModelLoader,
        max_models: int = 3,
    ):
        """
        Initialize model pool.

        Args:
            model_loader: ModelLoader instance
            max_models: Maximum number of models to keep in memory
        """
        self.model_loader = model_loader
        self.max_models = max_models
        self._models: OrderedDict[str, BaseEmbeddingModel] = OrderedDict()
        self._hits = 0
        self._misses = 0

    def get_model(
        self,
        model_name: str,
        device: str = "cpu",
    ) -> BaseEmbeddingModel:
        """
        Get a model from the pool, loading if necessary.

        Args:
            model_name: Name of the model
            device: Device to load model on

        Returns:
            Model instance

        Raises:
            ModelNotFoundError: If model is not supported
        """
        if model_name in self._models:
            # Move to end (most recently used)
            self._models.move_to_end(model_name)
            self._hits += 1
            logger.debug(f"Model cache hit: {model_name}")
        else:
            # Load new model
            logger.debug(f"Model cache miss: {model_name}")
            self._misses += 1

            # Check if we need to evict
            if len(self._models) >= self.max_models:
                evicted_name, evicted_model = self._models.popitem(last=False)
                logger.info(f"Evicting model from pool: {evicted_name}")
                evicted_model.unload()

            # Load new model
            model = self.model_loader.load_model(model_name, device)
            self._models[model_name] = model

        # Update metrics
        embedding_models_loaded.set(len(self._models))
        total_requests = self._hits + self._misses
        if total_requests > 0:
            hit_rate = self._hits / total_requests
            embedding_cache_hit_rate.set(hit_rate)

        return self._models[model_name]

    def preload_models(
        self,
        model_names: list,
        device: str = "cpu",
    ) -> None:
        """
        Preload multiple models into the pool.

        Args:
            model_names: List of model names to preload
            device: Device to load models on
        """
        for model_name in model_names:
            try:
                self.get_model(model_name, device)
                logger.info(f"Preloaded model: {model_name}")
            except Exception as e:
                logger.warning(f"Failed to preload model {model_name}: {e}")

    def clear(self) -> None:
        """Clear all models from the pool."""
        for model_name, model in self._models.items():
            try:
                model.unload()
                logger.debug(f"Unloaded model: {model_name}")
            except Exception as e:
                logger.warning(f"Error unloading model {model_name}: {e}")

        self._models.clear()
        embedding_models_loaded.set(0)
        logger.info("Model pool cleared")

    def get_stats(self) -> Dict:
        """Get pool statistics."""
        total_requests = self._hits + self._misses
        hit_rate = (
            self._hits / total_requests if total_requests > 0 else 0
        )

        return {
            "loaded_models": len(self._models),
            "max_models": self.max_models,
            "cache_hits": self._hits,
            "cache_misses": self._misses,
            "hit_rate": hit_rate,
            "model_names": list(self._models.keys()),
        }

    def __del__(self):
        """Cleanup on deletion."""
        self.clear()

