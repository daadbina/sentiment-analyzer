"""
Unit tests for training pipeline.

Tests trainer and hyperparameter tuner.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock

from src.training.trainer import Trainer
from src.training.hyperparameter_tuner import HyperparameterTuner
from src.training.splitter import DataSplitter


class TestDataSplitter:
    """Test data splitting functionality."""

    @pytest.fixture
    def sample_data(self):
        """Create sample data."""
        X = np.random.randn(1000, 10)
        y = np.random.randint(0, 2, 1000)
        timestamps = np.arange(1000)
        return X, y, timestamps

    def test_splitter_initialization(self):
        """Test splitter initialization."""
        splitter = DataSplitter(test_size=0.2, validation_size=0.1, random_seed=42)
        assert splitter is not None
        assert splitter.test_size == 0.2
        assert splitter.validation_size == 0.1

    def test_splitter_temporal_split(self, sample_data):
        """Test temporal splitting."""
        X, y, timestamps = sample_data
        splitter = DataSplitter(test_size=0.2, validation_size=0.1)

        (X_train, y_train), (X_val, y_val), (X_test, y_test) = splitter.split_temporal(
            X, y, timestamps
        )

        assert len(X_train) + len(X_val) + len(X_test) == len(X)
        assert len(X_train) > len(X_val)
        assert len(X_train) > len(X_test)

    def test_splitter_stratified_split(self, sample_data):
        """Test stratified splitting."""
        X, y, _ = sample_data
        splitter = DataSplitter(test_size=0.2, validation_size=0.1)

        (X_train, y_train), (X_val, y_val), (X_test, y_test) = (
            splitter.split_stratified(X, y)
        )

        assert len(X_train) + len(X_val) + len(X_test) == len(X)
        # Check stratification
        train_ratio = y_train.sum() / len(y_train)
        overall_ratio = y.sum() / len(y)
        assert abs(train_ratio - overall_ratio) < 0.1

    def test_splitter_no_data_leakage(self, sample_data):
        """Test that splitting prevents data leakage."""
        X, y, timestamps = sample_data
        splitter = DataSplitter(test_size=0.2, validation_size=0.1)

        (X_train, y_train), (X_val, y_val), (X_test, y_test) = splitter.split_temporal(
            X, y, timestamps
        )

        # Ensure no overlap
        train_indices = set(range(len(X_train)))
        val_indices = set(range(len(X_train), len(X_train) + len(X_val)))
        test_indices = set(range(len(X_train) + len(X_val), len(X)))

        assert len(train_indices & val_indices) == 0
        assert len(train_indices & test_indices) == 0
        assert len(val_indices & test_indices) == 0


class TestTrainer:
    """Test training orchestration."""

    @pytest.fixture
    def sample_data(self):
        """Create sample training data."""
        X_train = np.random.randn(100, 10)
        y_train = np.random.randint(0, 2, 100)
        X_val = np.random.randn(20, 10)
        y_val = np.random.randint(0, 2, 20)
        return X_train, y_train, X_val, y_val

    def test_trainer_initialization(self):
        """Test trainer initialization."""
        trainer = Trainer()
        assert trainer is not None
        assert trainer.models is not None

    def test_trainer_train_xgboost(self, sample_data):
        """Test training XGBoost model."""
        X_train, y_train, X_val, y_val = sample_data
        trainer = Trainer()

        model = trainer.train_xgboost(X_train, y_train, X_val, y_val)

        assert model is not None
        assert model.is_trained is True

    def test_trainer_train_logistic_regression(self, sample_data):
        """Test training Logistic Regression model."""
        X_train, y_train, X_val, y_val = sample_data
        trainer = Trainer()

        model = trainer.train_logistic_regression(X_train, y_train, X_val, y_val)

        assert model is not None
        assert model.is_trained is True

    @patch("src.training.trainer.LLMBaselineModel")
    def test_trainer_train_llm_baseline(self, mock_llm, sample_data):
        """Test training LLM baseline model."""
        X_train, y_train, X_val, y_val = sample_data
        trainer = Trainer()

        mock_model = MagicMock()
        mock_model.is_trained = True
        mock_llm.return_value = mock_model

        model = trainer.train_llm_baseline(X_train, y_train, X_val, y_val)

        assert model is not None

    def test_trainer_train_all_models(self, sample_data):
        """Test training all models."""
        X_train, y_train, X_val, y_val = sample_data
        trainer = Trainer()

        models = trainer.train_all_models(X_train, y_train, X_val, y_val)

        assert models is not None
        assert len(models) >= 2  # At least XGBoost and LogReg

    def test_trainer_get_best_model(self, sample_data):
        """Test getting best model."""
        X_train, y_train, X_val, y_val = sample_data
        trainer = Trainer()

        models = trainer.train_all_models(X_train, y_train, X_val, y_val)
        best_model = trainer.get_best_model()

        assert best_model is not None


class TestHyperparameterTuner:
    """Test hyperparameter tuning."""

    @pytest.fixture
    def sample_data(self):
        """Create sample training data."""
        X_train = np.random.randn(100, 10)
        y_train = np.random.randint(0, 2, 100)
        X_val = np.random.randn(20, 10)
        y_val = np.random.randint(0, 2, 20)
        return X_train, y_train, X_val, y_val

    def test_tuner_initialization(self):
        """Test tuner initialization."""
        tuner = HyperparameterTuner(n_trials=10)
        assert tuner is not None
        assert tuner.n_trials == 10

    def test_tuner_tune_xgboost(self, sample_data):
        """Test tuning XGBoost hyperparameters."""
        X_train, y_train, X_val, y_val = sample_data
        tuner = HyperparameterTuner(n_trials=5)

        best_params = tuner.tune_xgboost(X_train, y_train, X_val, y_val)

        assert best_params is not None
        assert isinstance(best_params, dict)
        assert "max_depth" in best_params
        assert "learning_rate" in best_params

    def test_tuner_tune_logistic_regression(self, sample_data):
        """Test tuning Logistic Regression hyperparameters."""
        X_train, y_train, X_val, y_val = sample_data
        tuner = HyperparameterTuner(n_trials=5)

        best_params = tuner.tune_logistic_regression(X_train, y_train, X_val, y_val)

        assert best_params is not None
        assert isinstance(best_params, dict)
        assert "C" in best_params

    def test_tuner_best_trial(self, sample_data):
        """Test getting best trial."""
        X_train, y_train, X_val, y_val = sample_data
        tuner = HyperparameterTuner(n_trials=5)

        best_params = tuner.tune_xgboost(X_train, y_train, X_val, y_val)
        best_trial = tuner.get_best_trial()

        assert best_trial is not None

    def test_tuner_study_history(self, sample_data):
        """Test getting study history."""
        X_train, y_train, X_val, y_val = sample_data
        tuner = HyperparameterTuner(n_trials=5)

        best_params = tuner.tune_xgboost(X_train, y_train, X_val, y_val)
        history = tuner.get_study_history()

        assert history is not None
        assert len(history) > 0
