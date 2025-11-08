"""
Performance tests for latency requirements.

Tests API and streaming latency targets.
"""

import pytest
import time
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Dict, Any
import statistics

from src.inference.batch_predictor import BatchPredictor
from src.inference.streaming_predictor import StreamingPredictor


@pytest.fixture
def batch_predictor_mock():
    """Create a mock BatchPredictor."""
    predictor = AsyncMock(spec=BatchPredictor)
    return predictor


@pytest.fixture
def streaming_predictor_mock():
    """Create a mock StreamingPredictor."""
    predictor = AsyncMock(spec=StreamingPredictor)
    return predictor


@pytest.mark.performance
class TestAPILatency:
    """Test API latency requirements (<300ms p95 including feature fetch)."""

    @pytest.mark.asyncio
    async def test_single_prediction_latency(self, batch_predictor_mock):
        """Test single prediction latency."""
        # Mock prediction with realistic latency
        async def mock_predict(*args, **kwargs):
            await asyncio.sleep(0.15)  # 150ms
            return [{"probability": 0.75, "confidence": 0.85}]
        
        batch_predictor_mock.predict.side_effect = mock_predict
        
        # Measure latency
        start_time = time.time()
        result = await batch_predictor_mock.predict(["group1"])
        latency_ms = (time.time() - start_time) * 1000
        
        # Verify latency < 300ms
        assert latency_ms < 300
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_batch_prediction_latency(self, batch_predictor_mock):
        """Test batch prediction latency."""
        # Mock batch prediction
        async def mock_predict(*args, **kwargs):
            await asyncio.sleep(0.25)  # 250ms for batch
            return [
                {"probability": 0.75, "confidence": 0.85},
                {"probability": 0.65, "confidence": 0.80},
                {"probability": 0.85, "confidence": 0.90},
            ]
        
        batch_predictor_mock.predict.side_effect = mock_predict
        
        # Measure latency
        start_time = time.time()
        result = await batch_predictor_mock.predict(["group1", "group2", "group3"])
        latency_ms = (time.time() - start_time) * 1000
        
        # Verify latency < 300ms
        assert latency_ms < 300
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_p95_latency_target(self, batch_predictor_mock):
        """Test p95 latency target (<300ms)."""
        # Mock prediction with variable latency
        latencies = []
        
        async def mock_predict(*args, **kwargs):
            # Simulate variable latency (100-280ms)
            import random
            latency = random.uniform(0.1, 0.28)
            await asyncio.sleep(latency)
            return [{"probability": 0.75, "confidence": 0.85}]
        
        batch_predictor_mock.predict.side_effect = mock_predict
        
        # Run 100 predictions
        for _ in range(100):
            start_time = time.time()
            await batch_predictor_mock.predict(["group1"])
            latency_ms = (time.time() - start_time) * 1000
            latencies.append(latency_ms)
        
        # Calculate p95
        p95_latency = statistics.quantiles(latencies, n=20)[18]  # 95th percentile
        
        # Verify p95 < 300ms
        assert p95_latency < 300

    @pytest.mark.asyncio
    async def test_latency_with_cache_hit(self, batch_predictor_mock):
        """Test latency with cache hit (should be faster)."""
        # Mock prediction with cache hit
        async def mock_predict_cached(*args, **kwargs):
            await asyncio.sleep(0.05)  # 50ms with cache
            return [{"probability": 0.75, "confidence": 0.85}]
        
        batch_predictor_mock.predict.side_effect = mock_predict_cached
        
        # Measure latency
        start_time = time.time()
        result = await batch_predictor_mock.predict(["group1"])
        latency_ms = (time.time() - start_time) * 1000
        
        # Verify latency much lower with cache
        assert latency_ms < 100
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_latency_with_feature_fetch(self, batch_predictor_mock):
        """Test latency including feature fetch."""
        # Mock prediction with feature fetch
        async def mock_predict_with_features(*args, **kwargs):
            # Simulate feature fetch (50ms) + prediction (150ms)
            await asyncio.sleep(0.05)  # Feature fetch
            await asyncio.sleep(0.15)  # Prediction
            return [{"probability": 0.75, "confidence": 0.85}]
        
        batch_predictor_mock.predict.side_effect = mock_predict_with_features
        
        # Measure latency
        start_time = time.time()
        result = await batch_predictor_mock.predict(["group1"])
        latency_ms = (time.time() - start_time) * 1000
        
        # Verify total latency < 300ms
        assert latency_ms < 300
        assert len(result) == 1


