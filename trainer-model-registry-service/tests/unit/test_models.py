"""
Unit tests for model implementations.

Tests XGBoost, Logistic Regression, and LLM baseline models.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock

from src.models.base_model import BaseModel
from src.models.xgboost_model import XGBoostModel
from src.models.logistic_regression_model import LogisticRegressionModel
from src.models.llm_baseline_model import LLMBaselineModel


class TestBaseModel:
    """Test base model abstract class."""

    def test_base_model_is_abstract(self):
        """Test that BaseModel cannot be instantiated."""
        with pytest.raises(TypeError):
            BaseModel()

    def test_base_model_requires_train(self):
        """Test that BaseModel requires train method."""

        class IncompleteModel(BaseModel):
            def predict(self, X):
                pass

            def predict_proba(self, X):
                pass

            def get_feature_importance(self):
                pass

            def serialize(self):
                pass

        with pytest.raises(TypeError):
            IncompleteModel()


class TestXGBoostModel:
    """Test XGBoost model implementation."""

    @pytest.fixture
    def sample_data(self):
        """Create sample training data."""
        X_train = np.random.randn(100, 10)
        y_train = np.random.randint(0, 2, 100)
        X_val = np.random.randn(20, 10)
        y_val = np.random.randint(0, 2, 20)
        return X_train, y_train, X_val, y_val

    def test_xgboost_model_initialization(self):
        """Test XGBoost model initialization."""
        model = XGBoostModel()
        assert model is not None
        assert model.model is not None
        assert model.is_trained is False

    def test_xgboost_model_train(self, sample_data):
        """Test XGBoost model training."""
        X_train, y_train, X_val, y_val = sample_data
        model = XGBoostModel()

        model.train(X_train, y_train, X_val, y_val)

        assert model.is_trained is True

    def test_xgboost_model_predict(self, sample_data):
        """Test XGBoost model prediction."""
        X_train, y_train, X_val, y_val = sample_data
        model = XGBoostModel()
        model.train(X_train, y_train, X_val, y_val)

        predictions = model.predict(X_val)

        assert predictions is not None
        assert len(predictions) == len(X_val)
        assert all(p in [0, 1] for p in predictions)

    def test_xgboost_model_predict_proba(self, sample_data):
        """Test XGBoost model probability prediction."""
        X_train, y_train, X_val, y_val = sample_data
        model = XGBoostModel()
        model.train(X_train, y_train, X_val, y_val)

        probas = model.predict_proba(X_val)

        assert probas is not None
        assert probas.shape == (len(X_val), 2)
        assert np.all((probas >= 0) & (probas <= 1))
        assert np.allclose(probas.sum(axis=1), 1.0)

    def test_xgboost_model_feature_importance(self, sample_data):
        """Test XGBoost feature importance extraction."""
        X_train, y_train, X_val, y_val = sample_data
        model = XGBoostModel()
        model.train(X_train, y_train, X_val, y_val)

        importance = model.get_feature_importance()

        assert importance is not None
        assert len(importance) == X_train.shape[1]
        assert all(imp >= 0 for imp in importance)

    def test_xgboost_model_serialize(self, sample_data):
        """Test XGBoost model serialization."""
        X_train, y_train, X_val, y_val = sample_data
        model = XGBoostModel()
        model.train(X_train, y_train, X_val, y_val)

        serialized = model.serialize()

        assert serialized is not None
        assert isinstance(serialized, bytes)


class TestLogisticRegressionModel:
    """Test Logistic Regression model implementation."""

    @pytest.fixture
    def sample_data(self):
        """Create sample training data."""
        X_train = np.random.randn(100, 10)
        y_train = np.random.randint(0, 2, 100)
        X_val = np.random.randn(20, 10)
        y_val = np.random.randint(0, 2, 20)
        return X_train, y_train, X_val, y_val

    def test_logistic_regression_model_initialization(self):
        """Test Logistic Regression model initialization."""
        model = LogisticRegressionModel()
        assert model is not None
        assert model.model is not None
        assert model.is_trained is False

    def test_logistic_regression_model_train(self, sample_data):
        """Test Logistic Regression model training."""
        X_train, y_train, X_val, y_val = sample_data
        model = LogisticRegressionModel()

        model.train(X_train, y_train, X_val, y_val)

        assert model.is_trained is True

    def test_logistic_regression_model_predict(self, sample_data):
        """Test Logistic Regression model prediction."""
        X_train, y_train, X_val, y_val = sample_data
        model = LogisticRegressionModel()
        model.train(X_train, y_train, X_val, y_val)

        predictions = model.predict(X_val)

        assert predictions is not None
        assert len(predictions) == len(X_val)
        assert all(p in [0, 1] for p in predictions)

    def test_logistic_regression_model_predict_proba(self, sample_data):
        """Test Logistic Regression model probability prediction."""
        X_train, y_train, X_val, y_val = sample_data
        model = LogisticRegressionModel()
        model.train(X_train, y_train, X_val, y_val)

        probas = model.predict_proba(X_val)

        assert probas is not None
        assert probas.shape == (len(X_val), 2)
        assert np.all((probas >= 0) & (probas <= 1))
        assert np.allclose(probas.sum(axis=1), 1.0)

    def test_logistic_regression_model_coefficients(self, sample_data):
        """Test Logistic Regression coefficient extraction."""
        X_train, y_train, X_val, y_val = sample_data
        model = LogisticRegressionModel()
        model.train(X_train, y_train, X_val, y_val)

        coefficients = model.get_feature_importance()

        assert coefficients is not None
        assert len(coefficients) == X_train.shape[1]

    def test_logistic_regression_model_serialize(self, sample_data):
        """Test Logistic Regression model serialization."""
        X_train, y_train, X_val, y_val = sample_data
        model = LogisticRegressionModel()
        model.train(X_train, y_train, X_val, y_val)

        serialized = model.serialize()

        assert serialized is not None
        assert isinstance(serialized, bytes)


class TestLLMBaselineModel:
    """Test LLM baseline model implementation."""

    @pytest.fixture
    def sample_data(self):
        """Create sample training data."""
        X_train = np.random.randn(10, 10)
        y_train = np.random.randint(0, 2, 10)
        X_val = np.random.randn(5, 10)
        y_val = np.random.randint(0, 2, 5)
        return X_train, y_train, X_val, y_val

    def test_llm_baseline_model_initialization(self):
        """Test LLM baseline model initialization."""
        model = LLMBaselineModel()
        assert model is not None
        assert model.is_trained is False

    @patch("src.models.llm_baseline_model.openai.ChatCompletion.create")
    def test_llm_baseline_model_train(self, mock_openai, sample_data):
        """Test LLM baseline model training."""
        X_train, y_train, X_val, y_val = sample_data
        model = LLMBaselineModel()

        model.train(X_train, y_train, X_val, y_val)

        assert model.is_trained is True

    @patch("src.models.llm_baseline_model.openai.ChatCompletion.create")
    def test_llm_baseline_model_predict(self, mock_openai, sample_data):
        """Test LLM baseline model prediction."""
        mock_openai.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content='{"sentiment": 1}'))]
        )

        X_train, y_train, X_val, y_val = sample_data
        model = LLMBaselineModel()
        model.train(X_train, y_train, X_val, y_val)

        predictions = model.predict(X_val)

        assert predictions is not None
        assert len(predictions) == len(X_val)

    @patch("src.models.llm_baseline_model.openai.ChatCompletion.create")
    def test_llm_baseline_model_predict_proba(self, mock_openai, sample_data):
        """Test LLM baseline model probability prediction."""
        mock_openai.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content='{"confidence": 0.8}'))]
        )

        X_train, y_train, X_val, y_val = sample_data
        model = LLMBaselineModel()
        model.train(X_train, y_train, X_val, y_val)

        probas = model.predict_proba(X_val)

        assert probas is not None
        assert probas.shape[0] == len(X_val)

    def test_llm_baseline_model_serialize(self, sample_data):
        """Test LLM baseline model serialization."""
        X_train, y_train, X_val, y_val = sample_data
        model = LLMBaselineModel()
        model.train(X_train, y_train, X_val, y_val)

        serialized = model.serialize()

        assert serialized is not None
        assert isinstance(serialized, bytes)
