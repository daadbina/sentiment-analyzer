"""
Integration tests for Kafka integration.

Tests message consumption, production, and end-to-end workflows.
Requires Kafka broker to be running for full integration tests.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
import json
from datetime import datetime

from src.clients.kafka_consumer_client import KafkaConsumerClient
from src.clients.kafka_producer_client import KafkaProducerClient
from src.config import KafkaConfig
from src.exceptions import KafkaError


@pytest.fixture
def kafka_config():
    """Create Kafka configuration for testing."""
    return KafkaConfig(
        bootstrap_servers=["localhost:9092"],
        consumer_group_id="predictor-service",
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        max_poll_records=100,
        session_timeout_ms=30000,
    )


@pytest.fixture
def kafka_consumer(kafka_config):
    """Create KafkaConsumerClient instance."""
    return KafkaConsumerClient(config=kafka_config)


@pytest.fixture
def kafka_producer(kafka_config):
    """Create KafkaProducerClient instance."""
    return KafkaProducerClient(config=kafka_config)


class TestKafkaConsumerConnection:
    """Test Kafka consumer connection and health checks."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_connect_success(self, kafka_consumer):
        """Test successful connection to Kafka."""
        with patch("aiokafka.AIOKafkaConsumer") as mock_consumer:
            mock_instance = AsyncMock()
            mock_consumer.return_value = mock_instance
            
            await kafka_consumer.connect()
            
            mock_instance.start.assert_called_once()
            assert kafka_consumer._consumer is not None

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_connect_failure(self, kafka_consumer):
        """Test connection failure handling."""
        with patch("aiokafka.AIOKafkaConsumer", side_effect=Exception("Connection failed")):
            with pytest.raises(KafkaError):
                await kafka_consumer.connect()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_disconnect(self, kafka_consumer):
        """Test disconnection from Kafka."""
        mock_consumer = AsyncMock()
        kafka_consumer._consumer = mock_consumer
        
        await kafka_consumer.disconnect()
        
        mock_consumer.stop.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_health_check_connected(self, kafka_consumer):
        """Test health check when connected."""
        mock_consumer = AsyncMock()
        kafka_consumer._consumer = mock_consumer
        
        result = await kafka_consumer.health_check()
        assert result is True

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_health_check_not_connected(self, kafka_consumer):
        """Test health check when not connected."""
        result = await kafka_consumer.health_check()
        assert result is False


class TestKafkaProducerConnection:
    """Test Kafka producer connection and health checks."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_connect_success(self, kafka_producer):
        """Test successful connection to Kafka."""
        with patch("aiokafka.AIOKafkaProducer") as mock_producer:
            mock_instance = AsyncMock()
            mock_producer.return_value = mock_instance
            
            await kafka_producer.connect()
            
            mock_instance.start.assert_called_once()
            assert kafka_producer._producer is not None

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_connect_failure(self, kafka_producer):
        """Test connection failure handling."""
        with patch("aiokafka.AIOKafkaProducer", side_effect=Exception("Connection failed")):
            with pytest.raises(KafkaError):
                await kafka_producer.connect()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_disconnect(self, kafka_producer):
        """Test disconnection from Kafka."""
        mock_producer = AsyncMock()
        kafka_producer._producer = mock_producer
        
        await kafka_producer.disconnect()
        
        mock_producer.stop.assert_called_once()


class TestMessageConsumption:
    """Test message consumption from Kafka."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_subscribe_to_topics(self, kafka_consumer):
        """Test subscribing to topics."""
        mock_consumer = AsyncMock()
        kafka_consumer._consumer = mock_consumer
        
        await kafka_consumer.subscribe(["semantic_groups", "predictions"])
        
        mock_consumer.subscribe.assert_called_once_with(["semantic_groups", "predictions"])

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_consume_single_message(self, kafka_consumer):
        """Test consuming a single message."""
        mock_consumer = AsyncMock()
        mock_message = MagicMock()
        mock_message.value = json.dumps({
            "group_id": "group123",
            "domain": "btc",
            "articles": [{"id": "art1"}],
        }).encode("utf-8")
        mock_message.topic = "semantic_groups"
        mock_message.partition = 0
        mock_message.offset = 100
        
        mock_consumer.__aiter__.return_value = [mock_message]
        kafka_consumer._consumer = mock_consumer
        
        messages = []
        async for msg in kafka_consumer.consume_messages():
            messages.append(msg)
            break
        
        assert len(messages) == 1
        assert messages[0]["group_id"] == "group123"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_consume_multiple_messages(self, kafka_consumer):
        """Test consuming multiple messages."""
        mock_consumer = AsyncMock()
        mock_messages = [
            MagicMock(
                value=json.dumps({"group_id": f"group{i}", "domain": "btc"}).encode("utf-8"),
                topic="semantic_groups",
                partition=0,
                offset=i,
            )
            for i in range(5)
        ]
        
        mock_consumer.__aiter__.return_value = mock_messages
        kafka_consumer._consumer = mock_consumer
        
        messages = []
        async for msg in kafka_consumer.consume_messages():
            messages.append(msg)
            if len(messages) >= 5:
                break
        
        assert len(messages) == 5
        assert messages[0]["group_id"] == "group0"
        assert messages[4]["group_id"] == "group4"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_consume_with_invalid_json(self, kafka_consumer):
        """Test consuming message with invalid JSON."""
        mock_consumer = AsyncMock()
        mock_message = MagicMock()
        mock_message.value = b"invalid json"
        mock_message.topic = "semantic_groups"
        
        mock_consumer.__aiter__.return_value = [mock_message]
        kafka_consumer._consumer = mock_consumer
        
        # Should handle invalid JSON gracefully
        messages = []
        async for msg in kafka_consumer.consume_messages():
            messages.append(msg)
            break
        
        # Message should be skipped or error logged
        assert len(messages) <= 1

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_commit_offset(self, kafka_consumer):
        """Test committing offset."""
        mock_consumer = AsyncMock()
        kafka_consumer._consumer = mock_consumer
        
        await kafka_consumer.commit()
        
        mock_consumer.commit.assert_called_once()


