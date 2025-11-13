"""
Kafka consumer client for consuming computed features and ground-truth messages.

Provides abstraction over confluent-kafka for consuming messages with Avro deserialization.
Implements exactly-once semantics and proper offset management.
"""

import asyncio
import json
import logging
from collections.abc import Callable
from typing import Any

from confluent_kafka import Consumer, KafkaError, KafkaException
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroDeserializer
from confluent_kafka.serialization import SerializationContext, MessageField

from ..config import KafkaConfig
from ..exceptions import KafkaError as KafkaErrorException
from ..metrics import kafka_consumer_lag, kafka_errors_total, kafka_messages_consumed_total
from ..utils.trace import trace_span

logger = logging.getLogger(__name__)


class KafkaConsumerClient:
    """
    Client for consuming messages from Kafka topics.

    Provides methods for consuming messages with Avro deserialization.
    Handles offset management and error recovery.
    """

    def __init__(self, config: KafkaConfig):
        """
        Initialize Kafka consumer client.

        Args:
            config: Kafka configuration
        """
        self.config = config
        self._consumer: Consumer | None = None
        self._deserializer: AvroDeserializer | None = None
        self._running = False
        self._skipped_messages_count = 0
        self._last_skipped_log_count = 0

        logger.info(
            f"Initializing Kafka consumer: brokers={config.bootstrap_servers}, "
            f"group={config.consumer_group_id}"
        )

    async def connect(self) -> None:
        """
        Connect to Kafka and create consumer.

        Raises:
            KafkaErrorException: If connection fails
        """
        try:
            logger.info(f"Connecting to Kafka: {self.config.bootstrap_servers}")

            # Build consumer configuration
            consumer_config = {
                "bootstrap.servers": self.config.bootstrap_servers,
                "group.id": self.config.consumer_group_id,
                "auto.offset.reset": "earliest",
                "enable.auto.commit": False,  # Manual commit for exactly-once
                "max.poll.interval.ms": 300000,  # 5 minutes
                "session.timeout.ms": 30000,  # 30 seconds
                "heartbeat.interval.ms": 10000,  # 10 seconds
            }

            # Add TLS configuration if enabled
            if self.config.enable_tls:
                consumer_config.update(
                    {
                        "security.protocol": "SSL",
                        "ssl.ca.location": self.config.tls_ca_cert,
                        "ssl.certificate.location": self.config.tls_client_cert,
                        "ssl.key.location": self.config.tls_client_key,
                    }
                )

            # Create regular consumer (not AvroConsumer)
            self._consumer = Consumer(consumer_config)

            # Create schema registry client and deserializer
            schema_registry_client = SchemaRegistryClient(
                {"url": self.config.schema_registry_url}
            )

            # Define the features_computed schema (must match feature-engineering-service output)
            features_computed_schema = {
                "type": "record",
                "name": "FeaturesComputedMessage",
                "namespace": "com.sentiment_analyzer.feature_engineering",
                "fields": [
                    {"name": "group_id", "type": "string"},
                    {
                        "name": "features",
                        "type": {
                            "type": "map",
                            "values": ["null", "double", "int", "string", "boolean"]
                        }
                    },
                    {"name": "timestamp", "type": "long"},
                    {"name": "feature_version", "type": "string"},
                    {"name": "feature_count", "type": "int"},
                    {
                        "name": "validation_status",
                        "type": {
                            "type": "enum",
                            "name": "ValidationStatus",
                            "symbols": ["VALID", "INVALID", "PARTIAL"]
                        }
                    },
                    {"name": "validation_failures", "type": {"type": "array", "items": "string"}},
                    {"name": "computation_duration_ms", "type": "long"},
                    {"name": "trace_id", "type": "string"},
                    {"name": "schema_version", "type": "string"}
                ]
            }

            # Create Avro deserializer
            self._deserializer = AvroDeserializer(
                schema_registry_client,
                json.dumps(features_computed_schema)
            )

            logger.info(
                f"Connected to Kafka: brokers={self.config.bootstrap_servers}, "
                f"group={self.config.consumer_group_id}"
            )
        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {e}", exc_info=True)
            raise KafkaErrorException(
                f"Failed to connect to Kafka: {e}",
                operation="connect",
            ) from e

    async def disconnect(self) -> None:
        """Disconnect from Kafka and close consumer."""
        if self._consumer:
            logger.info("Disconnecting from Kafka consumer")
            self._running = False
            self._consumer.close()
            self._consumer = None

    def _ensure_connected(self) -> Consumer:
        """
        Ensure consumer is connected.

        Returns:
            Consumer instance

        Raises:
            KafkaErrorException: If not connected
        """
        if self._consumer is None:
            raise KafkaErrorException(
                "Kafka consumer not connected. Call connect() first.",
                operation="ensure_connected",
            )
        return self._consumer

    async def subscribe(self, topics: list[str]) -> None:
        """
        Subscribe to Kafka topics.

        Args:
            topics: List of topic names to subscribe to

        Raises:
            KafkaErrorException: If subscription fails
        """
        consumer = self._ensure_connected()

        try:
            logger.info(f"Subscribing to topics: {topics}")
            consumer.subscribe(topics)
            logger.info(f"Subscribed to topics: {topics}")
        except Exception as e:
            logger.error(f"Failed to subscribe to topics: {e}", exc_info=True)
            raise KafkaErrorException(
                f"Failed to subscribe to topics: {e}",
                operation="subscribe",
            ) from e

    async def consume_messages(
        self,
        message_handler: Callable[[dict[str, Any], str], None],
        poll_timeout: float = 1.0,
        trace_id: str | None = None,
    ) -> None:
        """
        Consume messages from subscribed topics.

        Args:
            message_handler: Async callback function to handle messages
                Signature: async def handler(message: dict, topic: str) -> None
            poll_timeout: Timeout for polling in seconds
            trace_id: Optional trace ID for distributed tracing

        Raises:
            KafkaErrorException: If consumption fails
        """
        consumer = self._ensure_connected()
        self._running = True

        logger.info("Starting message consumption")

        try:
            while self._running:
                try:
                    # Poll for messages (blocking call in thread pool)
                    msg = await asyncio.get_event_loop().run_in_executor(
                        None,
                        consumer.poll,
                        poll_timeout,
                    )

                    if msg is None:
                        # No message received within timeout
                        continue

                    if msg.error():
                        # Handle Kafka errors
                        if msg.error().code() == KafkaError._PARTITION_EOF:
                            # End of partition, not an error
                            logger.debug(f"Reached end of partition: {msg.topic()}[{msg.partition()}]")
                            continue
                        # Real error
                        error_msg = f"Kafka error: {msg.error()}"
                        logger.error(error_msg)
                        kafka_errors_total.labels(
                            topic=msg.topic(),
                            operation="consume",
                            error_type=msg.error().name(),
                        ).inc()
                        raise KafkaException(msg.error())

                    # Process message
                    await self._process_message(msg, message_handler, trace_id)

                    # Commit offset after successful processing (exactly-once)
                    consumer.commit(asynchronous=False)

                    # Log successful message consumption
                    logger.debug(
                        f"Successfully consumed and processed message: topic={msg.topic()}, "
                        f"partition={msg.partition()}, offset={msg.offset()}"
                    )



                except KafkaErrorException as e:
                    # Handle processing errors gracefully - log and continue
                    logger.warning(
                        f"Skipping message with processing error: {e}",
                        extra={"trace_id": trace_id},
                    )
                    # Commit offset to skip this message and continue
                    consumer.commit(asynchronous=False)
                    continue

        except KeyboardInterrupt:
            logger.info("Received interrupt signal, stopping consumer")
            self._running = False
        except Exception as e:
            logger.error(f"Fatal error during message consumption: {e}", exc_info=True)
            self._running = False
            raise KafkaErrorException(
                f"Fatal error during message consumption: {e}",
                operation="consume",
                trace_id=trace_id,
            ) from e

    async def _process_message(
        self,
        msg,
        message_handler: Callable,
        trace_id: str | None = None,
    ) -> None:
        """
        Process a single Kafka message.

        Args:
            msg: Kafka message
            message_handler: Async callback function to handle message
            trace_id: Optional trace ID for distributed tracing
        """
        topic = msg.topic()
        partition = msg.partition()
        offset = msg.offset()

        with trace_span(
            "kafka_process_message",
            attributes={
                "topic": topic,
                "partition": partition,
                "offset": offset,
                "trace_id": trace_id,
            },
        ):
            try:
                # Deserialize message value using new Avro API
                if self._deserializer is None:
                    raise KafkaErrorException(
                        "Avro deserializer not initialized",
                        operation="deserialize",
                        trace_id=trace_id,
                    )

                # Deserialize the message value
                message_value = self._deserializer(
                    msg.value(),
                    SerializationContext(topic, MessageField.VALUE)
                )

                logger.debug(
                    f"Received message: topic={topic}, partition={partition}, " f"offset={offset}",
                    extra={"trace_id": trace_id},
                )

                # Call message handler
                await message_handler(message_value, topic)

                # Record metrics
                kafka_messages_consumed_total.labels(
                    topic=topic,
                    consumer_group=self.config.consumer_group_id,
                ).inc()

            except Exception as e:
                logger.error(
                    f"Failed to process message: topic={topic}, "
                    f"partition={partition}, offset={offset}, error={e}",
                    exc_info=True,
                    extra={"trace_id": trace_id},
                )
                kafka_errors_total.labels(
                    topic=topic,
                    operation="process",
                    error_type=type(e).__name__,
                ).inc()
                raise

    async def get_consumer_lag(self) -> dict[str, dict[int, int]]:
        """
        Get consumer lag for all subscribed topics.

        Returns:
            Dictionary mapping topic to partition lag
            Example: {"semantic_groups": {0: 100, 1: 50}}
        """
        consumer = self._ensure_connected()

        try:
            # Get assigned partitions
            assignment = consumer.assignment()

            if not assignment:
                return {}

            lag_info: dict[str, dict[int, int]] = {}

            for topic_partition in assignment:
                topic = topic_partition.topic
                partition = topic_partition.partition

                # Get committed offset
                committed = consumer.committed([topic_partition])[0]
                committed_offset = committed.offset if committed else 0

                # Get high watermark (latest offset)
                low, high = consumer.get_watermark_offsets(topic_partition)

                # Calculate lag
                lag = high - committed_offset

                if topic not in lag_info:
                    lag_info[topic] = {}
                lag_info[topic][partition] = lag

                # Update metrics
                kafka_consumer_lag.labels(
                    topic=topic,
                    partition=str(partition),
                    consumer_group=self.config.consumer_group_id,
                ).set(lag)

            return lag_info

        except Exception as e:
            logger.warning(f"Failed to get consumer lag: {e}")
            return {}

    async def stop(self) -> None:
        """Stop consuming messages gracefully."""
        logger.info("Stopping message consumption")
        self._running = False

    async def health_check(self) -> bool:
        """
        Check if Kafka consumer is healthy.

        Returns:
            True if healthy, False otherwise
        """
        try:
            consumer = self._ensure_connected()
            # Check if consumer has assignment
            assignment = consumer.assignment()
            return assignment is not None
        except Exception as e:
            logger.warning(f"Kafka consumer health check failed: {e}")
            return False
