"""Kafka consumer for semantic groups."""

from confluent_kafka import Consumer, KafkaError
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroDeserializer
from confluent_kafka.serialization import SerializationContext, MessageField
from typing import Optional, Dict, Any
import json
from ..config import config
from ..utils import StructuredLogger, TraceContext
from ..exceptions import KafkaError as KafkaErrorException

logger = StructuredLogger(__name__)


class SemanticGroupConsumer:
    """Consume semantic groups from Kafka."""

    def __init__(self):
        """Initialize consumer."""
        self.config = config
        self.consumer: Optional[Consumer] = None
        self.topic = "semantic_groups"
        self.schema_registry_client: Optional[SchemaRegistryClient] = None
        self.avro_deserializer: Optional[AvroDeserializer] = None
        self._offset_reset_count = 0  # Track offset resets

    def _error_callback(self, err):
        """Handle Kafka errors.

        Args:
            err: Kafka error
        """
        error_code = err.code()
        error_str = str(err)

        # Handle offset out of range errors
        if error_code == KafkaError.OFFSET_OUT_OF_RANGE:
            self._offset_reset_count += 1
            logger.warning(
                "Kafka offset out of range - consumer will reset to earliest",
                error=error_str,
                reset_count=self._offset_reset_count,
                topic=self.topic,
                action="auto_reset_to_earliest",
            )
        # Handle other errors
        elif error_code == KafkaError._PARTITION_EOF:
            # End of partition - not an error
            logger.debug("Reached end of partition", topic=self.topic)
        elif error_code in [KafkaError._TIMED_OUT, KafkaError.REQUEST_TIMED_OUT]:
            logger.warning("Kafka request timed out", error=error_str)
        elif error_code == KafkaError._ALL_BROKERS_DOWN:
            logger.error("All Kafka brokers are down", error=error_str)
        else:
            logger.warning(
                "Kafka consumer error",
                error=error_str,
                error_code=error_code,
            )

    def connect(self) -> bool:
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
                "auto.offset.reset": self.config.kafka.auto_offset_reset,  # From config
                "enable.auto.commit": False,
                "isolation.level": "read_committed",  # Exactly-once semantics
                "session.timeout.ms": self.config.kafka.session_timeout_ms,
                "heartbeat.interval.ms": 10000,  # 10 seconds
                "max.poll.interval.ms": self.config.kafka.max_poll_interval_ms,
                # Error handling
                "error_cb": self._error_callback,
                # Logging
                "log_level": 3,  # Warning level
            }

            self.consumer = Consumer(consumer_config)
            self.consumer.subscribe([self.topic])

            logger.info(
                "Kafka consumer configuration",
                auto_offset_reset=self.config.kafka.auto_offset_reset,
                enable_auto_commit=False,
                session_timeout_ms=self.config.kafka.session_timeout_ms,
                max_poll_interval_ms=self.config.kafka.max_poll_interval_ms,
            )

            logger.info(
                "Kafka consumer connected",
                bootstrap_servers=self.config.kafka.brokers,
                topic=self.topic,
            )
            return True

        except Exception as e:
            logger.error("Failed to connect to Kafka", error=str(e), exc_info=True)
            raise KafkaErrorException(f"Failed to connect to Kafka: {str(e)}")

    def consume_message(self, timeout_ms: int = 1000) -> Optional[Dict[str, Any]]:
        """Consume a single message.

        Args:
            timeout_ms: Timeout in milliseconds

        Returns:
            Message dictionary or None if timeout
        """
        if not self.consumer:
            raise KafkaErrorException("Consumer not connected")

        try:
            msg = self.consumer.poll(timeout_ms / 1000)

            if msg is None:
                return None

            if msg.error():
                error_code = msg.error().code()

                if error_code == KafkaError._PARTITION_EOF:
                    # End of partition, not an error
                    return None
                elif error_code == KafkaError.OFFSET_OUT_OF_RANGE:
                    # Offset out of range - will be handled by auto.offset.reset
                    self._offset_reset_count += 1
                    logger.warning(
                        "Offset out of range during poll - resetting to earliest",
                        error=str(msg.error()),
                        reset_count=self._offset_reset_count,
                        partition=msg.partition(),
                        topic=msg.topic(),
                    )
                    return None
                else:
                    logger.warning(
                        "Consumer error during poll",
                        error=str(msg.error()),
                        error_code=error_code,
                    )
                    return None

            # Deserialize Avro message
            try:
                raw_value = msg.value()
                logger.debug(
                    "Raw message value",
                    length=len(raw_value) if raw_value else 0,
                    first_bytes=raw_value[:20].hex() if raw_value else None,
                )

                ctx = SerializationContext(msg.topic(), MessageField.VALUE)
                message_data = self.avro_deserializer(raw_value, ctx)

                logger.debug(
                    "Deserialized message",
                    message_type=type(message_data),
                    message_keys=list(message_data.keys()) if isinstance(message_data, dict) else None,
                )
            except Exception as e:
                logger.error(
                    "Error deserializing Avro message",
                    error=str(e),
                    exc_info=True,
                    partition=msg.partition(),
                    offset=msg.offset(),
                )
                return None

            logger.debug(
                "Message consumed",
                topic=msg.topic(),
                partition=msg.partition(),
                offset=msg.offset(),
                group_id=message_data.get("group_id") if message_data else None,
            )

            return message_data

        except Exception as e:
            logger.warning("Error consuming message", error=str(e), exc_info=True)
            return None

    def commit_offset(self) -> bool:
        """Commit current offset.

        Returns:
            True if commit successful
        """
        if not self.consumer:
            raise KafkaErrorException("Consumer not connected")

        try:
            self.consumer.commit(asynchronous=False)
            logger.info("Offset committed")
            return True
        except Exception as e:
            logger.error("Error committing offset", error=str(e), exc_info=True)
            return False

    def reset_offsets_to_beginning(self) -> bool:
        """Reset consumer offsets to beginning of topic.

        Useful for recovery scenarios when offsets are out of range.

        Returns:
            True if reset successful
        """
        if not self.consumer:
            raise KafkaErrorException("Consumer not connected")

        try:
            # Get topic partitions
            metadata = self.consumer.list_topics(self.topic, timeout=10)
            if self.topic not in metadata.topics:
                logger.error("Topic not found", topic=self.topic)
                return False

            partitions = metadata.topics[self.topic].partitions

            # Seek to beginning for each partition
            from confluent_kafka import TopicPartition, OFFSET_BEGINNING

            for partition_id in partitions.keys():
                tp = TopicPartition(self.topic, partition_id, OFFSET_BEGINNING)
                self.consumer.seek(tp)
                logger.info(
                    "Reset offset to beginning",
                    topic=self.topic,
                    partition=partition_id,
                )

            logger.info(
                "All offsets reset to beginning",
                topic=self.topic,
                partition_count=len(partitions),
            )
            return True

        except Exception as e:
            logger.error(
                "Error resetting offsets",
                error=str(e),
                exc_info=True,
            )
            return False

    def get_offset_info(self) -> Dict[str, Any]:
        """Get current offset information for debugging.

        Returns:
            Dictionary with offset information
        """
        if not self.consumer:
            return {"error": "Consumer not connected"}

        try:
            # Get assigned partitions
            assignment = self.consumer.assignment()

            if not assignment:
                return {"error": "No partitions assigned"}

            offset_info = {}
            for tp in assignment:
                # Get committed offset
                committed = self.consumer.committed([tp], timeout=5)
                committed_offset = committed[0].offset if committed else -1

                # Get current position
                position = self.consumer.position([tp])
                current_offset = position[0].offset if position else -1

                # Get watermarks (low and high)
                low, high = self.consumer.get_watermark_offsets(tp, timeout=5)

                offset_info[f"partition_{tp.partition}"] = {
                    "committed_offset": committed_offset,
                    "current_offset": current_offset,
                    "low_watermark": low,
                    "high_watermark": high,
                    "lag": high - current_offset if current_offset >= 0 else -1,
                }

            offset_info["reset_count"] = self._offset_reset_count

            logger.info("Offset information retrieved", offset_info=offset_info)
            return offset_info

        except Exception as e:
            logger.error("Error getting offset info", error=str(e), exc_info=True)
            return {"error": str(e)}

    def close(self):
        """Close consumer connection."""
        if self.consumer:
            # Log final offset info before closing
            if self._offset_reset_count > 0:
                logger.info(
                    "Consumer closing with offset resets",
                    reset_count=self._offset_reset_count,
                )

            self.consumer.close()
            logger.info("Kafka consumer closed")

