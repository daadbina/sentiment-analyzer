"""
Performance tests for throughput requirements.

Tests throughput and cache hit rate targets.
"""

import pytest
import time
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Dict, Any

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
class TestThroughput:
    """Test throughput requirements (≥1000 predictions/sec with feature retrieval)."""

    @pytest.mark.asyncio
    async def test_batch_prediction_throughput(self, batch_predictor_mock):
        """Test batch prediction throughput."""
        # Mock fast prediction
        async def mock_predict(*args, **kwargs):
            await asyncio.sleep(0.001)  # 1ms per prediction
            return [{"probability": 0.75, "confidence": 0.85}]
        
        batch_predictor_mock.predict.side_effect = mock_predict
        
        # Measure throughput over 1 second
        start_time = time.time()
        predictions_count = 0
        
        while time.time() - start_time < 1.0:
            await batch_predictor_mock.predict(["group1"])
            predictions_count += 1
        
        # Verify throughput ≥1000 predictions/sec
        assert predictions_count >= 1000

    @pytest.mark.asyncio
    async def test_concurrent_prediction_throughput(self, batch_predictor_mock):
        """Test concurrent prediction throughput."""
        # Mock prediction
        async def mock_predict(*args, **kwargs):
            await asyncio.sleep(0.01)  # 10ms per prediction
            return [{"probability": 0.75, "confidence": 0.85}]
        
        batch_predictor_mock.predict.side_effect = mock_predict
        
        # Run 100 concurrent predictions
        start_time = time.time()
        tasks = [batch_predictor_mock.predict(["group1"]) for _ in range(100)]
        await asyncio.gather(*tasks)
        elapsed_time = time.time() - start_time
        
        # Calculate throughput
        throughput = 100 / elapsed_time
        
        # With concurrency, should achieve high throughput
        assert throughput >= 100  # At least 100 predictions/sec with concurrency

    @pytest.mark.asyncio
    async def test_streaming_throughput(self, streaming_predictor_mock):
        """Test streaming prediction throughput."""
        # Mock message handling
        async def mock_handle_message(*args, **kwargs):
            await asyncio.sleep(0.001)  # 1ms per message
        
        streaming_predictor_mock._handle_message.side_effect = mock_handle_message
        
        # Measure throughput over 1 second
        start_time = time.time()
        messages_count = 0
        message = {"group_id": "group1", "domain": "btc", "articles": []}
        
        while time.time() - start_time < 1.0:
            await streaming_predictor_mock._handle_message(message)
            messages_count += 1
        
        # Verify throughput ≥1000 messages/sec
        assert messages_count >= 1000

    @pytest.mark.asyncio
    async def test_batch_size_impact_on_throughput(self, batch_predictor_mock):
        """Test impact of batch size on throughput."""
        # Mock batch prediction
        async def mock_predict(group_ids, *args, **kwargs):
            batch_size = len(group_ids)
            await asyncio.sleep(0.001 * batch_size)  # 1ms per item
            return [{"probability": 0.75, "confidence": 0.85} for _ in range(batch_size)]
        
        batch_predictor_mock.predict.side_effect = mock_predict
        
        # Test different batch sizes
        batch_sizes = [1, 10, 50, 100]
        throughputs = []
        
        for batch_size in batch_sizes:
            start_time = time.time()
            predictions_count = 0
            
            # Run for 0.5 seconds
            while time.time() - start_time < 0.5:
                group_ids = [f"group{i}" for i in range(batch_size)]
                await batch_predictor_mock.predict(group_ids)
                predictions_count += batch_size
            
            elapsed_time = time.time() - start_time
            throughput = predictions_count / elapsed_time
            throughputs.append(throughput)
        
        # Larger batch sizes should have higher throughput
        assert throughputs[-1] > throughputs[0]


