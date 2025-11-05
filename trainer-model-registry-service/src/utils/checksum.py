"""
Checksum utilities for model and data integrity verification.

Provides functions to compute and validate checksums for models and datasets.
"""

import hashlib
import logging
from pathlib import Path
from typing import Optional
import pickle
import json

logger = logging.getLogger(__name__)


def compute_file_checksum(file_path: str, algorithm: str = "sha256") -> str:
    """
    Compute checksum of a file.

    Args:
        file_path: Path to the file
        algorithm: Hash algorithm (sha256, md5, sha1)

    Returns:
        Hex digest of the file

    Raises:
        FileNotFoundError: If file does not exist
        ValueError: If algorithm is not supported
    """
    if algorithm not in ["sha256", "md5", "sha1"]:
        raise ValueError(f"Unsupported algorithm: {algorithm}")

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    hash_obj = hashlib.new(algorithm)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_obj.update(chunk)

    checksum = hash_obj.hexdigest()
    logger.debug(f"Computed {algorithm} checksum for {file_path}: {checksum}")
    return checksum


def compute_model_checksum(model_path: str, algorithm: str = "sha256") -> str:
    """
    Compute checksum of a model file.

    Args:
        model_path: Path to the model file
        algorithm: Hash algorithm

    Returns:
        Hex digest of the model

    Raises:
        FileNotFoundError: If model file does not exist
    """
    return compute_file_checksum(model_path, algorithm)


def compute_data_checksum(data: dict, algorithm: str = "sha256") -> str:
    """
    Compute checksum of data dictionary.

    Args:
        data: Dictionary to compute checksum for
        algorithm: Hash algorithm

    Returns:
        Hex digest of the data

    Raises:
        ValueError: If data cannot be serialized
    """
    try:
        # Convert to JSON for consistent serialization
        json_str = json.dumps(data, sort_keys=True, default=str)
        hash_obj = hashlib.new(algorithm)
        hash_obj.update(json_str.encode("utf-8"))
        checksum = hash_obj.hexdigest()
        logger.debug(f"Computed {algorithm} checksum for data: {checksum}")
        return checksum
    except Exception as e:
        raise ValueError(f"Failed to compute data checksum: {e}")


def compute_array_checksum(array_bytes: bytes, algorithm: str = "sha256") -> str:
    """
    Compute checksum of array/tensor bytes.

    Args:
        array_bytes: Bytes representation of array
        algorithm: Hash algorithm

    Returns:
        Hex digest of the array

    Raises:
        ValueError: If algorithm is not supported
    """
    if algorithm not in ["sha256", "md5", "sha1"]:
        raise ValueError(f"Unsupported algorithm: {algorithm}")

    hash_obj = hashlib.new(algorithm)
    hash_obj.update(array_bytes)
    checksum = hash_obj.hexdigest()
    logger.debug(f"Computed {algorithm} checksum for array: {checksum}")
    return checksum


def validate_file_checksum(
    file_path: str, expected_checksum: str, algorithm: str = "sha256"
) -> bool:
    """
    Validate file checksum.

    Args:
        file_path: Path to the file
        expected_checksum: Expected checksum value
        algorithm: Hash algorithm

    Returns:
        True if checksum matches, False otherwise

    Raises:
        FileNotFoundError: If file does not exist
    """
    computed = compute_file_checksum(file_path, algorithm)
    matches = computed == expected_checksum
    if matches:
        logger.info(f"Checksum validation passed for {file_path}")
    else:
        logger.warning(
            f"Checksum validation failed for {file_path}. "
            f"Expected: {expected_checksum}, Got: {computed}"
        )
    return matches


def validate_model_checksum(
    model_path: str, expected_checksum: str, algorithm: str = "sha256"
) -> bool:
    """
    Validate model checksum.

    Args:
        model_path: Path to the model file
        expected_checksum: Expected checksum value
        algorithm: Hash algorithm

    Returns:
        True if checksum matches, False otherwise

    Raises:
        FileNotFoundError: If model file does not exist
    """
    return validate_file_checksum(model_path, expected_checksum, algorithm)


def validate_data_checksum(
    data: dict, expected_checksum: str, algorithm: str = "sha256"
) -> bool:
    """
    Validate data checksum.

    Args:
        data: Dictionary to validate
        expected_checksum: Expected checksum value
        algorithm: Hash algorithm

    Returns:
        True if checksum matches, False otherwise
    """
    computed = compute_data_checksum(data, algorithm)
    matches = computed == expected_checksum
    if matches:
        logger.info("Data checksum validation passed")
    else:
        logger.warning(
            f"Data checksum validation failed. "
            f"Expected: {expected_checksum}, Got: {computed}"
        )
    return matches


def generate_model_metadata(
    model_path: str, model_name: str, model_version: str, algorithm: str = "sha256"
) -> dict:
    """
    Generate metadata for a model including checksum.

    Args:
        model_path: Path to the model file
        model_name: Name of the model
        model_version: Version of the model
        algorithm: Hash algorithm

    Returns:
        Dictionary with model metadata

    Raises:
        FileNotFoundError: If model file does not exist
    """
    path = Path(model_path)
    if not path.exists():
        raise FileNotFoundError(f"Model file not found: {model_path}")

    checksum = compute_model_checksum(model_path, algorithm)
    file_size = path.stat().st_size

    return {
        "model_name": model_name,
        "model_version": model_version,
        "checksum": checksum,
        "checksum_algorithm": algorithm,
        "file_size": file_size,
        "file_path": str(model_path),
    }
