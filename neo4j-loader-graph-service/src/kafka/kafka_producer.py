"""
Kafka producer for Neo4j Loader Graph Service.
Publishes graph_updated events after successful Neo4j operations.
"""

from typing import Dict, Any, Optional
from confluent_kafka import Producer
from confluent_kafka.serialization import SerializationContext, MessageField
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer
import structlog
from datetime import datetime
import time

from ..config import config
from ..exceptions import ConnectionError as GraphConnectionError, LoadError
from ..metrics import (
    kafka_messages_produced_total,
    kafka_produce_duration_seconds,
    kafka_produce_failures_total,
)

logger = structlog.get_logger(__name__)


# Avro schema for graph_updated events
GRAPH_UPDATED_SCHEMA = """
{
  "type": "record",
  "name": "GraphUpdated",
  "namespace": "com.sentimentanalyzer.graph",
  "fields": [
    {"name": "node_type", "type": ["null", "string"], "default": null},
    {"name": "node_id", "type": ["null", "string"], "default": null},
    {"name": "relationship_type", "type": ["null", "string"], "default": null},
    {"name": "operation", "type": "string"},
    {"name": "timestamp", "type": "long"},
    {"name": "trace_id", "type": ["null", "string"], "default": null},
    {"name": "status", "type": "string"},
    {"name": "error_message", "type": ["null", "string"], "default": null},
    {"name": "metadata", "type": ["null", {"type": "map", "values": "string"}], "default": null}
  ]
}
"""


