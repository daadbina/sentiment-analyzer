"""
Unit tests for PredictionValidator.

Tests prediction comparison with labels, label consistency calculation, and accuracy tracking.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from src.validation.prediction_validator import PredictionValidator
from src.config import ValidationConfig


@pytest.fixture
def validation_config():
    """Create validation configuration for testing."""
    return ValidationConfig(
        label_consistency_threshold=0.85,
        drift_detection_window_hours=24,
        min_samples_for_drift=30
    )


@pytest.fixture
def postgres_client_mock():
    """Create PostgreSQL client mock."""
    client = Mock()
    client.execute_query = AsyncMock()
    return client


@pytest.fixture
def metrics_mock():
    """Create metrics collector mock."""
    metrics = Mock()
    metrics.set_label_consistency_score = Mock()
    return metrics


@pytest.fixture
def prediction_validator(validation_config, postgres_client_mock, metrics_mock):
    """Create PredictionValidator instance for testing."""
    return PredictionValidator(
        config=validation_config,
        postgres_client=postgres_client_mock,
        metrics=metrics_mock
    )


class TestPredictionValidator:
    """Test suite for PredictionValidator."""
    
    @pytest.mark.asyncio
    async def test_compare_prediction_with_label_match(self, prediction_validator):
        """Test comparison when prediction matches label."""
        prediction = 1
        label = 1
        label_confidence = 0.9
        
        score = await prediction_validator.compare_prediction_with_label(
            prediction=prediction,
            label=label,
            label_confidence=label_confidence
        )
        
        # Score should be weighted by label confidence
        assert score == 0.9
    
    @pytest.mark.asyncio
    async def test_compare_prediction_with_label_mismatch(self, prediction_validator):
        """Test comparison when prediction doesn't match label."""
        prediction = 1
        label = 0
        label_confidence = 0.8
        
        score = await prediction_validator.compare_prediction_with_label(
            prediction=prediction,
            label=label,
            label_confidence=label_confidence
        )
        
        # Score should be 0 for mismatch
        assert score == 0.0
    
    @pytest.mark.asyncio
    async def test_compare_prediction_with_label_low_confidence(self, prediction_validator):
        """Test comparison with low confidence label."""
        prediction = 1
        label = 1
        label_confidence = 0.3
        
        score = await prediction_validator.compare_prediction_with_label(
            prediction=prediction,
            label=label,
            label_confidence=label_confidence
        )
        
        # Score should be weighted by low confidence
        assert score == 0.3
    
    @pytest.mark.asyncio
    async def test_compare_prediction_with_label_zero_confidence(self, prediction_validator):
        """Test comparison with zero confidence label."""
        prediction = 1
        label = 1
        label_confidence = 0.0
        
        score = await prediction_validator.compare_prediction_with_label(
            prediction=prediction,
            label=label,
            label_confidence=label_confidence
        )
        
        # Score should be 0 for zero confidence
        assert score == 0.0
    
    @pytest.mark.asyncio
    async def test_calculate_label_consistency_above_threshold(
        self, prediction_validator, postgres_client_mock, metrics_mock
    ):
        """Test label consistency calculation above threshold."""
        # Mock database query to return high consistency
        postgres_client_mock.execute_query.return_value = [
            {"total_predictions": 100, "correct_predictions": 90}
        ]
        
        consistency = await prediction_validator.calculate_label_consistency(
            time_window_hours=48
        )
        
        assert consistency == 0.9
        assert consistency >= 0.85  # Above threshold
        metrics_mock.set_label_consistency_score.assert_called_once_with(0.9)
    
    @pytest.mark.asyncio
    async def test_calculate_label_consistency_below_threshold(
        self, prediction_validator, postgres_client_mock, metrics_mock
    ):
        """Test label consistency calculation below threshold."""
        # Mock database query to return low consistency
        postgres_client_mock.execute_query.return_value = [
            {"total_predictions": 100, "correct_predictions": 70}
        ]
        
        consistency = await prediction_validator.calculate_label_consistency(
            time_window_hours=48
        )
        
        assert consistency == 0.7
        assert consistency < 0.85  # Below threshold
        metrics_mock.set_label_consistency_score.assert_called_once_with(0.7)
    
    @pytest.mark.asyncio
    async def test_calculate_label_consistency_no_predictions(
        self, prediction_validator, postgres_client_mock, metrics_mock
    ):
        """Test label consistency calculation with no predictions."""
        # Mock database query to return no predictions
        postgres_client_mock.execute_query.return_value = [
            {"total_predictions": 0, "correct_predictions": 0}
        ]
        
        consistency = await prediction_validator.calculate_label_consistency(
            time_window_hours=48
        )
        
        # Should return 0.0 when no predictions
        assert consistency == 0.0
        metrics_mock.set_label_consistency_score.assert_called_once_with(0.0)
    
    @pytest.mark.asyncio
    async def test_calculate_label_consistency_custom_window(
        self, prediction_validator, postgres_client_mock, metrics_mock
    ):
        """Test label consistency calculation with custom time window."""
        postgres_client_mock.execute_query.return_value = [
            {"total_predictions": 50, "correct_predictions": 45}
        ]
        
        consistency = await prediction_validator.calculate_label_consistency(
            time_window_hours=24
        )
        
        assert consistency == 0.9
        
        # Verify query was called with correct time window
        call_args = postgres_client_mock.execute_query.call_args
        assert "24" in str(call_args) or "INTERVAL '24 hours'" in str(call_args)
    
    @pytest.mark.asyncio
    async def test_get_accuracy_over_time_with_data(
        self, prediction_validator, postgres_client_mock
    ):
        """Test getting accuracy over time with data."""
        # Mock database query to return time-series data
        postgres_client_mock.execute_query.return_value = [
            {
                "time_bucket": datetime(2024, 1, 1, 0, 0),
                "total": 100,
                "correct": 85,
                "accuracy": 0.85
            },
            {
                "time_bucket": datetime(2024, 1, 1, 1, 0),
                "total": 120,
                "correct": 100,
                "accuracy": 0.833
            }
        ]
        
        accuracy_data = await prediction_validator.get_accuracy_over_time(
            time_window_hours=48,
            bucket_size_hours=1
        )
        
        assert len(accuracy_data) == 2
        assert accuracy_data[0]["accuracy"] == 0.85
        assert accuracy_data[1]["accuracy"] == 0.833
    
    @pytest.mark.asyncio
    async def test_get_accuracy_over_time_no_data(
        self, prediction_validator, postgres_client_mock
    ):
        """Test getting accuracy over time with no data."""
        postgres_client_mock.execute_query.return_value = []
        
        accuracy_data = await prediction_validator.get_accuracy_over_time(
            time_window_hours=48,
            bucket_size_hours=1
        )
        
        assert accuracy_data == []
    
    @pytest.mark.asyncio
    async def test_get_accuracy_over_time_custom_bucket(
        self, prediction_validator, postgres_client_mock
    ):
        """Test getting accuracy over time with custom bucket size."""
        postgres_client_mock.execute_query.return_value = [
            {
                "time_bucket": datetime(2024, 1, 1, 0, 0),
                "total": 500,
                "correct": 425,
                "accuracy": 0.85
            }
        ]
        
        accuracy_data = await prediction_validator.get_accuracy_over_time(
            time_window_hours=24,
            bucket_size_hours=6
        )
        
        assert len(accuracy_data) == 1
        
        # Verify query was called with correct bucket size
        call_args = postgres_client_mock.execute_query.call_args
        assert "6" in str(call_args) or "INTERVAL '6 hours'" in str(call_args)
    
    @pytest.mark.asyncio
    async def test_compare_prediction_with_label_probabilistic(self, prediction_validator):
        """Test comparison with probabilistic predictions."""
        # Prediction close to 1
        score1 = await prediction_validator.compare_prediction_with_label(
            prediction=0.9,
            label=1,
            label_confidence=1.0
        )
        
        # Prediction close to 0
        score2 = await prediction_validator.compare_prediction_with_label(
            prediction=0.1,
            label=0,
            label_confidence=1.0
        )
        
        # Both should be considered correct
        assert score1 > 0.5
        assert score2 > 0.5
    
    @pytest.mark.asyncio
    async def test_compare_prediction_with_label_boundary(self, prediction_validator):
        """Test comparison at decision boundary."""
        # Prediction at 0.5 (uncertain)
        score = await prediction_validator.compare_prediction_with_label(
            prediction=0.5,
            label=1,
            label_confidence=1.0
        )
        
        # Score should reflect uncertainty
        assert 0.0 <= score <= 1.0
    
    @pytest.mark.asyncio
    async def test_calculate_label_consistency_database_error(
        self, prediction_validator, postgres_client_mock, metrics_mock
    ):
        """Test label consistency calculation when database query fails."""
        postgres_client_mock.execute_query.side_effect = Exception("Database error")
        
        with pytest.raises(Exception):
            await prediction_validator.calculate_label_consistency(
                time_window_hours=48
            )
    
    @pytest.mark.asyncio
    async def test_get_accuracy_over_time_database_error(
        self, prediction_validator, postgres_client_mock
    ):
        """Test accuracy over time when database query fails."""
        postgres_client_mock.execute_query.side_effect = Exception("Database error")
        
        with pytest.raises(Exception):
            await prediction_validator.get_accuracy_over_time(
                time_window_hours=48,
                bucket_size_hours=1
            )
    
    @pytest.mark.asyncio
    async def test_weighted_scoring_multiple_labels(self, prediction_validator):
        """Test weighted scoring with multiple labels of varying confidence."""
        # High confidence match
        score1 = await prediction_validator.compare_prediction_with_label(
            prediction=1,
            label=1,
            label_confidence=0.95
        )
        
        # Medium confidence match
        score2 = await prediction_validator.compare_prediction_with_label(
            prediction=1,
            label=1,
            label_confidence=0.6
        )
        
        # Low confidence match
        score3 = await prediction_validator.compare_prediction_with_label(
            prediction=1,
            label=1,
            label_confidence=0.3
        )
        
        # Scores should be proportional to confidence
        assert score1 > score2 > score3
        assert score1 == 0.95
        assert score2 == 0.6
        assert score3 == 0.3

