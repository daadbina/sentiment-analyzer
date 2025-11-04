"""Checksum and hashing utilities for model reproducibility."""

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def compute_model_hash(model_path: str) -> str:
    """
    Compute SHA-256 hash of model artifacts for reproducibility.

    Args:
        model_path: Path to model directory or file

    Returns:
        SHA-256 hex digest
    """
    sha256 = hashlib.sha256()
    model_path_obj = Path(model_path)

    if not model_path_obj.exists():
        logger.warning(f"Model path does not exist: {model_path}")
        return ""

    try:
        if model_path_obj.is_file():
            # Single file
            with open(model_path_obj, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256.update(chunk)
        else:
            # Directory - hash all files in sorted order
            for file_path in sorted(model_path_obj.rglob("*")):
                if file_path.is_file():
                    with open(file_path, "rb") as f:
                        for chunk in iter(lambda: f.read(4096), b""):
                            sha256.update(chunk)

        hash_value = sha256.hexdigest()
        logger.debug(f"Computed model hash: {hash_value}")
        return hash_value

    except Exception as e:
        logger.error(f"Failed to compute model hash: {e}")
        raise


def compute_tokenizer_hash(tokenizer: Any) -> str:
    """
    Compute SHA-256 hash of tokenizer configuration for reproducibility.

    Args:
        tokenizer: Tokenizer object (from transformers library)

    Returns:
        SHA-256 hex digest
    """
    try:
        # Serialize tokenizer config to JSON
        config = tokenizer.to_dict() if hasattr(tokenizer, "to_dict") else {}

        # Sort keys for deterministic serialization
        config_str = json.dumps(config, sort_keys=True, default=str)

        # Compute hash
        hash_value = hashlib.sha256(config_str.encode()).hexdigest()
        logger.debug(f"Computed tokenizer hash: {hash_value}")
        return hash_value

    except Exception as e:
        logger.error(f"Failed to compute tokenizer hash: {e}")
        raise


def compute_text_hash(text: str) -> str:
    """
    Compute SHA-256 hash of text for deduplication.

    Args:
        text: Text to hash

    Returns:
        SHA-256 hex digest
    """
    return hashlib.sha256(text.encode()).hexdigest()


def compute_config_hash(config: dict) -> str:
    """
    Compute SHA-256 hash of configuration dictionary.

    Args:
        config: Configuration dictionary

    Returns:
        SHA-256 hex digest
    """
    config_str = json.dumps(config, sort_keys=True, default=str)
    return hashlib.sha256(config_str.encode()).hexdigest()