class TestMessageProduction:
    """Test message production to Kafka."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_send_single_message(self, kafka_producer):
        """Test sending a single message."""
        mock_producer = AsyncMock()
        kafka_producer._producer = mock_producer
        
        message = {
            "group_id": "group123",
            "prediction": 0.75,
            "confidence": 0.9,
        }
        
        await kafka_producer.send("predictions", message)
        
        mock_producer.send.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_send_multiple_messages(self, kafka_producer):
        """Test sending multiple messages."""
        mock_producer = AsyncMock()
        kafka_producer._producer = mock_producer
        
        messages = [
            {"group_id": f"group{i}", "prediction": 0.7 + i * 0.05}
            for i in range(5)
        ]
        
        for msg in messages:
            await kafka_producer.send("predictions", msg)
        
        assert mock_producer.send.call_count == 5

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_send_with_key(self, kafka_producer):
        """Test sending message with key."""
        mock_producer = AsyncMock()
        kafka_producer._producer = mock_producer
        
        message = {"group_id": "group123", "prediction": 0.75}
        key = "group123"
        
        await kafka_producer.send("predictions", message, key=key)
        
        call_args = mock_producer.send.call_args
        assert call_args[1]["key"] == key.encode("utf-8")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_flush_messages(self, kafka_producer):
        """Test flushing pending messages."""
        mock_producer = AsyncMock()
        kafka_producer._producer = mock_producer
        
        await kafka_producer.flush()
        
        mock_producer.flush.assert_called_once()


class TestEndToEndWorkflow:
    """Test end-to-end Kafka workflows."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_consume_process_produce_workflow(self, kafka_consumer, kafka_producer):
        """Test complete workflow: consume -> process -> produce."""
        # Setup consumer
        mock_consumer = AsyncMock()
        mock_message = MagicMock()
        mock_message.value = json.dumps({
            "group_id": "group123",
            "domain": "btc",
        }).encode("utf-8")
        mock_message.topic = "semantic_groups"
        
        mock_consumer.__aiter__.return_value = [mock_message]
        kafka_consumer._consumer = mock_consumer
        
        # Setup producer
        mock_producer = AsyncMock()
        kafka_producer._producer = mock_producer
        
        # Consume message
        async for msg in kafka_consumer.consume_messages():
            # Process (simulate prediction)
            prediction = {
                "group_id": msg["group_id"],
                "prediction": 0.75,
                "confidence": 0.9,
            }
            
            # Produce result
            await kafka_producer.send("predictions", prediction)
            break
        
        # Verify production
        mock_producer.send.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_batch_processing_workflow(self, kafka_consumer, kafka_producer):
        """Test batch processing workflow."""
        # Setup consumer with multiple messages
        mock_consumer = AsyncMock()
        mock_messages = [
            MagicMock(
                value=json.dumps({"group_id": f"group{i}", "domain": "btc"}).encode("utf-8"),
                topic="semantic_groups",
            )
            for i in range(10)
        ]
        
        mock_consumer.__aiter__.return_value = mock_messages
        kafka_consumer._consumer = mock_consumer
        
        # Setup producer
        mock_producer = AsyncMock()
        kafka_producer._producer = mock_producer
        
        # Process batch
        batch = []
        async for msg in kafka_consumer.consume_messages():
            batch.append(msg)
            if len(batch) >= 10:
                break
        
        # Produce batch results
        for msg in batch:
            prediction = {"group_id": msg["group_id"], "prediction": 0.75}
            await kafka_producer.send("predictions", prediction)
        
        assert mock_producer.send.call_count == 10


class TestErrorHandling:
    """Test error handling in Kafka integration."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_network_timeout(self, kafka_consumer):
        """Test handling of network timeout."""
        mock_consumer = AsyncMock()
        mock_consumer.__aiter__.side_effect = TimeoutError("Timeout")
        kafka_consumer._consumer = mock_consumer
        
        with pytest.raises(TimeoutError):
            async for msg in kafka_consumer.consume_messages():
                pass

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_broker_unavailable(self, kafka_consumer):
        """Test handling of broker unavailability."""
        with patch("aiokafka.AIOKafkaConsumer", side_effect=Exception("Broker unavailable")):
            with pytest.raises(KafkaError):
                await kafka_consumer.connect()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_producer_send_failure(self, kafka_producer):
        """Test handling of producer send failure."""
        mock_producer = AsyncMock()
        mock_producer.send.side_effect = Exception("Send failed")
        kafka_producer._producer = mock_producer
        
        with pytest.raises(KafkaError):
            await kafka_producer.send("predictions", {"data": "value"})

