"""
Unit tests for ConfidenceScorer.

Tests confidence computation, uncertainty quantification, and model-specific logic.
"""

import pytest
import numpy as np
from unittest.mock import Mock, MagicMock

from src.inference.confidence_scorer import ConfidenceScorer


@pytest.fixture
def metrics_mock():
    """Create metrics collector mock."""
    metrics = Mock()
    metrics.record_prediction_confidence = Mock()
    return metrics


@pytest.fixture
def confidence_scorer(metrics_mock):
    """Create ConfidenceScorer instance for testing."""
    return ConfidenceScorer(metrics=metrics_mock)


@pytest.fixture
def xgboost_model():
    """Create mock XGBoost model."""
    model = Mock()
    model.__class__.__name__ = "XGBClassifier"
    model.predict_proba = Mock(return_value=np.array([[0.2, 0.8]]))
    return model


@pytest.fixture
def sklearn_model():
    """Create mock sklearn model."""
    model = Mock()
    model.__class__.__name__ = "RandomForestClassifier"
    model.predict_proba = Mock(return_value=np.array([[0.3, 0.7]]))
    return model


@pytest.fixture
def baseline_model():
    """Create mock baseline model."""
    model = Mock()
    model.__class__.__name__ = "BaselineModel"
    model.predict = Mock(return_value=np.array([0.6]))
    return model


