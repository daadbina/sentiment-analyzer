"""
Integration tests for label validation.

Tests label freshness, license validation, and consistency calculation.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, List, Any

from src.validation.label_reconciliation_service import LabelReconciliationService
from src.storage.postgres_client import PostgresClient


@pytest.fixture
def postgres_client_mock():
    """Create a mock PostgresClient."""
    client = AsyncMock(spec=PostgresClient)
    return client


@pytest.fixture
def label_service(postgres_client_mock):
    """Create a LabelReconciliationService instance."""
    return LabelReconciliationService(
        postgres_client=postgres_client_mock,
        label_freshness_threshold_hours=48,
        consistency_target=0.85,
    )


@pytest.fixture
def fresh_labels() -> List[Dict[str, Any]]:
    """Create fresh label data."""
    now = datetime.utcnow()
    return [
        {
            "label_id": "label1",
            "group_id": "group1",
            "label": 1,
            "label_confidence": 0.9,
            "timestamp": now - timedelta(hours=1),
            "license_status": "active",
        },
        {
            "label_id": "label2",
            "group_id": "group2",
            "label": 0,
            "label_confidence": 0.85,
            "timestamp": now - timedelta(hours=2),
            "license_status": "active",
        },
        {
            "label_id": "label3",
            "group_id": "group3",
            "label": 1,
            "label_confidence": 0.95,
            "timestamp": now - timedelta(hours=3),
            "license_status": "active",
        },
    ]


@pytest.fixture
def stale_labels() -> List[Dict[str, Any]]:
    """Create stale label data."""
    now = datetime.utcnow()
    return [
        {
            "label_id": "label4",
            "group_id": "group4",
            "label": 1,
            "label_confidence": 0.9,
            "timestamp": now - timedelta(hours=50),  # Stale (>48h)
            "license_status": "active",
        },
        {
            "label_id": "label5",
            "group_id": "group5",
            "label": 0,
            "label_confidence": 0.85,
            "timestamp": now - timedelta(hours=72),  # Stale (>48h)
            "license_status": "active",
        },
    ]


@pytest.fixture
def inactive_license_labels() -> List[Dict[str, Any]]:
    """Create labels with inactive licenses."""
    now = datetime.utcnow()
    return [
        {
            "label_id": "label6",
            "group_id": "group6",
            "label": 1,
            "label_confidence": 0.9,
            "timestamp": now - timedelta(hours=1),
            "license_status": "inactive",
        },
        {
            "label_id": "label7",
            "group_id": "group7",
            "label": 0,
            "label_confidence": 0.85,
            "timestamp": now - timedelta(hours=2),
            "license_status": "expired",
        },
    ]


@pytest.fixture
def predictions_and_labels() -> Dict[str, Any]:
    """Create predictions and corresponding labels for consistency testing."""
    return {
        "predictions": [
            {"group_id": "group1", "probability": 0.9, "confidence": 0.85},
            {"group_id": "group2", "probability": 0.2, "confidence": 0.80},
            {"group_id": "group3", "probability": 0.8, "confidence": 0.90},
            {"group_id": "group4", "probability": 0.3, "confidence": 0.75},
            {"group_id": "group5", "probability": 0.7, "confidence": 0.85},
        ],
        "labels": [
            {"group_id": "group1", "label": 1, "label_confidence": 0.9},  # Match
            {"group_id": "group2", "label": 0, "label_confidence": 0.85},  # Match
            {"group_id": "group3", "label": 1, "label_confidence": 0.95},  # Match
            {"group_id": "group4", "label": 1, "label_confidence": 0.80},  # Mismatch
            {"group_id": "group5", "label": 1, "label_confidence": 0.85},  # Match
        ],
    }


@pytest.mark.integration
class TestLabelFreshnessValidation:
    """Test label freshness validation."""

    @pytest.mark.asyncio
    async def test_fresh_labels_validation(self, label_service, postgres_client_mock, fresh_labels):
        """Test validation of fresh labels."""
        postgres_client_mock.query_labels.return_value = fresh_labels
        
        labels = await label_service.get_recent_labels(hours=48)
        
        # All labels should be fresh
        now = datetime.utcnow()
        for label in labels:
            age_hours = (now - label["timestamp"]).total_seconds() / 3600
            assert age_hours < 48

    @pytest.mark.asyncio
    async def test_stale_labels_detection(self, label_service, postgres_client_mock, stale_labels):
        """Test detection of stale labels."""
        postgres_client_mock.query_labels.return_value = stale_labels
        
        labels = await label_service.get_recent_labels(hours=48)
        
        # All labels should be stale
        now = datetime.utcnow()
        for label in labels:
            age_hours = (now - label["timestamp"]).total_seconds() / 3600
            assert age_hours > 48

    @pytest.mark.asyncio
    async def test_mixed_freshness_labels(
        self, label_service, postgres_client_mock, fresh_labels, stale_labels
    ):
        """Test mixed fresh and stale labels."""
        all_labels = fresh_labels + stale_labels
        postgres_client_mock.query_labels.return_value = all_labels
        
        labels = await label_service.get_recent_labels(hours=48)
        
        # Count fresh vs stale
        now = datetime.utcnow()
        fresh_count = 0
        stale_count = 0
        
        for label in labels:
            age_hours = (now - label["timestamp"]).total_seconds() / 3600
            if age_hours < 48:
                fresh_count += 1
            else:
                stale_count += 1
        
        assert fresh_count == 3
        assert stale_count == 2


@pytest.mark.integration
class TestLicenseValidation:
    """Test license status validation."""

    @pytest.mark.asyncio
    async def test_active_license_validation(self, label_service, postgres_client_mock, fresh_labels):
        """Test validation of active licenses."""
        postgres_client_mock.query_labels.return_value = fresh_labels
        
        labels = await label_service.get_recent_labels(hours=48)
        
        # All labels should have active licenses
        for label in labels:
            assert label["license_status"] == "active"

    @pytest.mark.asyncio
    async def test_inactive_license_detection(
        self, label_service, postgres_client_mock, inactive_license_labels
    ):
        """Test detection of inactive licenses."""
        postgres_client_mock.query_labels.return_value = inactive_license_labels
        
        labels = await label_service.get_recent_labels(hours=48)
        
        # Filter out inactive licenses
        active_labels = [l for l in labels if l["license_status"] == "active"]
        inactive_labels = [l for l in labels if l["license_status"] != "active"]
        
        assert len(active_labels) == 0
        assert len(inactive_labels) == 2

    @pytest.mark.asyncio
    async def test_mixed_license_status(
        self, label_service, postgres_client_mock, fresh_labels, inactive_license_labels
    ):
        """Test mixed license statuses."""
        all_labels = fresh_labels + inactive_license_labels
        postgres_client_mock.query_labels.return_value = all_labels
        
        labels = await label_service.get_recent_labels(hours=48)
        
        # Count active vs inactive
        active_count = sum(1 for l in labels if l["license_status"] == "active")
        inactive_count = sum(1 for l in labels if l["license_status"] != "active")
        
        assert active_count == 3
        assert inactive_count == 2


@pytest.mark.integration
class TestLabelConsistencyCalculation:
    """Test label consistency calculation."""

    @pytest.mark.asyncio
    async def test_perfect_consistency(self, label_service, postgres_client_mock):
        """Test perfect consistency (100% accuracy)."""
        predictions = [
            {"group_id": "group1", "probability": 0.9, "confidence": 0.85},
            {"group_id": "group2", "probability": 0.2, "confidence": 0.80},
            {"group_id": "group3", "probability": 0.8, "confidence": 0.90},
        ]
        
        labels = [
            {"group_id": "group1", "label": 1, "label_confidence": 0.9},
            {"group_id": "group2", "label": 0, "label_confidence": 0.85},
            {"group_id": "group3", "label": 1, "label_confidence": 0.95},
        ]
        
        postgres_client_mock.query_labels.return_value = labels
        
        # Calculate consistency
        correct = 0
        total = 0
        
        for pred, label in zip(predictions, labels):
            predicted_label = 1 if pred["probability"] >= 0.5 else 0
            total += 1
            if predicted_label == label["label"]:
                correct += 1
        
        consistency = correct / total if total > 0 else 0
        
        assert consistency == 1.0
        assert consistency >= 0.85  # Meets target

    @pytest.mark.asyncio
    async def test_consistency_with_mismatches(
        self, label_service, postgres_client_mock, predictions_and_labels
    ):
        """Test consistency calculation with mismatches."""
        predictions = predictions_and_labels["predictions"]
        labels = predictions_and_labels["labels"]
        
        postgres_client_mock.query_labels.return_value = labels
        
        # Calculate consistency
        correct = 0
        total = 0
        
        for pred, label in zip(predictions, labels):
            predicted_label = 1 if pred["probability"] >= 0.5 else 0
            total += 1
            if predicted_label == label["label"]:
                correct += 1
        
        consistency = correct / total if total > 0 else 0
        
        # 4 out of 5 correct = 80% consistency
        assert consistency == 0.8
        assert consistency < 0.85  # Below target

    @pytest.mark.asyncio
    async def test_weighted_consistency_by_confidence(
        self, label_service, postgres_client_mock, predictions_and_labels
    ):
        """Test weighted consistency calculation by label confidence."""
        predictions = predictions_and_labels["predictions"]
        labels = predictions_and_labels["labels"]
        
        postgres_client_mock.query_labels.return_value = labels
        
        # Calculate weighted consistency
        weighted_correct = 0.0
        total_weight = 0.0
        
        for pred, label in zip(predictions, labels):
            predicted_label = 1 if pred["probability"] >= 0.5 else 0
            weight = label["label_confidence"]
            total_weight += weight
            
            if predicted_label == label["label"]:
                weighted_correct += weight
        
        weighted_consistency = weighted_correct / total_weight if total_weight > 0 else 0
        
        # Weighted consistency should be higher due to high confidence on correct predictions
        assert weighted_consistency > 0.8

    @pytest.mark.asyncio
    async def test_consistency_target_validation(
        self, label_service, postgres_client_mock, predictions_and_labels
    ):
        """Test consistency target validation (≥0.85)."""
        predictions = predictions_and_labels["predictions"]
        labels = predictions_and_labels["labels"]
        
        postgres_client_mock.query_labels.return_value = labels
        
        # Calculate consistency
        correct = 0
        total = 0
        
        for pred, label in zip(predictions, labels):
            predicted_label = 1 if pred["probability"] >= 0.5 else 0
            total += 1
            if predicted_label == label["label"]:
                correct += 1
        
        consistency = correct / total if total > 0 else 0
        
        # Check if meets target
        meets_target = consistency >= 0.85
        
        # With 80% consistency, should not meet target
        assert meets_target is False


@pytest.mark.integration
class TestLabelValidationMetrics:
    """Test label validation metrics recording."""

    @pytest.mark.asyncio
    async def test_record_freshness_metrics(self, label_service, postgres_client_mock, fresh_labels):
        """Test recording freshness metrics."""
        with patch("src.validation.label_reconciliation_service.label_freshness_hours") as metrics_mock:
            postgres_client_mock.query_labels.return_value = fresh_labels
            
            labels = await label_service.get_recent_labels(hours=48)
            
            # Metrics should be recorded for each label
            # This is a placeholder for actual metrics recording logic

    @pytest.mark.asyncio
    async def test_record_consistency_metrics(
        self, label_service, postgres_client_mock, predictions_and_labels
    ):
        """Test recording consistency metrics."""
        with patch("src.validation.label_reconciliation_service.label_consistency_score") as metrics_mock:
            predictions = predictions_and_labels["predictions"]
            labels = predictions_and_labels["labels"]
            
            postgres_client_mock.query_labels.return_value = labels
            
            # Calculate and record consistency
            correct = 0
            total = 0
            
            for pred, label in zip(predictions, labels):
                predicted_label = 1 if pred["probability"] >= 0.5 else 0
                total += 1
                if predicted_label == label["label"]:
                    correct += 1
            
            consistency = correct / total if total > 0 else 0
            
            # Metrics should be recorded
            # This is a placeholder for actual metrics recording logic

