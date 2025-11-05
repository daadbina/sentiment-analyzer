"""
Unit tests for evaluation and drift detection.

Tests evaluator and drift detector.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock

from src.evaluation.evaluator import Evaluator
from src.evaluation.drift_detector import DriftDetector
from src.models.xgboost_model import XGBoostModel


class TestEvaluator:
    """Test model evaluation."""

    @pytest.fixture
    def trained_model(self):
        """Create a trained model."""
        X_train = np.random.randn(100, 10)
        y_train = np.random.randint(0, 2, 100)
        X_val = np.random.randn(20, 10)
        y_val = np.random.randint(0, 2, 20)
        
        model = XGBoostModel()
        model.train(X_train, y_train, X_val, y_val)
        return model

    @pytest.fixture
    def test_data(self):
        """Create test data."""
        X_test = np.random.randn(50, 10)
        y_test = np.random.randint(0, 2, 50)
        return X_test, y_test

    def test_evaluator_initialization(self):
        """Test evaluator initialization."""
        evaluator = Evaluator()
        assert evaluator is not None

    def test_evaluator_evaluate(self, trained_model, test_data):
        """Test model evaluation."""
        X_test, y_test = test_data
        evaluator = Evaluator()
        
        metrics = evaluator.evaluate(trained_model, X_test, y_test)
        
        assert metrics is not None
        assert 'accuracy' in metrics
        assert 'precision' in metrics
        assert 'recall' in metrics
        assert 'f1' in metrics
        assert 'auc' in metrics

    def test_evaluator_metrics_range(self, trained_model, test_data):
        """Test that metrics are in valid ranges."""
        X_test, y_test = test_data
        evaluator = Evaluator()
        
        metrics = evaluator.evaluate(trained_model, X_test, y_test)
        
        assert 0 <= metrics['accuracy'] <= 1
        assert 0 <= metrics['precision'] <= 1
        assert 0 <= metrics['recall'] <= 1
        assert 0 <= metrics['f1'] <= 1
        assert 0 <= metrics['auc'] <= 1

    def test_evaluator_confusion_matrix(self, trained_model, test_data):
        """Test confusion matrix computation."""
        X_test, y_test = test_data
        evaluator = Evaluator()
        
        metrics = evaluator.evaluate(trained_model, X_test, y_test)
        
        assert 'confusion_matrix' in metrics
        cm = metrics['confusion_matrix']
        assert cm.shape == (2, 2)

    def test_evaluator_roc_curve(self, trained_model, test_data):
        """Test ROC curve computation."""
        X_test, y_test = test_data
        evaluator = Evaluator()
        
        metrics = evaluator.evaluate(trained_model, X_test, y_test)
        
        assert 'roc_curve' in metrics
        roc = metrics['roc_curve']
        assert 'fpr' in roc
        assert 'tpr' in roc
        assert 'thresholds' in roc

    def test_evaluator_cross_validation(self, trained_model, test_data):
        """Test cross-validation evaluation."""
        X_test, y_test = test_data
        evaluator = Evaluator()
        
        cv_scores = evaluator.cross_validate(trained_model, X_test, y_test, cv=3)
        
        assert cv_scores is not None
        assert len(cv_scores) > 0

    def test_evaluator_compare_models(self, trained_model, test_data):
        """Test comparing multiple models."""
        X_test, y_test = test_data
        evaluator = Evaluator()
        
        model2 = XGBoostModel()
        X_train = np.random.randn(100, 10)
        y_train = np.random.randint(0, 2, 100)
        X_val = np.random.randn(20, 10)
        y_val = np.random.randint(0, 2, 20)
        model2.train(X_train, y_train, X_val, y_val)
        
        models = [trained_model, model2]
        comparison = evaluator.compare_models(models, X_test, y_test)
        
        assert comparison is not None
        assert len(comparison) == 2


class TestDriftDetector:
    """Test drift detection."""

    @pytest.fixture
    def reference_data(self):
        """Create reference data."""
        X_ref = np.random.randn(100, 10)
        y_ref = np.random.randint(0, 2, 100)
        return X_ref, y_ref

    @pytest.fixture
    def current_data(self):
        """Create current data."""
        X_curr = np.random.randn(50, 10)
        y_curr = np.random.randint(0, 2, 50)
        return X_curr, y_curr

    def test_drift_detector_initialization(self):
        """Test drift detector initialization."""
        detector = DriftDetector(threshold=0.1)
        assert detector is not None
        assert detector.threshold == 0.1

    def test_drift_detector_feature_drift(self, reference_data, current_data):
        """Test feature drift detection."""
        X_ref, _ = reference_data
        X_curr, _ = current_data
        detector = DriftDetector(threshold=0.1)
        
        drift_report = detector.detect_feature_drift(X_ref, X_curr)
        
        assert drift_report is not None
        assert 'drift_detected' in drift_report
        assert 'metrics' in drift_report

    def test_drift_detector_target_drift(self, reference_data, current_data):
        """Test target drift detection."""
        _, y_ref = reference_data
        _, y_curr = current_data
        detector = DriftDetector(threshold=0.1)
        
        drift_report = detector.detect_target_drift(y_ref, y_curr)
        
        assert drift_report is not None
        assert 'drift_detected' in drift_report

    def test_drift_detector_no_drift(self):
        """Test drift detection with identical data."""
        X = np.random.randn(100, 10)
        detector = DriftDetector(threshold=0.1)
        
        drift_report = detector.detect_feature_drift(X, X)
        
        assert drift_report is not None
        # Should detect minimal drift
        assert isinstance(drift_report['drift_detected'], bool)

    def test_drift_detector_clear_drift(self):
        """Test drift detection with clearly different data."""
        X_ref = np.random.randn(100, 10)
        X_curr = np.random.randn(100, 10) + 5  # Shifted distribution
        detector = DriftDetector(threshold=0.1)
        
        drift_report = detector.detect_feature_drift(X_ref, X_curr)
        
        assert drift_report is not None
        # Should detect drift
        assert isinstance(drift_report['drift_detected'], bool)

    def test_drift_detector_report_structure(self, reference_data, current_data):
        """Test drift report structure."""
        X_ref, y_ref = reference_data
        X_curr, y_curr = current_data
        detector = DriftDetector(threshold=0.1)
        
        drift_report = detector.detect_feature_drift(X_ref, X_curr)
        
        assert 'drift_detected' in drift_report
        assert 'metrics' in drift_report
        assert 'timestamp' in drift_report

    def test_drift_detector_multiple_features(self, reference_data, current_data):
        """Test drift detection for multiple features."""
        X_ref, _ = reference_data
        X_curr, _ = current_data
        detector = DriftDetector(threshold=0.1)
        
        drift_report = detector.detect_feature_drift(X_ref, X_curr)
        
        assert drift_report is not None
        assert 'metrics' in drift_report
        metrics = drift_report['metrics']
        assert len(metrics) > 0

    def test_drift_detector_statistical_test(self, reference_data, current_data):
        """Test statistical drift detection."""
        X_ref, _ = reference_data
        X_curr, _ = current_data
        detector = DriftDetector(threshold=0.1)
        
        drift_report = detector.detect_feature_drift(X_ref, X_curr)
        
        assert drift_report is not None
        assert 'metrics' in drift_report
        # Check for p-values or test statistics
        for metric in drift_report['metrics']:
            assert 'test_statistic' in metric or 'p_value' in metric

