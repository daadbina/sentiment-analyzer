#!/usr/bin/env python3
"""Basic functionality test for embedding service."""

import sys
import logging
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_basic_functionality():
    """Test basic embedding service functionality."""
    try:
        logger.info("Testing embedding service imports...")
        from src.config import config
        logger.info(f"Config loaded: device={config.model.device}")
        
        from src.preprocessing.text_preprocessor import TextPreprocessor
        preprocessor = TextPreprocessor()
        logger.info("TextPreprocessor initialized")
        
        # Test text preprocessing
        test_text = "This is a test article about technology and AI."
        preprocessed = preprocessor.preprocess(test_text)
        logger.info(f"Text preprocessing test passed: '{test_text}' -> '{preprocessed}'")
        
        from src.embedding.normalization import normalize_l2
        test_embedding = np.random.randn(768).astype(np.float32)
        normalized = normalize_l2(test_embedding.reshape(1, -1))[0]
        norm_value = np.linalg.norm(normalized)
        logger.info(f"Normalization test passed: norm={norm_value:.4f}")
        
        from src.validation.embedding_validator import EmbeddingValidator
        validator = EmbeddingValidator(expected_dimension=768)
        result = validator.validate_embedding(normalized)
        is_valid = result["valid"]
        logger.info(f"Validation test passed: valid={is_valid}")
        
        if not is_valid:
            logger.error(f"Validation failed: {result['errors']}")
            return False
        
        # Test batch validation
        batch_embeddings = np.random.randn(5, 768).astype(np.float32)
        batch_embeddings = normalize_l2(batch_embeddings)
        batch_result = validator.validate_batch(batch_embeddings)
        logger.info(f"Batch validation test passed: valid_count={batch_result['valid_count']}/{batch_result['total']}")
        
        logger.info("✅ All basic functionality tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = test_basic_functionality()
    sys.exit(0 if success else 1)