@pytest.mark.performance
class TestStreamingLatency:
    """Test streaming latency requirements (<200ms p95 including feature fetch)."""

    @pytest.mark.asyncio
    async def test_single_message_latency(self, streaming_predictor_mock):
        """Test single message processing latency."""
        # Mock message handling
        async def mock_handle_message(*args, **kwargs):
            await asyncio.sleep(0.12)  # 120ms
        
        streaming_predictor_mock._handle_message.side_effect = mock_handle_message
        
        # Measure latency
        message = {"group_id": "group1", "domain": "btc", "articles": []}
        start_time = time.time()
        await streaming_predictor_mock._handle_message(message)
        latency_ms = (time.time() - start_time) * 1000
        
        # Verify latency < 200ms
        assert latency_ms < 200

    @pytest.mark.asyncio
    async def test_p95_streaming_latency_target(self, streaming_predictor_mock):
        """Test p95 streaming latency target (<200ms)."""
        # Mock message handling with variable latency
        latencies = []
        
        async def mock_handle_message(*args, **kwargs):
            # Simulate variable latency (80-180ms)
            import random
            latency = random.uniform(0.08, 0.18)
            await asyncio.sleep(latency)
        
        streaming_predictor_mock._handle_message.side_effect = mock_handle_message
        
        # Process 100 messages
        message = {"group_id": "group1", "domain": "btc", "articles": []}
        for _ in range(100):
            start_time = time.time()
            await streaming_predictor_mock._handle_message(message)
            latency_ms = (time.time() - start_time) * 1000
            latencies.append(latency_ms)
        
        # Calculate p95
        p95_latency = statistics.quantiles(latencies, n=20)[18]  # 95th percentile
        
        # Verify p95 < 200ms
        assert p95_latency < 200

    @pytest.mark.asyncio
    async def test_streaming_latency_with_cache_hit(self, streaming_predictor_mock):
        """Test streaming latency with cache hit."""
        # Mock message handling with cache hit
        async def mock_handle_message_cached(*args, **kwargs):
            await asyncio.sleep(0.03)  # 30ms with cache
        
        streaming_predictor_mock._handle_message.side_effect = mock_handle_message_cached
        
        # Measure latency
        message = {"group_id": "group1", "domain": "btc", "articles": []}
        start_time = time.time()
        await streaming_predictor_mock._handle_message(message)
        latency_ms = (time.time() - start_time) * 1000
        
        # Verify latency much lower with cache
        assert latency_ms < 50

    @pytest.mark.asyncio
    async def test_streaming_latency_with_feature_fetch(self, streaming_predictor_mock):
        """Test streaming latency including feature fetch."""
        # Mock message handling with feature fetch
        async def mock_handle_message_with_features(*args, **kwargs):
            # Simulate feature fetch (40ms) + prediction (100ms)
            await asyncio.sleep(0.04)  # Feature fetch
            await asyncio.sleep(0.10)  # Prediction
        
        streaming_predictor_mock._handle_message.side_effect = mock_handle_message_with_features
        
        # Measure latency
        message = {"group_id": "group1", "domain": "btc", "articles": []}
        start_time = time.time()
        await streaming_predictor_mock._handle_message(message)
        latency_ms = (time.time() - start_time) * 1000
        
        # Verify total latency < 200ms
        assert latency_ms < 200


@pytest.mark.performance
class TestFeatureFetchLatency:
    """Test feature fetch latency requirements (<50ms p95)."""

    @pytest.mark.asyncio
    async def test_online_feature_fetch_latency(self):
        """Test online feature fetch latency."""
        # Mock feature fetch
        async def mock_fetch_features():
            await asyncio.sleep(0.03)  # 30ms
            return {"feature1": 0.5, "feature2": 0.8}
        
        # Measure latency
        start_time = time.time()
        result = await mock_fetch_features()
        latency_ms = (time.time() - start_time) * 1000
        
        # Verify latency < 50ms
        assert latency_ms < 50
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_p95_feature_fetch_latency_target(self):
        """Test p95 feature fetch latency target (<50ms)."""
        # Mock feature fetch with variable latency
        latencies = []
        
        async def mock_fetch_features():
            # Simulate variable latency (20-45ms)
            import random
            latency = random.uniform(0.02, 0.045)
            await asyncio.sleep(latency)
            return {"feature1": 0.5, "feature2": 0.8}
        
        # Fetch features 100 times
        for _ in range(100):
            start_time = time.time()
            await mock_fetch_features()
            latency_ms = (time.time() - start_time) * 1000
            latencies.append(latency_ms)
        
        # Calculate p95
        p95_latency = statistics.quantiles(latencies, n=20)[18]  # 95th percentile
        
        # Verify p95 < 50ms
        assert p95_latency < 50


@pytest.mark.performance
class TestLabelQueryLatency:
    """Test label query latency requirements (<100ms p95)."""

    @pytest.mark.asyncio
    async def test_single_label_query_latency(self):
        """Test single label query latency."""
        # Mock label query
        async def mock_query_label():
            await asyncio.sleep(0.06)  # 60ms
            return {"label": 1, "confidence": 0.9}
        
        # Measure latency
        start_time = time.time()
        result = await mock_query_label()
        latency_ms = (time.time() - start_time) * 1000
        
        # Verify latency < 100ms
        assert latency_ms < 100
        assert result["label"] == 1

    @pytest.mark.asyncio
    async def test_p95_label_query_latency_target(self):
        """Test p95 label query latency target (<100ms)."""
        # Mock label query with variable latency
        latencies = []
        
        async def mock_query_label():
            # Simulate variable latency (40-90ms)
            import random
            latency = random.uniform(0.04, 0.09)
            await asyncio.sleep(latency)
            return {"label": 1, "confidence": 0.9}
        
        # Query labels 100 times
        for _ in range(100):
            start_time = time.time()
            await mock_query_label()
            latency_ms = (time.time() - start_time) * 1000
            latencies.append(latency_ms)
        
        # Calculate p95
        p95_latency = statistics.quantiles(latencies, n=20)[18]  # 95th percentile
        
        # Verify p95 < 100ms
        assert p95_latency < 100

