"""
Kafka consumer for Neo4j Loader Graph Service.
Consumes messages from 4 topics with Avro deserialization.
"""

from typing import Optional, Dict, Any, Callable, List
from confluent_kafka import Consumer, KafkaError, KafkaException
from confluent_kafka.avro import AvroConsumer
from confluent_kafka.avro.serializer import SerializerError
import structlog

from ..config import config
from ..exceptions import ConnectionError as GraphConnectionError
from ..metrics import (
    kafka_messages_consumed_total,
    kafka_consumer_lag,
    kafka_message_processing_duration_seconds,
)

logger = structlog.get_logger(__name__)


class KafkaConsumerClient:
    """
    Kafka consumer with Avro deserialization.
    Consumes from multiple topics with message routing.
    """

    # Topics to consume from
    TOPICS = [
        "semantic_groups",
        "entities_extracted",
        "predictions",
        "news_canonical",
    ]

    def __init__(self):
        """Initialize Kafka consumer."""
        self._consumer: Optional[AvroConsumer] = None
        self._is_running = False
        self._message_handlers: Dict[str, Callable] = {}

    def connect(self) -> None:
        """
        Establish connection to Kafka cluster.
        
        Raises:
            GraphConnectionError: If connection fails
        """
        try:
            consumer_config = config.get_kafka_consumer_config()
            
            self._consumer = AvroConsumer(consumer_config)
            
            # Subscribe to topics
            self._consumer.subscribe(self.TOPICS)
            
            logger.info(
                "kafka_consumer_connected",
                topics=self.TOPICS,
                group_id=config.consumer_group,
            )
            
        except Exception as e:
            logger.error(
                "kafka_consumer_connection_failed",
                error=str(e),
                brokers=config.kafka_brokers,
            )
            raise GraphConnectionError(
                message=f"Failed to connect to Kafka: {str(e)}",
                service="kafka",
                host=config.kafka_brokers,
            ) from e

    def close(self) -> None:
        """Close Kafka consumer and release resources."""
        if self._consumer:
            self._consumer.close()
            self._is_running = False
            logger.info("kafka_consumer_closed")

    def register_handler(self, topic: str, handler: Callable[[Dict[str, Any]], None]) -> None:
        """
        Register message handler for a topic.
        
        Args:
            topic: Topic name
            handler: Callable that processes the message
        """
        self._message_handlers[topic] = handler
        logger.info("message_handler_registered", topic=topic)

    def consume_messages(
        self,
        timeout: float = 1.0,
        max_messages: Optional[int] = None,
    ) -> None:
        """
        Consume messages from subscribed topics.
        
        Args:
            timeout: Poll timeout in seconds
            max_messages: Maximum number of messages to consume (None = infinite)
            
        Raises:
            GraphConnectionError: If consumer is not connected
        """
        if not self._consumer:
            raise GraphConnectionError(
                message="Kafka consumer is not connected",
                service="kafka",
            )

        self._is_running = True
        messages_consumed = 0

        logger.info(
            "kafka_consumer_started",
            timeout=timeout,
            max_messages=max_messages,
        )

        try:
            while self._is_running:
                if max_messages and messages_consumed >= max_messages:
                    break

                msg = self._consumer.poll(timeout=timeout)

                if msg is None:
                    continue

                if msg.error():
                    self._handle_error(msg.error())
                    continue

                # Process message
                self._process_message(msg)
                messages_consumed += 1

        except KeyboardInterrupt:
            logger.info("kafka_consumer_interrupted")
        except Exception as e:
            logger.error("kafka_consumer_error", error=str(e))
            raise
        finally:
            self._is_running = False

    def _process_message(self, msg) -> None:
        """
        Process a single Kafka message.
        
        Args:
            msg: Kafka message
        """
        import time
        start_time = time.time()
        
        topic = msg.topic()
        partition = msg.partition()
        offset = msg.offset()
        
        try:
            # Deserialize message (Avro)
            message_value = msg.value()
            message_key = msg.key()
            
            logger.debug(
                "kafka_message_received",
                topic=topic,
                partition=partition,
                offset=offset,
                key=message_key,
            )
            
            # Route to handler
            handler = self._message_handlers.get(topic)
            if handler:
                handler(message_value)
            else:
                logger.warning(
                    "no_handler_for_topic",
                    topic=topic,
                    partition=partition,
                    offset=offset,
                )
            
            # Commit offset
            self._consumer.commit(asynchronous=False)
            
            # Record metrics
            kafka_messages_consumed_total.labels(topic=topic).inc()
            duration = time.time() - start_time
            kafka_message_processing_duration_seconds.labels(
                topic=topic,
                message_type=topic,
            ).observe(duration)
            
            logger.debug(
                "kafka_message_processed",
                topic=topic,
                partition=partition,
                offset=offset,
                duration_seconds=duration,
            )
            
        except SerializerError as e:
            logger.error(
                "kafka_deserialization_error",
                topic=topic,
                partition=partition,
                offset=offset,
                error=str(e),
            )
        except Exception as e:
            logger.error(
                "kafka_message_processing_error",
                topic=topic,
                partition=partition,
                offset=offset,
                error=str(e),
            )

    def _handle_error(self, error: KafkaError) -> None:
        """
        Handle Kafka errors.
        
        Args:
            error: Kafka error
        """
        if error.code() == KafkaError._PARTITION_EOF:
            logger.debug("kafka_partition_eof", error=str(error))
        elif error.code() == KafkaError._ALL_BROKERS_DOWN:
            logger.error("kafka_all_brokers_down", error=str(error))
            self._is_running = False
        else:
            logger.error("kafka_error", error=str(error), code=error.code())

    def get_consumer_lag(self) -> Dict[str, Dict[int, int]]:
        """
        Get consumer lag for all subscribed topics.
        
        Returns:
            Dictionary mapping topic -> partition -> lag
        """
        if not self._consumer:
            return {}

        lag_info = {}
        
        try:
            # Get assigned partitions
            assignment = self._consumer.assignment()
            
            for topic_partition in assignment:
                topic = topic_partition.topic
                partition = topic_partition.partition
                
                # Get committed offset
                committed = self._consumer.committed([topic_partition])[0]
                committed_offset = committed.offset if committed else 0
                
                # Get high watermark (latest offset)
                low, high = self._consumer.get_watermark_offsets(topic_partition)
                
                # Calculate lag
                lag = high - committed_offset
                
                if topic not in lag_info:
                    lag_info[topic] = {}
                lag_info[topic][partition] = lag
                
                # Update metrics
                kafka_consumer_lag.labels(
                    topic=topic,
                    partition=partition,
                ).set(lag)
            
            logger.debug("consumer_lag_calculated", lag_info=lag_info)
            return lag_info
            
        except Exception as e:
            logger.error("get_consumer_lag_failed", error=str(e))
            return {}

    def stop(self) -> None:
        """Stop consuming messages."""
        self._is_running = False
        logger.info("kafka_consumer_stopping")


# Global Kafka consumer instance
kafka_consumer = KafkaConsumerClient()

