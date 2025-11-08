"""
Kafka producer client for publishing predictions.

Provides abstraction over confluent-kafka for producing messages with Avro serialization.
Implements exactly-once semantics and delivery guarantees.
"""

import asyncio
import logging
from typing import Any

from confluent_kafka.avro import AvroProducer
from confluent_kafka.avro.serializer import SerializerError

from ..config import KafkaConfig
from ..exceptions import KafkaError as KafkaErrorException
from ..metrics import kafka_errors_total, kafka_messages_produced_total
from ..utils.trace import trace_span

logger = logging.getLogger(__name__)


class KafkaProducerClient:
    """
    Client for producing messages to Kafka topics.

    Provides methods for publishing predictions with Avro serialization.
    Handles delivery confirmation and error recovery.
    """

    def __init__(self, config: KafkaConfig):
        """
        Initialize Kafka producer client.

        Args:
            config: Kafka configuration
        """
        self.config = config
        self._producer: AvroProducer | None = None

        logger.info(f"Initializing Kafka producer: brokers={config.brokers}")

    async def connect(self) -> None:
        """
        Connect to Kafka and create producer.

        Raises:
            KafkaErrorException: If connection fails
        """
        try:
            logger.info(f"Connecting to Kafka producer: {self.config.brokers}")

            # Build producer configuration
            producer_config = {
                "bootstrap.servers": self.config.brokers,
                "schema.registry.url": self.config.schema_registry_url,
                "acks": "all",  # Wait for all replicas
                "enable.idempotence": True,  # Exactly-once semantics
                "max.in.flight.requests.per.connection": 5,
                "retries": 10,
                "retry.backoff.ms": 100,
                "compression.type": "snappy",
            }

            # Add TLS configuration if enabled
            if self.config.enable_tls:
                producer_config.update({
                    "security.protocol": "SSL",
                    "ssl.ca.location": self.config.tls_ca_cert,
                    "ssl.certificate.location": self.config.tls_client_cert,
                    "ssl.key.location": self.config.tls_client_key,
                })

            # Create Avro producer
            self._producer = AvroProducer(
                producer_config,
                default_key_schema=None,  # No key schema
                default_value_schema=None,  # Schema provided per message
            )

            logger.info(f"Connected to Kafka producer: brokers={self.config.brokers}")
        except Exception as e:
            logger.error(f"Failed to connect to Kafka producer: {e}", exc_info=True)
            raise KafkaErrorException(
                f"Failed to connect to Kafka producer: {e}",
                operation="connect",
            )

    async def disconnect(self) -> None:
        """Disconnect from Kafka and flush pending messages."""
        if self._producer:
            logger.info("Disconnecting from Kafka producer")
            # Flush pending messages
            remaining = self._producer.flush(timeout=30)
            if remaining > 0:
                logger.warning(f"Failed to flush {remaining} messages before disconnect")
            self._producer = None

    def _ensure_connected(self) -> AvroProducer:
        """
        Ensure producer is connected.

        Returns:
            AvroProducer instance

        Raises:
            KafkaErrorException: If not connected
        """
        if self._producer is None:
            raise KafkaErrorException(
                "Kafka producer not connected. Call connect() first.",
                operation="ensure_connected",
            )
        return self._producer

    async def produce_prediction(
        self,
        prediction: dict[str, Any],
        value_schema: dict[str, Any],
        trace_id: str | None = None,
    ) -> None:
        """
        Produce prediction message to Kafka.

        Args:
            prediction: Prediction data to publish
            value_schema: Avro schema for the prediction
            trace_id: Optional trace ID for distributed tracing

        Raises:
            KafkaErrorException: If production fails

        Example:
            await producer.produce_prediction(
                prediction={
                    "group_id": "123",
                    "domain": "btc",
                    "prediction_probability": 0.75,
                    "prediction_confidence": 0.85,
                    "model_version": "v1.0",
                    "predicted_at": "2025-11-07T12:00:00Z",
                },
                value_schema=prediction_schema,
            )
        """
        producer = self._ensure_connected()
        topic = self.config.predictions_topic

        with trace_span(
            "kafka_produce_prediction",
            attributes={
                "topic": topic,
                "group_id": prediction.get("group_id"),
                "trace_id": trace_id,
            },
        ):
            try:
                # Create delivery callback
                delivery_future = asyncio.Future()

                def delivery_callback(err, msg):
                    """Callback for delivery confirmation."""
                    if err:
                        delivery_future.set_exception(
                            KafkaErrorException(
                                f"Message delivery failed: {err}",
                                topic=topic,
                                operation="produce",
                            )
                        )
                    else:
                        delivery_future.set_result(msg)

                # Produce message with Avro serialization
                producer.produce(
                    topic=topic,
                    value=prediction,
                    value_schema=value_schema,
                    callback=delivery_callback,
                )

                # Poll to trigger callbacks
                producer.poll(0)

                # Wait for delivery confirmation
                msg = await delivery_future

                # Record metrics
                kafka_messages_produced_total.labels(topic=topic).inc()

                logger.debug(
                    f"Produced prediction: topic={topic}, partition={msg.partition()}, "
                    f"offset={msg.offset()}, group_id={prediction.get('group_id')}",
                    extra={"trace_id": trace_id, "group_id": prediction.get("group_id")},
                )

            except SerializerError as e:
                logger.error(
                    f"Failed to serialize prediction: topic={topic}, error={e}",
                    exc_info=True,
                    extra={"trace_id": trace_id},
                )
                kafka_errors_total.labels(
                    topic=topic,
                    operation="serialize",
                    error_type="SerializerError",
                ).inc()
                raise KafkaErrorException(
                    f"Failed to serialize prediction: {e}",
                    topic=topic,
                    operation="serialize",
                    trace_id=trace_id,
                )
            except Exception as e:
                logger.error(
                    f"Failed to produce prediction: topic={topic}, error={e}",
                    exc_info=True,
                    extra={"trace_id": trace_id},
                )
                kafka_errors_total.labels(
                    topic=topic,
                    operation="produce",
                    error_type=type(e).__name__,
                ).inc()
                raise KafkaErrorException(
                    f"Failed to produce prediction: {e}",
                    topic=topic,
                    operation="produce",
                    trace_id=trace_id,
                )

    async def flush(self, timeout: float = 10.0) -> int:
        """
        Flush pending messages.

        Args:
            timeout: Timeout in seconds

        Returns:
            Number of messages still pending after timeout
        """
        producer = self._ensure_connected()

        try:
            logger.debug(f"Flushing pending messages: timeout={timeout}s")

            # Flush in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            remaining = await loop.run_in_executor(
                None,
                producer.flush,
                timeout,
            )

            if remaining > 0:
                logger.warning(f"Failed to flush {remaining} messages within timeout")
            else:
                logger.debug("All pending messages flushed successfully")

            return remaining

        except Exception as e:
            logger.error(f"Failed to flush messages: {e}", exc_info=True)
            raise KafkaErrorException(
                f"Failed to flush messages: {e}",
                operation="flush",
            )

    async def health_check(self) -> bool:
        """
        Check if Kafka producer is healthy.

        Returns:
            True if healthy, False otherwise
        """
        try:
            self._ensure_connected()
            # Producer is healthy if it's connected
            return True
        except Exception as e:
            logger.warning(f"Kafka producer health check failed: {e}")
            return False


# Avro schema for predictions topic
PREDICTION_SCHEMA = {
    "type": "record",
    "name": "Prediction",
    "namespace": "com.sentimentanalyzer.predictor",
    "fields": [
        {"name": "group_id", "type": "string"},
        {"name": "domain", "type": "string"},
        {"name": "prediction_probability", "type": "double"},
        {"name": "prediction_confidence", "type": "double"},
        {"name": "model_version", "type": "string"},
        {"name": "predicted_at", "type": "string"},
        {"name": "trace_id", "type": ["null", "string"], "default": None},
        {
            "name": "features",
            "type": {
                "type": "map",
                "values": ["null", "double", "string", "long"],
            },
        },
    ],
}