class TestConfidenceScorer:
    """Test suite for ConfidenceScorer."""
    
    def test_compute_confidence_xgboost(self, confidence_scorer, xgboost_model, metrics_mock):
        """Test confidence computation for XGBoost model."""
        prediction = 1
        features = {"feature1": 0.5, "feature2": 0.3}
        
        confidence = confidence_scorer.compute_confidence(
            model=xgboost_model,
            prediction=prediction,
            features=features
        )
        
        assert confidence == 0.8
        xgboost_model.predict_proba.assert_called_once()
        metrics_mock.record_prediction_confidence.assert_called_once_with(0.8)
    
    def test_compute_confidence_sklearn(self, confidence_scorer, sklearn_model, metrics_mock):
        """Test confidence computation for sklearn model."""
        prediction = 1
        features = {"feature1": 0.5, "feature2": 0.3}
        
        confidence = confidence_scorer.compute_confidence(
            model=sklearn_model,
            prediction=prediction,
            features=features
        )
        
        assert confidence == 0.7
        sklearn_model.predict_proba.assert_called_once()
        metrics_mock.record_prediction_confidence.assert_called_once_with(0.7)
    
    def test_compute_confidence_baseline(self, confidence_scorer, baseline_model, metrics_mock):
        """Test confidence computation for baseline model."""
        prediction = 0.6
        features = {"feature1": 0.5, "feature2": 0.3}
        
        confidence = confidence_scorer.compute_confidence(
            model=baseline_model,
            prediction=prediction,
            features=features
        )
        
        # For baseline, confidence is based on distance from 0.5
        expected_confidence = abs(0.6 - 0.5) * 2  # 0.2
        assert confidence == expected_confidence
        metrics_mock.record_prediction_confidence.assert_called_once()
    
    def test_compute_confidence_unknown_model(self, confidence_scorer, metrics_mock):
        """Test confidence computation for unknown model type."""
        unknown_model = Mock()
        unknown_model.__class__.__name__ = "UnknownModel"
        
        prediction = 1
        features = {"feature1": 0.5}
        
        confidence = confidence_scorer.compute_confidence(
            model=unknown_model,
            prediction=prediction,
            features=features
        )
        
        # Should return default confidence
        assert confidence == 0.5
        metrics_mock.record_prediction_confidence.assert_called_once_with(0.5)
    
    def test_compute_confidence_with_uncertainty(self, confidence_scorer, xgboost_model, metrics_mock):
        """Test confidence computation with uncertainty adjustment."""
        prediction = 1
        features = {"feature1": 0.5, "feature2": 0.3}
        
        confidence = confidence_scorer.compute_confidence(
            model=xgboost_model,
            prediction=prediction,
            features=features,
            adjust_for_uncertainty=True
        )
        
        # Confidence should be adjusted downward due to uncertainty
        assert confidence < 0.8
        assert confidence > 0.0
        metrics_mock.record_prediction_confidence.assert_called_once()
    
    def test_quantify_uncertainty_with_features(self, confidence_scorer):
        """Test uncertainty quantification with feature data."""
        features = {
            "feature1": 0.5,
            "feature2": 0.3,
            "feature3": 0.8
        }
        
        epistemic, aleatoric = confidence_scorer.quantify_uncertainty(features)
        
        assert 0.0 <= epistemic <= 1.0
        assert 0.0 <= aleatoric <= 1.0
    
    def test_quantify_uncertainty_empty_features(self, confidence_scorer):
        """Test uncertainty quantification with empty features."""
        features = {}
        
        epistemic, aleatoric = confidence_scorer.quantify_uncertainty(features)
        
        # Should return high uncertainty for empty features
        assert epistemic > 0.5
        assert aleatoric > 0.5
    
    def test_quantify_uncertainty_missing_features(self, confidence_scorer):
        """Test uncertainty quantification with missing features."""
        features = {
            "feature1": None,
            "feature2": 0.5,
            "feature3": None
        }
        
        epistemic, aleatoric = confidence_scorer.quantify_uncertainty(features)
        
        # Should have higher uncertainty due to missing features
        assert epistemic > 0.3
        assert aleatoric > 0.3
    
    def test_adjust_confidence_by_uncertainty_high_uncertainty(self, confidence_scorer):
        """Test confidence adjustment with high uncertainty."""
        base_confidence = 0.9
        epistemic_uncertainty = 0.8
        aleatoric_uncertainty = 0.7
        
        adjusted = confidence_scorer.adjust_confidence_by_uncertainty(
            base_confidence,
            epistemic_uncertainty,
            aleatoric_uncertainty
        )
        
        # Confidence should be significantly reduced
        assert adjusted < base_confidence
        assert adjusted > 0.0
    
    def test_adjust_confidence_by_uncertainty_low_uncertainty(self, confidence_scorer):
        """Test confidence adjustment with low uncertainty."""
        base_confidence = 0.9
        epistemic_uncertainty = 0.1
        aleatoric_uncertainty = 0.1
        
        adjusted = confidence_scorer.adjust_confidence_by_uncertainty(
            base_confidence,
            epistemic_uncertainty,
            aleatoric_uncertainty
        )
        
        # Confidence should be slightly reduced
        assert adjusted < base_confidence
        assert adjusted > 0.7
    
    def test_adjust_confidence_by_uncertainty_zero_uncertainty(self, confidence_scorer):
        """Test confidence adjustment with zero uncertainty."""
        base_confidence = 0.9
        epistemic_uncertainty = 0.0
        aleatoric_uncertainty = 0.0
        
        adjusted = confidence_scorer.adjust_confidence_by_uncertainty(
            base_confidence,
            epistemic_uncertainty,
            aleatoric_uncertainty
        )
        
        # Confidence should remain high
        assert adjusted == base_confidence
    
    def test_compute_confidence_edge_case_zero_probability(self, confidence_scorer, xgboost_model, metrics_mock):
        """Test confidence computation with zero probability."""
        xgboost_model.predict_proba = Mock(return_value=np.array([[1.0, 0.0]]))
        
        prediction = 1
        features = {"feature1": 0.5}
        
        confidence = confidence_scorer.compute_confidence(
            model=xgboost_model,
            prediction=prediction,
            features=features
        )
        
        assert confidence == 0.0
        metrics_mock.record_prediction_confidence.assert_called_once_with(0.0)
    
    def test_compute_confidence_edge_case_one_probability(self, confidence_scorer, xgboost_model, metrics_mock):
        """Test confidence computation with probability of 1.0."""
        xgboost_model.predict_proba = Mock(return_value=np.array([[0.0, 1.0]]))
        
        prediction = 1
        features = {"feature1": 0.5}
        
        confidence = confidence_scorer.compute_confidence(
            model=xgboost_model,
            prediction=prediction,
            features=features
        )
        
        assert confidence == 1.0
        metrics_mock.record_prediction_confidence.assert_called_once_with(1.0)
    
    def test_compute_confidence_with_exception(self, confidence_scorer, xgboost_model, metrics_mock):
        """Test confidence computation when model raises exception."""
        xgboost_model.predict_proba = Mock(side_effect=Exception("Model error"))
        
        prediction = 1
        features = {"feature1": 0.5}
        
        confidence = confidence_scorer.compute_confidence(
            model=xgboost_model,
            prediction=prediction,
            features=features
        )
        
        # Should return default confidence on error
        assert confidence == 0.5
        metrics_mock.record_prediction_confidence.assert_called_once_with(0.5)
    
    def test_compute_confidence_multiclass(self, confidence_scorer, xgboost_model, metrics_mock):
        """Test confidence computation for multiclass prediction."""
        xgboost_model.predict_proba = Mock(return_value=np.array([[0.1, 0.6, 0.3]]))
        
        prediction = 1
        features = {"feature1": 0.5}
        
        confidence = confidence_scorer.compute_confidence(
            model=xgboost_model,
            prediction=prediction,
            features=features
        )
        
        assert confidence == 0.6
        metrics_mock.record_prediction_confidence.assert_called_once_with(0.6)
    
    def test_compute_confidence_baseline_edge_cases(self, confidence_scorer, baseline_model, metrics_mock):
        """Test baseline confidence computation edge cases."""
        # Test prediction at 0.5 (maximum uncertainty)
        confidence = confidence_scorer.compute_confidence(
            model=baseline_model,
            prediction=0.5,
            features={}
        )
        assert confidence == 0.0
        
        # Test prediction at 0.0 (maximum confidence for negative)
        confidence = confidence_scorer.compute_confidence(
            model=baseline_model,
            prediction=0.0,
            features={}
        )
        assert confidence == 1.0
        
        # Test prediction at 1.0 (maximum confidence for positive)
        confidence = confidence_scorer.compute_confidence(
            model=baseline_model,
            prediction=1.0,
            features={}
        )
        assert confidence == 1.0

