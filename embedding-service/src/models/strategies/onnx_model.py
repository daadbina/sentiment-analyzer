"""ONNX model strategy for optimized embeddings."""

import logging
from typing import List
import numpy as np
import onnxruntime as ort
from transformers import AutoTokenizer

from .base import BaseEmbeddingModel
from ..exceptions import ModelLoadError

logger = logging.getLogger(__name__)


class ONNXModel(BaseEmbeddingModel):
    """ONNX model strategy for optimized inference."""

    def __init__(
        self,
        model_name: str,
        device: str = "cpu",
        model_path: str = None,
        cache_dir: str = None,
        onnx_model_path: str = None,
    ):
        """
        Initialize ONNX model.

        Args:
            model_name: Model identifier
            device: Device to run model on ("cuda" or "cpu")
            model_path: Optional path to local model
            cache_dir: Directory to cache models
            onnx_model_path: Path to ONNX model file
        """
        super().__init__(model_name, device, model_path)
        self.cache_dir = cache_dir
        self.onnx_model_path = onnx_model_path
        self.session = None
        self.embedding_dim = None
        self.max_seq_length = None

    def load(self) -> None:
        """Load ONNX model and tokenizer."""
        try:
            logger.info(f"Loading ONNX model: {self.model_name}")

            # Load tokenizer from HuggingFace
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_path or self.model_name,
                cache_dir=self.cache_dir,
                trust_remote_code=True,
            )

            # Set up ONNX Runtime session
            providers = (
                ["CUDAExecutionProvider", "CPUExecutionProvider"]
                if self.device == "cuda"
                else ["CPUExecutionProvider"]
            )

            session_options = ort.SessionOptions()
            session_options.graph_optimization_level = (
                ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            )

            self.session = ort.InferenceSession(
                self.onnx_model_path,
                sess_options=session_options,
                providers=providers,
            )

            # Get model info
            input_names = [input.name for input in self.session.get_inputs()]
            output_names = [output.name for output in self.session.get_outputs()]

            logger.info(f"ONNX model inputs: {input_names}")
            logger.info(f"ONNX model outputs: {output_names}")

            # Infer embedding dimension from output shape
            output_shape = self.session.get_outputs()[0].shape
            self.embedding_dim = output_shape[-1] if output_shape[-1] > 0 else 768

            # Get max sequence length from tokenizer
            self.max_seq_length = (
                self.tokenizer.model_max_length
                if hasattr(self.tokenizer, "model_max_length")
                else 512
            )

            self._is_loaded = True
            logger.info(
                f"Successfully loaded ONNX model {self.model_name} "
                f"(dim={self.embedding_dim}, max_seq={self.max_seq_length})"
            )

        except Exception as e:
            logger.error(f"Failed to load ONNX model: {e}")
            raise ModelLoadError(f"Failed to load {self.model_name}: {str(e)}")

    def unload(self) -> None:
        """Unload model and tokenizer to free memory."""
        try:
            if self.session is not None:
                del self.session
                self.session = None

            if self.tokenizer is not None:
                del self.tokenizer
                self.tokenizer = None

            self._is_loaded = False
            logger.info(f"Unloaded ONNX model {self.model_name}")

        except Exception as e:
            logger.error(f"Error unloading model: {e}")

    def encode(
        self,
        texts: List[str],
        batch_size: int = 32,
        normalize: bool = True,
    ) -> np.ndarray:
        """
        Encode texts to embeddings using ONNX model.

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

        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i : i + batch_size]

            # Tokenize
            encoded = self.tokenizer(
                batch_texts,
                padding=True,
                truncation=True,
                max_length=self.max_seq_length,
                return_tensors="np",
            )

            # Prepare inputs for ONNX
            onnx_inputs = {
                "input_ids": encoded["input_ids"].astype(np.int64),
                "attention_mask": encoded["attention_mask"].astype(np.int64),
            }

            # Add token_type_ids if present
            if "token_type_ids" in encoded:
                onnx_inputs["token_type_ids"] = encoded["token_type_ids"].astype(
                    np.int64
                )

            # Run inference
            outputs = self.session.run(None, onnx_inputs)

            # Extract embeddings (usually last hidden state)
            batch_embeddings = outputs[0]

            # Mean pooling
            attention_mask = encoded["attention_mask"]
            mask_expanded = np.expand_dims(attention_mask, axis=-1)
            sum_embeddings = (batch_embeddings * mask_expanded).sum(axis=1)
            sum_mask = mask_expanded.sum(axis=1)
            batch_embeddings = sum_embeddings / np.maximum(sum_mask, 1e-9)

            # Normalize if requested
            if normalize:
                norms = np.linalg.norm(batch_embeddings, axis=1, keepdims=True)
                batch_embeddings = batch_embeddings / np.maximum(norms, 1e-9)

            embeddings.append(batch_embeddings)

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
        return self.max_seq_length

