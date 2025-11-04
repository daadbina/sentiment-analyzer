"""Tokenizer management for model-specific tokenization."""

import logging
from typing import List, Dict, Optional
from transformers import AutoTokenizer

from src.exceptions import TokenizationError
from src.utils.checksum import compute_tokenizer_hash

logger = logging.getLogger(__name__)


class TokenizerManager:
    """Manages tokenizers for different models."""

    def __init__(self, model_cache_dir: str = "/models"):
        """
        Initialize tokenizer manager.

        Args:
            model_cache_dir: Directory to cache tokenizers
        """
        self.model_cache_dir = model_cache_dir
        self._tokenizers: Dict[str, any] = {}

    def get_tokenizer(self, model_name: str):
        """
        Get or load tokenizer for a model.

        Args:
            model_name: Name of the model

        Returns:
            Tokenizer instance

        Raises:
            TokenizationError: If tokenizer loading fails
        """
        if model_name in self._tokenizers:
            logger.debug(f"Using cached tokenizer for {model_name}")
            return self._tokenizers[model_name]

        try:
            logger.info(f"Loading tokenizer for {model_name}")
            tokenizer = AutoTokenizer.from_pretrained(
                model_name,
                cache_dir=self.model_cache_dir,
                trust_remote_code=True,
            )

            # Compute hash for reproducibility
            tokenizer_hash = compute_tokenizer_hash(tokenizer)
            logger.debug(f"Tokenizer hash: {tokenizer_hash}")

            self._tokenizers[model_name] = tokenizer
            return tokenizer

        except Exception as e:
            logger.error(f"Failed to load tokenizer for {model_name}: {e}")
            raise TokenizationError(
                f"Failed to load tokenizer for {model_name}: {e}"
            )

    def tokenize(
        self,
        texts: List[str],
        model_name: str,
        max_length: int = 384,
        truncation: bool = True,
        padding: bool = True,
    ) -> Dict:
        """
        Tokenize texts using model-specific tokenizer.

        Args:
            texts: List of texts to tokenize
            model_name: Name of the model
            max_length: Maximum sequence length
            truncation: Whether to truncate long sequences
            padding: Whether to pad sequences

        Returns:
            Dictionary with input_ids, attention_mask, etc.

        Raises:
            TokenizationError: If tokenization fails
        """
        try:
            tokenizer = self.get_tokenizer(model_name)

            logger.debug(
                f"Tokenizing {len(texts)} texts with max_length={max_length}"
            )

            encoded = tokenizer(
                texts,
                max_length=max_length,
                truncation=truncation,
                padding=padding,
                return_tensors="pt",
            )

            return encoded

        except Exception as e:
            logger.error(f"Tokenization failed: {e}")
            raise TokenizationError(f"Tokenization failed: {e}")

    def get_token_count(
        self,
        text: str,
        model_name: str,
    ) -> int:
        """
        Get token count for a text.

        Args:
            text: Text to count tokens for
            model_name: Name of the model

        Returns:
            Number of tokens
        """
        try:
            tokenizer = self.get_tokenizer(model_name)
            tokens = tokenizer.encode(text)
            return len(tokens)
        except Exception as e:
            logger.warning(f"Failed to count tokens: {e}")
            return 0

    def clear_cache(self) -> None:
        """Clear cached tokenizers."""
        self._tokenizers.clear()
        logger.info("Tokenizer cache cleared")

