"""HuggingFace Transformer model strategy for embeddings."""

import logging
from typing import List
import numpy as np
import torch
from transformers import AutoTokenizer, AutoModel

from .base import BaseEmbeddingModel
from src.exceptions import ModelLoadError

logger = logging.getLogger(__name__)


class HuggingFaceTransformerModel(BaseEmbeddingModel):
    """HuggingFace Transformer model strategy using mean pooling."""

    def __init__(
        self,
        model_name: str,
        device: str = "cpu",
        model_path: str = None,
        cache_dir: str = None,
    ):
        """
        Initialize HuggingFace Transformer model.

        Args:
            model_name: HuggingFace model identifier
            device: Device to run model on ("cuda" or "cpu")
            model_path: Optional path to local model
            cache_dir: Directory to cache models
        """
        super().__init__(model_name, device, model_path)
        self.cache_dir = cache_dir
        self.embedding_dim = None

    def load(self) -> None:
        """Load HuggingFace model and tokenizer."""
        try:
            logger.info(f"Loading HuggingFace model: {self.model_name}")

            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_path or self.model_name,
                cache_dir=self.cache_dir,
                trust_remote_code=True,
            )

            # Load model
            self.model = AutoModel.from_pretrained(
                self.model_path or self.model_name,
                cache_dir=self.cache_dir,
                trust_remote_code=True,
            )

            # Move to device
            self.model = self.model.to(self.device)
            self.model.eval()

            # Get embedding dimension
            self.embedding_dim = self.model.config.hidden_size

            self._is_loaded = True
            logger.info(
                f"Successfully loaded {self.model_name} "
                f"(dim={self.embedding_dim}) on {self.device}"
            )

        except Exception as e:
            logger.error(f"Failed to load HuggingFace model: {e}")
            raise ModelLoadError(f"Failed to load {self.model_name}: {str(e)}")

    def unload(self) -> None:
        """Unload model and tokenizer to free memory."""
        try:
            if self.model is not None:
                del self.model
            if self.tokenizer is not None:
                del self.tokenizer

            if self.device == "cuda":
                torch.cuda.empty_cache()

            self._is_loaded = False
            logger.info(f"Unloaded model {self.model_name}")

        except Exception as e:
            logger.error(f"Error unloading model: {e}")

    def encode(
        self,
        texts: List[str],
        batch_size: int = 32,
        normalize: bool = True,
    ) -> np.ndarray:
        """
        Encode texts to embeddings using mean pooling.

        Args:
            texts: List of texts to encode
            batch_size: Batch size for processing
            normalize: Whether to L2-normalize embeddings

        Returns:
            Array of shape (len(texts), embedding_dim)
        """
        if not self._is_loaded:
            raise RuntimeError("Model not loaded. Call load() first.")

        embeddings = []

        with torch.no_grad():
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i : i + batch_size]

                # Tokenize
                encoded = self.tokenizer(
                    batch_texts,
                    padding=True,
                    truncation=True,
                    max_length=self.get_max_sequence_length(),
                    return_tensors="pt",
                )

                # Move to device
                encoded = {k: v.to(self.device) for k, v in encoded.items()}

                # Forward pass
                outputs = self.model(**encoded)

                # Mean pooling
                attention_mask = encoded["attention_mask"]
                last_hidden = outputs.last_hidden_state

                # Expand mask for broadcasting
                mask_expanded = (
                    attention_mask.unsqueeze(-1)
                    .expand(last_hidden.size())
                    .float()
                )

                # Sum and divide by attention mask sum
                sum_hidden = (last_hidden * mask_expanded).sum(1)
                sum_mask = mask_expanded.sum(1)
                batch_embeddings = sum_hidden / sum_mask.clamp(min=1e-9)

                # Normalize if requested
                if normalize:
                    batch_embeddings = torch.nn.functional.normalize(
                        batch_embeddings, p=2, dim=1
                    )

                embeddings.append(batch_embeddings.cpu().numpy())

        return np.vstack(embeddings)

    def get_embedding_dimension(self) -> int:
        """Get embedding dimension."""
        if not self._is_loaded:
            raise RuntimeError("Model not loaded. Call load() first.")
        return self.embedding_dim

    def get_max_sequence_length(self) -> int:
        """Get maximum sequence length supported by model."""
        if not self._is_loaded:
            raise RuntimeError("Model not loaded. Call load() first.")
        return self.model.config.max_position_embeddings