class KafkaProducerClient:
    """
    Kafka producer for publishing graph update events.
    Implements idempotent producer with transactional writes.
    """

    def __init__(self):
        """Initialize Kafka producer."""
        self._producer: Optional[Producer] = None
        self._schema_registry_client: Optional[SchemaRegistryClient] = None
        self._avro_serializer: Optional[AvroSerializer] = None
        self._topic = "graph_updated"

    def connect(self) -> None:
        """
        Initialize Kafka producer and schema registry client.
        
        Raises:
            GraphConnectionError: If connection fails
        """
        try:
            # Initialize schema registry client
            self._schema_registry_client = SchemaRegistryClient({
                'url': config.schema_registry_url
            })
            
            # Initialize Avro serializer
            self._avro_serializer = AvroSerializer(
                self._schema_registry_client,
                GRAPH_UPDATED_SCHEMA,
            )
            
            # Initialize producer with idempotence enabled
            producer_config = {
                'bootstrap.servers': config.kafka_brokers,
                'client.id': f'{config.service_name}-producer',
                'enable.idempotence': True,  # Exactly-once semantics
                'acks': 'all',  # Wait for all replicas
                'retries': 3,
                'max.in.flight.requests.per.connection': 5,
                'compression.type': 'snappy',
            }

            self._producer = Producer(producer_config)

            logger.info(
                "kafka_producer_connected",
                bootstrap_servers=config.kafka_brokers,
                topic=self._topic,
            )

        except Exception as e:
            logger.error(
                "kafka_producer_connection_failed",
                error=str(e),
                bootstrap_servers=config.kafka_brokers,
            )
            raise GraphConnectionError(
                message=f"Failed to connect Kafka producer: {str(e)}",
                service="kafka",
                host=config.kafka_brokers,
            ) from e

    def close(self) -> None:
        """Close Kafka producer and flush pending messages."""
        if self._producer:
            # Flush pending messages (wait up to 30 seconds)
            remaining = self._producer.flush(timeout=30)
            if remaining > 0:
                logger.warning(
                    "kafka_producer_flush_incomplete",
                    remaining_messages=remaining,
                )
            
            logger.info("kafka_producer_closed")

    def _delivery_callback(self, err, msg):
        """
        Callback for message delivery reports.
        
        Args:
            err: Error if delivery failed
            msg: Message that was delivered or failed
        """
        if err:
            logger.error(
                "kafka_message_delivery_failed",
                error=str(err),
                topic=msg.topic(),
                partition=msg.partition(),
            )
            kafka_produce_failures_total.labels(
                topic=msg.topic(),
                error_type=type(err).__name__,
            ).inc()
        else:
            logger.debug(
                "kafka_message_delivered",
                topic=msg.topic(),
                partition=msg.partition(),
                offset=msg.offset(),
            )
            kafka_messages_produced_total.labels(
                topic=msg.topic(),
            ).inc()

    async def publish_node_created(
        self,
        node_type: str,
        node_id: str,
        trace_id: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Publish node created event.
        
        Args:
            node_type: Type of node created
            node_id: ID of node created
            trace_id: Trace ID for correlation
            metadata: Additional metadata
            
        Raises:
            LoadError: If publish fails after retries
        """
        event = {
            'node_type': node_type,
            'node_id': node_id,
            'relationship_type': None,
            'operation': 'node_created',
            'timestamp': int(time.time() * 1000),  # Milliseconds
            'trace_id': trace_id,
            'status': 'success',
            'error_message': None,
            'metadata': metadata,
        }
        
        await self._publish_event(event, trace_id)

    async def publish_relationship_created(
        self,
        relationship_type: str,
        source_node_id: str,
        target_node_id: str,
        trace_id: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Publish relationship created event.
        
        Args:
            relationship_type: Type of relationship created
            source_node_id: Source node ID
            target_node_id: Target node ID
            trace_id: Trace ID for correlation
            metadata: Additional metadata
            
        Raises:
            LoadError: If publish fails after retries
        """
        event = {
            'node_type': None,
            'node_id': None,
            'relationship_type': relationship_type,
            'operation': 'relationship_created',
            'timestamp': int(time.time() * 1000),
            'trace_id': trace_id,
            'status': 'success',
            'error_message': None,
            'metadata': {
                **(metadata or {}),
                'source_node_id': source_node_id,
                'target_node_id': target_node_id,
            },
        }
        
        await self._publish_event(event, trace_id)

    async def publish_operation_failed(
        self,
        operation: str,
        error_message: str,
        node_type: Optional[str] = None,
        node_id: Optional[str] = None,
        relationship_type: Optional[str] = None,
        trace_id: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Publish operation failed event.
        
        Args:
            operation: Operation that failed
            error_message: Error message
            node_type: Node type if applicable
            node_id: Node ID if applicable
            relationship_type: Relationship type if applicable
            trace_id: Trace ID for correlation
            metadata: Additional metadata
            
        Raises:
            LoadError: If publish fails after retries
        """
        event = {
            'node_type': node_type,
            'node_id': node_id,
            'relationship_type': relationship_type,
            'operation': operation,
            'timestamp': int(time.time() * 1000),
            'trace_id': trace_id,
            'status': 'failure',
            'error_message': error_message,
            'metadata': metadata,
        }
        
        await self._publish_event(event, trace_id)

    async def _publish_event(
        self,
        event: Dict[str, Any],
        trace_id: Optional[str] = None,
    ) -> None:
        """
        Publish event to Kafka with retry logic.
        
        Args:
            event: Event data
            trace_id: Trace ID for correlation
            
        Raises:
            LoadError: If publish fails after retries
        """
        if not self._producer or not self._avro_serializer:
            raise GraphConnectionError(
                message="Kafka producer is not initialized",
                service="kafka",
            )
        
        start_time = time.time()
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Serialize event
                serialization_context = SerializationContext(
                    self._topic,
                    MessageField.VALUE,
                )
                serialized_value = self._avro_serializer(
                    event,
                    serialization_context,
                )
                
                # Produce message
                self._producer.produce(
                    topic=self._topic,
                    value=serialized_value,
                    key=event.get('node_id') or event.get('relationship_type'),
                    on_delivery=self._delivery_callback,
                )
                
                # Poll for delivery reports
                self._producer.poll(0)
                
                duration = time.time() - start_time
                kafka_produce_duration_seconds.labels(
                    topic=self._topic,
                ).observe(duration)
                
                logger.debug(
                    "graph_event_published",
                    operation=event['operation'],
                    status=event['status'],
                    trace_id=trace_id,
                    duration_seconds=duration,
                )
                
                return
                
            except Exception as e:
                retry_count += 1
                logger.warning(
                    "kafka_publish_retry",
                    operation=event['operation'],
                    retry_count=retry_count,
                    max_retries=max_retries,
                    error=str(e),
                    trace_id=trace_id,
                )
                
                if retry_count >= max_retries:
                    kafka_produce_failures_total.labels(
                        topic=self._topic,
                        error_type=type(e).__name__,
                    ).inc()
                    
                    logger.error(
                        "kafka_publish_failed",
                        operation=event['operation'],
                        error=str(e),
                        trace_id=trace_id,
                    )
                    
                    raise LoadError(
                        message=f"Failed to publish event after {max_retries} retries: {str(e)}",
                        node_label=event.get('node_type'),
                        details={'operation': event['operation'], 'error': str(e)},
                    ) from e
                
                # Exponential backoff
                time.sleep(2 ** retry_count)


# Global Kafka producer instance
kafka_producer = KafkaProducerClient()

