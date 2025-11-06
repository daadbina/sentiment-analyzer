"""Kafka consumer for semantic groups."""

import json
from typing import List, Dict, Any, Optional
from confluent_kafka import Consumer, KafkaError
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroDeserializer
from confluent_kafka.schema_registry.error import SchemaRegistryError

from src.config import config
from src.utils.trace import get_logger
from src.clients.circuit_breaker import CircuitBreaker, ExponentialBackoff

logger = get_logger(__name__, config.logging.log_level)


class SemanticGroupConsumer:
    """Consume semantic groups from Kafka."""

    def __init__(self):
        """Initialize consumer."""
        self.config = config
        self.consumer: Optional[Consumer] = None
        self.topic = config.kafka.semantic_groups_topic
        self.schema_registry_client: Optional[SchemaRegistryClient] = None
        self.avro_deserializer: Optional[AvroDeserializer] = None
        self.semantic_groups: List[Dict[str, Any]] = []

        # Initialize circuit breaker for resilience
        self.circuit_breaker = CircuitBreaker(
            name="semantic_group_consumer",
            failure_threshold=5,
            recovery_timeout_seconds=60
        )

        # Initialize exponential backoff for retries
        self.backoff = ExponentialBackoff(
            initial_delay_ms=100,
            max_delay_ms=30000,
            multiplier=2.0,
            jitter=True
        )

    async def connect(self) -> bool:
        """Connect to Kafka.

        Returns:
            True if connection successful
        """
        try:
            # Initialize schema registry client
            self.schema_registry_client = SchemaRegistryClient(
                {"url": self.config.kafka.schema_registry_url}
            )

            # Initialize Avro deserializer
            self.avro_deserializer = AvroDeserializer(self.schema_registry_client)

            consumer_config = {
                "bootstrap.servers": self.config.kafka.brokers,
                "group.id": self.config.kafka.consumer_group,
                "auto.offset.reset": "earliest",
                "enable.auto.commit": self.config.kafka.consumer_auto_commit_enabled,
                "auto.commit.interval.ms": self.config.kafka.consumer_auto_commit_interval_ms,
                "isolation.level": "read_committed",  # Exactly-once semantics
                "max.poll.interval.ms": self.config.kafka.max_poll_interval_ms,  # Allow long processing
            }

            self.consumer = Consumer(consumer_config)
            self.consumer.subscribe([self.topic])

            # Wait for partition assignment
            logger.debug(
                "Waiting for partition assignment",
                operation="connect"
            )
            import time
            time.sleep(self.config.kafka.consumer_partition_wait_ms / 1000.0)

            # Seek to beginning once on startup
            await self.seek_to_beginning()

            logger.info(
                "Kafka consumer connected for semantic groups",
                bootstrap_servers=self.config.kafka.brokers,
                topic=self.topic,
            )
            return True

        except SchemaRegistryError as e:
            logger.error(
                f"Schema Registry error: {str(e)}",
                operation="connect",
                error_type=type(e).__name__
            )
            self.circuit_breaker._on_failure()
            return False
        except Exception as e:
            logger.error(
                f"Failed to connect to Kafka: {str(e)}",
                operation="connect",
                error_type=type(e).__name__
            )
            return False

    async def seek_to_beginning(self):
        """Seek consumer to the beginning of all partitions."""
        try:
            if not self.consumer:
                logger.error("Consumer not connected", operation="seek_to_beginning")
                return

            # Wait for partition assignment with retries
            import time
            from confluent_kafka import TopicPartition

            max_retries = self.config.kafka.consumer_max_retries
            retry_count = 0
            partitions = []

            while retry_count < max_retries and not partitions:
                time.sleep(self.config.kafka.consumer_partition_wait_ms / 1000.0)
                partitions = self.consumer.assignment()
                retry_count += 1

                if not partitions:
                    logger.info(
                        f"Waiting for partition assignment",
                        operation="seek_to_beginning",
                        retry=retry_count,
                        max_retries=max_retries
                    )

            logger.info(
                f"Checking partitions for seek",
                operation="seek_to_beginning",
                partition_count=len(partitions) if partitions else 0,
                retries_used=retry_count
            )

            if not partitions:
                logger.info("No partitions assigned after retries", operation="seek_to_beginning")
                return

            logger.info(
                f"Seeking to beginning of {len(partitions)} partitions",
                operation="seek_to_beginning",
                partition_count=len(partitions)
            )

            # Seek to beginning for each partition
            for partition in partitions:
                tp = TopicPartition(partition.topic(), partition.partition(), 0)
                self.consumer.seek(tp)
                logger.info(
                    f"Seeked to beginning",
                    operation="seek_to_beginning",
                    topic=partition.topic(),
                    partition=partition.partition()
                )
        except Exception as e:
            logger.error(
                f"Error seeking to beginning: {str(e)}",
                operation="seek_to_beginning",
                error_type=type(e).__name__,
                exc_info=True
            )

    async def consume_batch(self, timeout_ms: int = None, max_messages: int = 1000, force_reset: bool = False) -> List[Dict[str, Any]]:
        """Consume a batch of semantic groups.

        Args:
            timeout_ms: Timeout in milliseconds per poll (uses config default if None)
            max_messages: Maximum messages to consume in one batch
            force_reset: Force seek to beginning (for recovery)

        Returns:
            List of semantic groups
        """
        if not self.consumer:
            logger.error("Consumer not connected", operation="consume_batch")
            return []

        # Use config default if timeout not specified
        if timeout_ms is None:
            timeout_ms = self.config.kafka.consumer_poll_timeout_ms

        groups = []
        messages_consumed = 0
        poll_count = 0
        consecutive_timeouts = 0
        max_consecutive_timeouts = self.config.kafka.consumer_max_consecutive_timeouts
        try:
            logger.info(
                "Starting to consume semantic groups",
                operation="consume_batch",
                timeout_ms=timeout_ms,
                max_messages=max_messages,
                force_reset=force_reset
            )

            # Force seek to beginning if requested (for recovery)
            if force_reset:
                logger.info("Force reset requested, seeking to beginning", operation="consume_batch")
                await self.seek_to_beginning()

            # Poll multiple times to get messages
            max_polls = self.config.kafka.consumer_max_polls
            while messages_consumed < max_messages and poll_count < max_polls:
                msg = self.consumer.poll(timeout_ms / 1000.0)
                poll_count += 1

                if msg is None:
                    consecutive_timeouts += 1
                    logger.info(
                        "Poll timeout reached",
                        operation="consume_batch",
                        messages_so_far=messages_consumed,
                        poll_count=poll_count,
                        consecutive_timeouts=consecutive_timeouts
                    )
                    # Break after consecutive timeouts if we have consumed some messages
                    if consecutive_timeouts >= max_consecutive_timeouts and messages_consumed > 0:
                        logger.info(
                            "Breaking consume loop after consecutive timeouts",
                            operation="consume_batch",
                            consecutive_timeouts=consecutive_timeouts,
                            messages_consumed=messages_consumed
                        )
                        break
                    continue

                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        logger.info(
                            "Reached end of partition",
                            operation="consume_batch"
                        )
                        continue
                    else:
                        logger.error(
                            f"Kafka error: {msg.error()}",
                            operation="consume_batch"
                        )
                        break

                # Reset consecutive timeouts counter when a message is received
                consecutive_timeouts = 0

                try:
                    # Deserialize Avro message
                    group_data = self.avro_deserializer(msg.value(), None)
                    groups.append(group_data)
                    messages_consumed += 1

                    # Batch commit offsets every N messages (if auto-commit disabled)
                    if not self.config.kafka.consumer_auto_commit_enabled:
                        if messages_consumed % self.config.kafka.consumer_batch_commit_interval == 0:
                            self.consumer.commit(asynchronous=False)
                            logger.debug(
                                "Committed offset batch",
                                operation="consume_batch",
                                messages_committed=messages_consumed,
                                offset=msg.offset()
                            )

                    logger.debug(
                        "Consumed semantic group",
                        operation="consume_batch",
                        group_id=group_data.get("group_id"),
                        offset=msg.offset(),
                        messages_so_far=messages_consumed
                    )

                except Exception as e:
                    logger.error(
                        f"Failed to deserialize message: {str(e)}",
                        operation="consume_batch",
                        error_type=type(e).__name__
                    )

            logger.info(
                f"Consume batch completed",
                operation="consume_batch",
                group_count=len(groups),
                poll_count=poll_count,
                max_polls=max_polls
            )

            return groups

        except Exception as e:
            logger.error(
                f"Error consuming batch: {str(e)}",
                operation="consume_batch",
                error_type=type(e).__name__,
                exc_info=True
            )
            return groups

    async def disconnect(self):
        """Disconnect from Kafka."""
        if self.consumer:
            self.consumer.close()
            logger.info("Kafka consumer disconnected", operation="disconnect")

    def get_health_status(self) -> dict:
        """Get consumer health status including circuit breaker state.

        Returns:
            Health status dictionary
        """
        return {
            "connected": self.consumer is not None,
            "topic": self.topic,
            "circuit_breaker": self.circuit_breaker.get_state()
        }

