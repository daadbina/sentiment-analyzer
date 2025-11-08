"""Kafka consumer for entities_extracted topic."""

import logging
import json
import redis
from typing import Dict, List, Optional
from confluent_kafka import Consumer, KafkaError
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroDeserializer
from confluent_kafka.serialization import StringDeserializer

logger = logging.getLogger(__name__)


class EntitiesConsumer:
    """Consumes entities from entities_extracted topic and caches them by article_id."""

    def __init__(self, brokers: str = "154.53.166.231:9092",
                 schema_registry_url: str = "http://154.53.166.231:8081",
                 redis_host: str = "localhost",
                 redis_port: int = 6379):
        """Initialize entities consumer.

        Args:
            brokers: Kafka bootstrap servers
            schema_registry_url: Schema Registry URL
            redis_host: Redis host
            redis_port: Redis port
        """
        self.brokers = brokers
        self.schema_registry_url = schema_registry_url
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.consumer = None
        self.entities_cache: Dict[str, List[Dict]] = {}
        self.deserializer = None
        self.redis_client = None
        
    def initialize(self) -> None:
        """Initialize Kafka consumer and schema registry."""
        try:
            # Connect to Redis
            self.redis_client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                decode_responses=True,
                socket_connect_timeout=5,
            )
            self.redis_client.ping()
            logger.info(f"Redis connected: {self.redis_host}:{self.redis_port}")

            # Initialize schema registry
            sr_client = SchemaRegistryClient({"url": self.schema_registry_url})

            # Create Avro deserializer
            self.deserializer = AvroDeserializer(sr_client)

            # Create consumer
            consumer_config = {
                "bootstrap.servers": self.brokers,
                "group.id": "feature-engineering-entities-group",
                "auto.offset.reset": "earliest",
                "enable.auto.commit": False,
                "max.poll.interval.ms": 300000,
                "session.timeout.ms": 30000,
            }

            self.consumer = Consumer(consumer_config)
            self.consumer.subscribe(["entities_extracted"])

            logger.info(
                f"Entities consumer initialized successfully: "
                f"brokers={self.brokers}, "
                f"schema_registry={self.schema_registry_url}, "
                f"group_id=feature-engineering-entities-group"
            )

        except Exception as e:
            logger.error(f"Error initializing entities consumer: {e}", exc_info=True)
            raise
    
    def consume_batch(self, timeout_seconds: float = 1.0, max_messages: int = 100) -> int:
        """Consume a batch of entity messages and cache them.

        Args:
            timeout_seconds: Poll timeout in seconds
            max_messages: Maximum messages to consume in one batch

        Returns:
            Number of messages consumed
        """
        if not self.consumer:
            logger.warning("Consumer not initialized")
            return 0

        messages_consumed = 0
        self.poll_count = getattr(self, 'poll_count', 0) + 1

        # Log every 100 polls
        if self.poll_count % 100 == 0:
            logger.info(
                f"Entities consumer poll #{self.poll_count}: "
                f"cache_size={len(self.entities_cache)}"
            )

        try:
            for _ in range(max_messages):
                msg = self.consumer.poll(timeout_seconds)

                if msg is None:
                    break

                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    else:
                        logger.error(f"Consumer error: {msg.error()}")
                        continue

                try:
                    # Deserialize message
                    entity_msg = self.deserializer(msg.value(), None)
                    article_id = entity_msg.get("article_id")
                    entities = entity_msg.get("entities", [])

                    if article_id:
                        # Cache in memory
                        self.entities_cache[article_id] = entities

                        # Store in Redis with 24-hour TTL
                        if self.redis_client:
                            try:
                                redis_key = f"entities:{article_id}"
                                self.redis_client.setex(
                                    redis_key,
                                    86400,  # 24 hours
                                    json.dumps(entities)
                                )
                            except Exception as redis_err:
                                logger.warning(f"Failed to store entities in Redis: {redis_err}")

                        logger.info(
                            f"Cached {len(entities)} entities for article {article_id}, "
                            f"cache_size={len(self.entities_cache)}"
                        )
                        messages_consumed += 1

                    self.consumer.commit(msg)

                except Exception as e:
                    logger.error(f"Error deserializing entity message: {e}", exc_info=True)
                    continue

        except Exception as e:
            logger.error(f"Error consuming entities batch: {e}", exc_info=True)

        if messages_consumed > 0:
            logger.info(f"Consumed {messages_consumed} entity messages in batch")

        return messages_consumed
    
    def get_entities(self, article_id: str) -> List[Dict]:
        """Get cached entities for an article.

        Checks memory cache first, then Redis.

        Args:
            article_id: Article ID

        Returns:
            List of entity dictionaries
        """
        # Check memory cache first
        if article_id in self.entities_cache:
            return self.entities_cache[article_id]

        # Check Redis
        if self.redis_client:
            try:
                redis_key = f"entities:{article_id}"
                entities_json = self.redis_client.get(redis_key)
                if entities_json:
                    entities = json.loads(entities_json)
                    # Cache in memory for future lookups
                    self.entities_cache[article_id] = entities
                    return entities
            except Exception as e:
                logger.warning(f"Failed to retrieve entities from Redis: {e}")

        return []
    
    def clear_cache(self) -> None:
        """Clear the entities cache."""
        self.entities_cache.clear()
        logger.info("Entities cache cleared")
    
    def shutdown(self) -> None:
        """Shutdown the consumer."""
        if self.consumer:
            self.consumer.close()
            logger.info("Entities consumer shutdown")

        if self.redis_client:
            try:
                self.redis_client.close()
                logger.info("Redis connection closed")
            except Exception as e:
                logger.warning(f"Error closing Redis connection: {e}")

