"""
Integration tests for end-to-end training pipeline.

Tests complete training workflow with real components.
"""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio

from src.service import TrainerService
from src.data.feature_retriever import FeatureRetriever
from src.data.label_retriever import LabelRetriever
from src.data.preprocessor import DataPreprocessor
from src.training.splitter import DataSplitter
from src.training.trainer import Trainer
from src.evaluation.evaluator import Evaluator
from src.evaluation.drift_detector import DriftDetector
from src.registry.model_promoter import ModelPromoter


class TestEndToEndTraining:
    """Test complete training pipeline."""

    @pytest.fixture
    def sample_features(self):
        """Create sample features."""
        return pd.DataFrame(
            np.random.randn(1000, 24),
            columns=[f'feature_{i}' for i in range(24)]
        )

    @pytest.fixture
    def sample_labels(self):
        """Create sample labels."""
        return np.random.randint(0, 2, 1000)

    @pytest.fixture
    def timestamps(self):
        """Create timestamps."""
        return pd.date_range('2024-01-01', periods=1000, freq='D')

    def test_feature_retrieval_to_preprocessing(self, sample_features, sample_labels):
        """Test feature retrieval and preprocessing."""
        with patch('src.data.feature_retriever.FeastClient') as mock_feast:
            mock_client = MagicMock()
            mock_client.get_features.return_value = sample_features
            mock_feast.return_value = mock_client
            
            retriever = FeatureRetriever()
            features = retriever.retrieve_features(
                entity_ids=list(range(1000)),
                start_date='2024-01-01',
                end_date='2024-12-31'
            )
            
            preprocessor = DataPreprocessor()
            X_processed = preprocessor.fit_transform(features.values)
            
            assert X_processed is not None
            assert X_processed.shape[0] == len(features)

    def test_data_splitting_to_training(self, sample_features, sample_labels, timestamps):
        """Test data splitting and model training."""
        X = sample_features.values
        y = sample_labels
        
        splitter = DataSplitter(test_size=0.2, validation_size=0.1)
        (X_train, y_train), (X_val, y_val), (X_test, y_test) = (
            splitter.split_temporal(X, y, timestamps.values)
        )
        
        trainer = Trainer()
        models = trainer.train_all_models(X_train, y_train, X_val, y_val)
        
        assert models is not None
        assert len(models) >= 2

    def test_training_to_evaluation(self, sample_features, sample_labels, timestamps):
        """Test training and evaluation."""
        X = sample_features.values
        y = sample_labels
        
        splitter = DataSplitter(test_size=0.2, validation_size=0.1)
        (X_train, y_train), (X_val, y_val), (X_test, y_test) = (
            splitter.split_temporal(X, y, timestamps.values)
        )
        
        trainer = Trainer()
        models = trainer.train_all_models(X_train, y_train, X_val, y_val)
        
        evaluator = Evaluator()
        for model in models:
            metrics = evaluator.evaluate(model, X_test, y_test)
            
            assert metrics is not None
            assert 'auc' in metrics
            assert 0 <= metrics['auc'] <= 1

    def test_evaluation_to_drift_detection(self, sample_features, sample_labels, timestamps):
        """Test evaluation and drift detection."""
        X = sample_features.values
        y = sample_labels
        
        splitter = DataSplitter(test_size=0.2, validation_size=0.1)
        (X_train, y_train), (X_val, y_val), (X_test, y_test) = (
            splitter.split_temporal(X, y, timestamps.values)
        )
        
        trainer = Trainer()
        models = trainer.train_all_models(X_train, y_train, X_val, y_val)
        
        evaluator = Evaluator()
        metrics = evaluator.evaluate(models[0], X_test, y_test)
        
        drift_detector = DriftDetector(threshold=0.1)
        feature_drift = drift_detector.detect_feature_drift(X_train, X_test)
        target_drift = drift_detector.detect_target_drift(y_train, y_test)
        
        assert feature_drift is not None
        assert target_drift is not None

    def test_drift_detection_to_promotion(self, sample_features, sample_labels, timestamps):
        """Test drift detection and model promotion."""
        X = sample_features.values
        y = sample_labels
        
        splitter = DataSplitter(test_size=0.2, validation_size=0.1)
        (X_train, y_train), (X_val, y_val), (X_test, y_test) = (
            splitter.split_temporal(X, y, timestamps.values)
        )
        
        trainer = Trainer()
        models = trainer.train_all_models(X_train, y_train, X_val, y_val)
        
        evaluator = Evaluator()
        metrics = evaluator.evaluate(models[0], X_test, y_test)
        
        drift_detector = DriftDetector(threshold=0.1)
        feature_drift = drift_detector.detect_feature_drift(X_train, X_test)
        
        with patch('src.registry.model_promoter.MLflowClient') as mock_mlflow:
            mock_client = MagicMock()
            mock_mlflow.return_value = mock_client
            
            promoter = ModelPromoter()
            
            # Only promote if no drift and metrics are good
            if not feature_drift['drift_detected'] and metrics['auc'] >= 0.75:
                result = promoter.promote_model(
                    'test_model',
                    'v1',
                    metrics,
                    stage='Staging'
                )
                assert result is not None

    def test_complete_pipeline_flow(self, sample_features, sample_labels, timestamps):
        """Test complete pipeline from features to promotion."""
        X = sample_features.values
        y = sample_labels
        
        # Step 1: Preprocess
        preprocessor = DataPreprocessor()
        X_processed = preprocessor.fit_transform(X)
        
        # Step 2: Split
        splitter = DataSplitter(test_size=0.2, validation_size=0.1)
        (X_train, y_train), (X_val, y_val), (X_test, y_test) = (
            splitter.split_temporal(X_processed, y, timestamps.values)
        )
        
        # Step 3: Train
        trainer = Trainer()
        models = trainer.train_all_models(X_train, y_train, X_val, y_val)
        
        # Step 4: Evaluate
        evaluator = Evaluator()
        metrics = evaluator.evaluate(models[0], X_test, y_test)
        
        # Step 5: Detect drift
        drift_detector = DriftDetector(threshold=0.1)
        feature_drift = drift_detector.detect_feature_drift(X_train, X_test)
        target_drift = drift_detector.detect_target_drift(y_train, y_test)
        
        # Step 6: Promote if conditions met
        with patch('src.registry.model_promoter.MLflowClient') as mock_mlflow:
            mock_client = MagicMock()
            mock_mlflow.return_value = mock_client
            
            promoter = ModelPromoter()
            
            if (not feature_drift['drift_detected'] and 
                not target_drift['drift_detected'] and 
                metrics['auc'] >= 0.75):
                result = promoter.promote_model(
                    'test_model',
                    'v1',
                    metrics,
                    stage='Production'
                )
                assert result is not None

    def test_pipeline_with_hyperparameter_tuning(self, sample_features, sample_labels, timestamps):
        """Test pipeline with hyperparameter tuning."""
        from src.training.hyperparameter_tuner import HyperparameterTuner
        
        X = sample_features.values
        y = sample_labels
        
        splitter = DataSplitter(test_size=0.2, validation_size=0.1)
        (X_train, y_train), (X_val, y_val), (X_test, y_test) = (
            splitter.split_temporal(X, y, timestamps.values)
        )
        
        # Tune hyperparameters
        tuner = HyperparameterTuner(n_trials=5)
        best_params = tuner.tune_xgboost(X_train, y_train, X_val, y_val)
        
        assert best_params is not None
        assert 'max_depth' in best_params

    def test_pipeline_error_handling(self, sample_features, sample_labels):
        """Test pipeline error handling."""
        X = sample_features.values
        y = sample_labels
        
        # Test with invalid data
        with pytest.raises(Exception):
            splitter = DataSplitter(test_size=0.2, validation_size=0.1)
            splitter.split_temporal(X, y[:-1], None)  # Mismatched lengths

    def test_pipeline_data_integrity(self, sample_features, sample_labels, timestamps):
        """Test data integrity throughout pipeline."""
        X = sample_features.values
        y = sample_labels
        
        original_shape = X.shape
        
        preprocessor = DataPreprocessor()
        X_processed = preprocessor.fit_transform(X)
        
        # Shape should be preserved
        assert X_processed.shape[0] == original_shape[0]
        
        splitter = DataSplitter(test_size=0.2, validation_size=0.1)
        (X_train, y_train), (X_val, y_val), (X_test, y_test) = (
            splitter.split_temporal(X_processed, y, timestamps.values)
        )
        
        # Total samples should match
        total_samples = len(X_train) + len(X_val) + len(X_test)
        assert total_samples == len(X)

    def test_pipeline_reproducibility(self, sample_features, sample_labels, timestamps):
        """Test pipeline reproducibility with fixed seed."""
        X = sample_features.values
        y = sample_labels
        
        # Run 1
        splitter1 = DataSplitter(test_size=0.2, validation_size=0.1, random_seed=42)
        (X_train1, y_train1), _, _ = splitter1.split_temporal(X, y, timestamps.values)
        
        # Run 2
        splitter2 = DataSplitter(test_size=0.2, validation_size=0.1, random_seed=42)
        (X_train2, y_train2), _, _ = splitter2.split_temporal(X, y, timestamps.values)
        
        # Results should be identical
        assert np.array_equal(X_train1, X_train2)
        assert np.array_equal(y_train1, y_train2)

