"""
Unit tests for exceptions module.
"""

import pytest

from src.exceptions import (
    PredictionError,
    ModelLoadError,
    FeatureError,
    FeatureFetchError,
    FeatureValidationError,
    FeatureReconciliationError,
    InferenceError,
    InferenceTimeoutError,
    LabelValidationError,
    LabelFetchError,
    CacheError,
    KafkaError,
    PostgresError,
)


class TestPredictionError:
    """Tests for PredictionError base class."""
    
    def test_create_with_message(self):
        """Test creating exception with message."""
        error = PredictionError("Test error")
        assert str(error) == "Test error"
        assert error.group_id is None
        assert error.trace_id is None
    
    def test_create_with_context(self):
        """Test creating exception with context."""
        error = PredictionError(
            "Test error",
            group_id="group_123",
            trace_id="trace_456",
        )
        assert str(error) == "Test error"
        assert error.group_id == "group_123"
        assert error.trace_id == "trace_456"


class TestModelLoadError:
    """Tests for ModelLoadError."""
    
    def test_create_with_model_version(self):
        """Test creating exception with model version."""
        error = ModelLoadError(
            "Failed to load model",
            model_version="v1.0.0",
        )
        assert "Failed to load model" in str(error)
        assert error.model_version == "v1.0.0"


class TestFeatureError:
    """Tests for FeatureError."""
    
    def test_create_with_feature_name(self):
        """Test creating exception with feature name."""
        error = FeatureError(
            "Feature error",
            feature_name="feature_num_sources",
        )
        assert "Feature error" in str(error)
        assert error.feature_name == "feature_num_sources"


class TestFeatureFetchError:
    """Tests for FeatureFetchError."""
    
    def test_create_with_store_type(self):
        """Test creating exception with store type."""
        error = FeatureFetchError(
            "Failed to fetch features",
            store_type="online",
        )
        assert "Failed to fetch features" in str(error)
        assert error.store_type == "online"


class TestFeatureValidationError:
    """Tests for FeatureValidationError."""
    
    def test_create_with_validation_type(self):
        """Test creating exception with validation type."""
        error = FeatureValidationError(
            "Feature validation failed",
            validation_type="missing",
        )
        assert "Feature validation failed" in str(error)
        assert error.validation_type == "missing"


class TestFeatureReconciliationError:
    """Tests for FeatureReconciliationError."""
    
    def test_create_with_mismatch_rate(self):
        """Test creating exception with mismatch rate."""
        error = FeatureReconciliationError(
            "Reconciliation failed",
            mismatch_rate=0.05,
        )
        assert "Reconciliation failed" in str(error)
        assert error.mismatch_rate == 0.05


class TestInferenceError:
    """Tests for InferenceError."""
    
    def test_create_basic(self):
        """Test creating basic inference error."""
        error = InferenceError("Inference failed")
        assert str(error) == "Inference failed"


class TestInferenceTimeoutError:
    """Tests for InferenceTimeoutError."""
    
    def test_create_with_timeout(self):
        """Test creating exception with timeout."""
        error = InferenceTimeoutError(
            "Inference timed out",
            timeout_seconds=30,
        )
        assert "Inference timed out" in str(error)
        assert error.timeout_seconds == 30


class TestLabelValidationError:
    """Tests for LabelValidationError."""
    
    def test_create_basic(self):
        """Test creating basic label validation error."""
        error = LabelValidationError("Label validation failed")
        assert str(error) == "Label validation failed"


class TestLabelFetchError:
    """Tests for LabelFetchError."""
    
    def test_create_with_source(self):
        """Test creating exception with source."""
        error = LabelFetchError(
            "Failed to fetch label",
            source="ACLED",
        )
        assert "Failed to fetch label" in str(error)
        assert error.source == "ACLED"


class TestCacheError:
    """Tests for CacheError."""
    
    def test_create_with_operation(self):
        """Test creating exception with operation."""
        error = CacheError(
            "Cache operation failed",
            operation="get",
        )
        assert "Cache operation failed" in str(error)
        assert error.operation == "get"


class TestKafkaError:
    """Tests for KafkaError."""
    
    def test_create_with_topic(self):
        """Test creating exception with topic."""
        error = KafkaError(
            "Kafka error",
            topic="predictions",
        )
        assert "Kafka error" in str(error)
        assert error.topic == "predictions"


class TestPostgresError:
    """Tests for PostgresError."""
    
    def test_create_with_query(self):
        """Test creating exception with query."""
        error = PostgresError(
            "Database error",
            query="SELECT * FROM predictions",
        )
        assert "Database error" in str(error)
        assert error.query == "SELECT * FROM predictions"

