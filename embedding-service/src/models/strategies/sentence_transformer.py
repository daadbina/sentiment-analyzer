"""SentenceTransformer model implementation."""

from typing import List
import numpy as np
import logging
from sentence_transformers import SentenceTransformer
import torch

from src.models.strategies.base import BaseEmbeddingModel
from src.exceptions import ModelLoadError, EmbeddingComputationError
from src.metrics import embedding_model_load_total, embedding_computation_duration_seconds
import time

logger = logging.getLogger(__name__)


class SentenceTransformerModel(BaseEmbeddingModel):
    """SentenceTransformer model implementation."""

    def load(self) -> None:
        """Load SentenceTransformer model."""
        try:
            logger.info(f"Loading SentenceTransformer model: {self.model_name}")
            start_time = time.time()

            self.model = SentenceTransformer(
                self.model_name,
                device=self.device,
                cache_folder=self.model_path,
            )

            load_time = time.time() - start_time
            self._is_loaded = True

            embedding_model_load_total.labels(
                model_name=self.model_name, status="success"
            ).inc()

            logger.info(
                f"Model loaded successfully in {load_time:.2f}s: {self.model_name}"
            )

        except Exception as e:
            embedding_model_load_total.labels(
                model_name=self.model_name, status="failure"
            ).inc()
            logger.error(f"Failed to load model {self.model_name}: {e}")
            raise ModelLoadError(f"Failed to load model {self.model_name}: {e}")

    def unload(self) -> None:
        """Unload model to free memory."""
        try:
            if self.model is not None:
                del self.model
                self.model = None
                self._is_loaded = False

                if self.device == "cuda":
                    torch.cuda.empty_cache()

                logger.debug(f"Model unloaded: {self.model_name}")

        except Exception as e:
            logger.warning(f"Error unloading model: {e}")

    def encode(
        self,
        texts: List[str],
        batch_size: int = 32,
        normalize: bool = True,
    ) -> np.ndarray:
        """
        Encode texts to embeddings using SentenceTransformer.

        Args:
            texts: List of texts to encode
            batch_size: Batch size for processing
            normalize: Whether to L2-normalize embeddings

        Returns:
            Array of shape (len(texts), embedding_dim)
        """
        if not self._is_loaded:
            raise EmbeddingComputationError("Model not loaded")

        if not texts:
            return np.array([])

        try:
            logger.debug(
                f"Encoding {len(texts)} texts with batch_size={batch_size}"
            )
            start_time = time.time()

            embeddings = self.model.encode(
                texts,
                batch_size=batch_size,
                normalize_embeddings=normalize,
                convert_to_numpy=True,
                show_progress_bar=False,
            )

            compute_time = time.time() - start_time
            embedding_computation_duration_seconds.labels(
                model_name=self.model_name, device=self.device
            ).observe(compute_time)

            logger.debug(
                f"Encoded {len(texts)} texts in {compute_time:.2f}s "
                f"({len(texts) / compute_time:.1f} texts/sec)"
            )

            return embeddings

        except Exception as e:
            logger.error(f"Embedding computation failed: {e}")
            raise EmbeddingComputationError(f"Embedding computation failed: {e}")

    def get_embedding_dimension(self) -> int:
        """Get embedding dimension."""
        if not self._is_loaded:
            raise EmbeddingComputationError("Model not loaded")

        return self.model.get_sentence_embedding_dimension()

    def get_max_sequence_length(self) -> int:
        """Get maximum sequence length."""
        if not self._is_loaded:
            raise EmbeddingComputationError("Model not loaded")

        return self.model.max_seq_length

