"""Tests for batch processor."""

import pytest
from src.optimization.batch_processor import (
    BatchProcessor,
    BatchResult,
    DatabaseBatchOperations,
    RedisBatchOperations,
)


class TestBatchResult:
    """Test batch result."""

    def test_batch_result_creation(self):
        """Test creating batch result."""
        result = BatchResult(
            total_items=10,
            successful_items=8,
            failed_items=2,
            results=[1, 2, 3],
            errors=["error1", "error2"],
        )
        assert result.total_items == 10
        assert result.successful_items == 8
        assert result.failed_items == 2

    def test_batch_result_success_rate(self):
        """Test batch result success rate."""
        result = BatchResult(
            total_items=10,
            successful_items=8,
            failed_items=2,
            results=[],
            errors=[],
        )
        assert result.success_rate == 0.8

    def test_batch_result_success_rate_zero(self):
        """Test batch result success rate with zero items."""
        result = BatchResult(
            total_items=0,
            successful_items=0,
            failed_items=0,
            results=[],
            errors=[],
        )
        assert result.success_rate == 0.0


class TestBatchProcessor:
    """Test batch processor."""

    def test_batch_processor_initialization(self):
        """Test batch processor initialization."""
        processor = BatchProcessor()
        assert processor.batch_size == 100
        assert processor.max_workers == 4

    def test_batch_processor_custom_parameters(self):
        """Test batch processor with custom parameters."""
        processor = BatchProcessor(batch_size=50, max_workers=8)
        assert processor.batch_size == 50
        assert processor.max_workers == 8

    @pytest.mark.asyncio
    async def test_batch_processor_empty_items(self):
        """Test batch processor with empty items."""
        processor = BatchProcessor()

        async def dummy_processor(item):
            return item

        result = await processor.process_batch([], dummy_processor)
        assert result.total_items == 0
        assert result.successful_items == 0
        assert result.failed_items == 0

    @pytest.mark.asyncio
    async def test_batch_processor_successful_processing(self):
        """Test batch processor with successful processing."""
        processor = BatchProcessor(batch_size=10)

        async def dummy_processor(item):
            return item * 2

        items = [1, 2, 3, 4, 5]
        result = await processor.process_batch(items, dummy_processor)
        assert result.total_items == 5
        assert result.successful_items == 5
        assert result.failed_items == 0
        assert len(result.results) == 5

    @pytest.mark.asyncio
    async def test_batch_processor_with_failures(self):
        """Test batch processor with some failures."""
        processor = BatchProcessor(batch_size=10)

        async def processor_with_errors(item):
            if item == 3:
                raise ValueError("Test error")
            return item * 2

        items = [1, 2, 3, 4, 5]
        result = await processor.process_batch(items, processor_with_errors)
        assert result.total_items == 5
        assert result.successful_items == 4
        assert result.failed_items == 1

    @pytest.mark.asyncio
    async def test_batch_processor_sequential(self):
        """Test batch processor sequential processing."""
        processor = BatchProcessor()

        async def dummy_processor(item):
            return item * 2

        items = [1, 2, 3, 4, 5]
        result = await processor.process_batch_sequential(items, dummy_processor)
        assert result.total_items == 5
        assert result.successful_items == 5
        assert result.failed_items == 0

    @pytest.mark.asyncio
    async def test_batch_processor_sequential_empty(self):
        """Test batch processor sequential with empty items."""
        processor = BatchProcessor()

        async def dummy_processor(item):
            return item

        result = await processor.process_batch_sequential([], dummy_processor)
        assert result.total_items == 0


class TestDatabaseBatchOperations:
    """Test database batch operations."""

    def test_db_batch_operations_initialization(self):
        """Test database batch operations initialization."""
        ops = DatabaseBatchOperations(None)
        assert ops is not None
        assert ops.batch_size == 100

    def test_db_batch_operations_custom_batch_size(self):
        """Test database batch operations with custom batch size."""
        ops = DatabaseBatchOperations(None, batch_size=50)
        assert ops.batch_size == 50

    @pytest.mark.asyncio
    async def test_db_batch_insert_empty(self):
        """Test batch insert with empty records."""
        ops = DatabaseBatchOperations(None)
        result = await ops.batch_insert("test_table", [])
        assert result == 0

    @pytest.mark.asyncio
    async def test_db_batch_insert_records(self):
        """Test batch insert with records."""
        ops = DatabaseBatchOperations(None)
        records = [{"id": 1}, {"id": 2}, {"id": 3}]
        result = await ops.batch_insert("test_table", records)
        assert result == 3

    @pytest.mark.asyncio
    async def test_db_batch_update_empty(self):
        """Test batch update with empty updates."""
        ops = DatabaseBatchOperations(None)
        result = await ops.batch_update("test_table", [])
        assert result == 0

    @pytest.mark.asyncio
    async def test_db_batch_update_records(self):
        """Test batch update with records."""
        ops = DatabaseBatchOperations(None)
        updates = [{"id": 1}, {"id": 2}]
        result = await ops.batch_update("test_table", updates)
        assert result == 2


class TestRedisBatchOperations:
    """Test Redis batch operations."""

    def test_redis_batch_operations_initialization(self):
        """Test Redis batch operations initialization."""
        ops = RedisBatchOperations(None)
        assert ops is not None
        assert ops.batch_size == 100

    def test_redis_batch_operations_custom_batch_size(self):
        """Test Redis batch operations with custom batch size."""
        ops = RedisBatchOperations(None, batch_size=50)
        assert ops.batch_size == 50

    @pytest.mark.asyncio
    async def test_redis_batch_set_empty(self):
        """Test batch set with empty keys."""
        ops = RedisBatchOperations(None)
        result = await ops.batch_set({})
        assert result == 0

    @pytest.mark.asyncio
    async def test_redis_batch_set_keys(self):
        """Test batch set with keys."""
        # Create a mock redis client
        class MockRedis:
            async def setex(self, key, ttl, value):
                pass
            async def set(self, key, value):
                pass

        ops = RedisBatchOperations(MockRedis())
        key_values = {"key1": "value1", "key2": "value2"}
        result = await ops.batch_set(key_values)
        assert result == 2

    @pytest.mark.asyncio
    async def test_redis_batch_delete_empty(self):
        """Test batch delete with empty keys."""
        ops = RedisBatchOperations(None)
        result = await ops.batch_delete([])
        assert result == 0

    @pytest.mark.asyncio
    async def test_redis_batch_delete_keys(self):
        """Test batch delete with keys."""
        # Create a mock redis client
        class MockRedis:
            async def delete(self, key):
                pass

        ops = RedisBatchOperations(MockRedis())
        keys = ["key1", "key2", "key3"]
        result = await ops.batch_delete(keys)
        assert result == 3