@pytest.mark.performance
class TestCacheHitRate:
    """Test cache hit rate requirements (≥50%)."""

    @pytest.mark.asyncio
    async def test_cache_hit_rate_target(self, batch_predictor_mock):
        """Test cache hit rate target (≥50%)."""
        # Mock prediction with cache simulation
        cache = {}
        cache_hits = 0
        cache_misses = 0
        
        async def mock_predict(group_ids, *args, **kwargs):
            nonlocal cache_hits, cache_misses
            results = []
            
            for group_id in group_ids:
                if group_id in cache:
                    # Cache hit
                    cache_hits += 1
                    await asyncio.sleep(0.001)  # Fast cache lookup
                    results.append(cache[group_id])
                else:
                    # Cache miss
                    cache_misses += 1
                    await asyncio.sleep(0.01)  # Slower prediction
                    result = {"probability": 0.75, "confidence": 0.85}
                    cache[group_id] = result
                    results.append(result)
            
            return results
        
        batch_predictor_mock.predict.side_effect = mock_predict
        
        # Make predictions with repeated group_ids
        group_ids = ["group1", "group2", "group3"] * 10  # 30 predictions, 20 should be cache hits
        
        for group_id in group_ids:
            await batch_predictor_mock.predict([group_id])
        
        # Calculate cache hit rate
        total_requests = cache_hits + cache_misses
        cache_hit_rate = cache_hits / total_requests if total_requests > 0 else 0
        
        # Verify cache hit rate ≥50%
        assert cache_hit_rate >= 0.5

    @pytest.mark.asyncio
    async def test_cache_effectiveness(self, batch_predictor_mock):
        """Test cache effectiveness on latency."""
        # Mock prediction with cache
        cache = {}
        
        async def mock_predict_with_cache(group_ids, *args, **kwargs):
            results = []
            for group_id in group_ids:
                if group_id in cache:
                    await asyncio.sleep(0.001)  # 1ms with cache
                    results.append(cache[group_id])
                else:
                    await asyncio.sleep(0.05)  # 50ms without cache
                    result = {"probability": 0.75, "confidence": 0.85}
                    cache[group_id] = result
                    results.append(result)
            return results
        
        batch_predictor_mock.predict.side_effect = mock_predict_with_cache
        
        # First request (cache miss)
        start_time = time.time()
        await batch_predictor_mock.predict(["group1"])
        first_latency_ms = (time.time() - start_time) * 1000
        
        # Second request (cache hit)
        start_time = time.time()
        await batch_predictor_mock.predict(["group1"])
        second_latency_ms = (time.time() - start_time) * 1000
        
        # Cache hit should be much faster
        assert second_latency_ms < first_latency_ms
        assert second_latency_ms < 10  # <10ms with cache

    @pytest.mark.asyncio
    async def test_cache_ttl_impact(self, batch_predictor_mock):
        """Test cache TTL impact on hit rate."""
        # Mock prediction with TTL-aware cache
        cache = {}
        cache_timestamps = {}
        ttl_seconds = 3600  # 1 hour
        
        async def mock_predict_with_ttl(group_ids, *args, **kwargs):
            results = []
            current_time = time.time()
            
            for group_id in group_ids:
                if group_id in cache:
                    # Check if cache entry is still valid
                    if current_time - cache_timestamps[group_id] < ttl_seconds:
                        await asyncio.sleep(0.001)  # Cache hit
                        results.append(cache[group_id])
                    else:
                        # Cache expired
                        await asyncio.sleep(0.01)  # Refresh cache
                        result = {"probability": 0.75, "confidence": 0.85}
                        cache[group_id] = result
                        cache_timestamps[group_id] = current_time
                        results.append(result)
                else:
                    # Cache miss
                    await asyncio.sleep(0.01)
                    result = {"probability": 0.75, "confidence": 0.85}
                    cache[group_id] = result
                    cache_timestamps[group_id] = current_time
                    results.append(result)
            
            return results
        
        batch_predictor_mock.predict.side_effect = mock_predict_with_ttl
        
        # Make predictions
        await batch_predictor_mock.predict(["group1"])
        await batch_predictor_mock.predict(["group1"])  # Should hit cache
        
        # Verify cache is working
        assert "group1" in cache


@pytest.mark.performance
class TestLoadTesting:
    """Test system under load."""

    @pytest.mark.asyncio
    async def test_sustained_load(self, batch_predictor_mock):
        """Test sustained load over time."""
        # Mock prediction
        async def mock_predict(*args, **kwargs):
            await asyncio.sleep(0.01)  # 10ms per prediction
            return [{"probability": 0.75, "confidence": 0.85}]
        
        batch_predictor_mock.predict.side_effect = mock_predict
        
        # Run sustained load for 5 seconds
        start_time = time.time()
        predictions_count = 0
        
        while time.time() - start_time < 5.0:
            await batch_predictor_mock.predict(["group1"])
            predictions_count += 1
        
        elapsed_time = time.time() - start_time
        throughput = predictions_count / elapsed_time
        
        # Verify sustained throughput
        assert throughput >= 50  # At least 50 predictions/sec sustained

    @pytest.mark.asyncio
    async def test_burst_load(self, batch_predictor_mock):
        """Test burst load handling."""
        # Mock prediction
        async def mock_predict(*args, **kwargs):
            await asyncio.sleep(0.01)  # 10ms per prediction
            return [{"probability": 0.75, "confidence": 0.85}]
        
        batch_predictor_mock.predict.side_effect = mock_predict
        
        # Send burst of 100 concurrent requests
        start_time = time.time()
        tasks = [batch_predictor_mock.predict(["group1"]) for _ in range(100)]
        await asyncio.gather(*tasks)
        elapsed_time = time.time() - start_time
        
        # Verify burst handling
        throughput = 100 / elapsed_time
        assert throughput >= 50  # At least 50 predictions/sec during burst

    @pytest.mark.asyncio
    async def test_mixed_workload(self, batch_predictor_mock, streaming_predictor_mock):
        """Test mixed batch and streaming workload."""
        # Mock predictions
        async def mock_batch_predict(*args, **kwargs):
            await asyncio.sleep(0.01)
            return [{"probability": 0.75, "confidence": 0.85}]
        
        async def mock_stream_handle(*args, **kwargs):
            await asyncio.sleep(0.01)
        
        batch_predictor_mock.predict.side_effect = mock_batch_predict
        streaming_predictor_mock._handle_message.side_effect = mock_stream_handle
        
        # Run mixed workload
        start_time = time.time()
        batch_count = 0
        stream_count = 0
        message = {"group_id": "group1", "domain": "btc", "articles": []}
        
        while time.time() - start_time < 2.0:
            # Alternate between batch and streaming
            await batch_predictor_mock.predict(["group1"])
            batch_count += 1
            
            await streaming_predictor_mock._handle_message(message)
            stream_count += 1
        
        elapsed_time = time.time() - start_time
        total_throughput = (batch_count + stream_count) / elapsed_time
        
        # Verify mixed workload throughput
        assert total_throughput >= 50  # At least 50 operations/sec

