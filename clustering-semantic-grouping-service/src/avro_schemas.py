"""Avro schema definitions and registration for Kafka topics."""

import logging
from typing import Dict, Any
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.schema_registry_client import SchemaRegistryError

logger = logging.getLogger(__name__)


# Semantic Groups Output Schema (Avro)
SEMANTIC_GROUPS_SCHEMA = {
    "type": "record",
    "name": "SemanticGroupMessage",
    "namespace": "com.sentiment_analyzer.clustering",
    "fields": [
        {"name": "group_id", "type": "string"},
        {"name": "article_ids", "type": {"type": "array", "items": "string"}},
        {"name": "article_count", "type": "int"},
        {"name": "centroid_vector", "type": {"type": "array", "items": "double"}},
        {"name": "centroid_article_id", "type": ["null", "string"], "default": None},
        {"name": "similarity_avg", "type": "double"},
        {"name": "similarity_min", "type": "double"},
        {"name": "similarity_std", "type": "double"},
        {"name": "topic_label", "type": "string"},
        {"name": "topic_label_method", "type": "string"},
        {"name": "languages", "type": {"type": "array", "items": "string"}},
        {"name": "domains", "type": {"type": "array", "items": "string"}},
        {"name": "sources", "type": {"type": "array", "items": "string"}},
        {"name": "countries", "type": {"type": "array", "items": "string"}},
        {"name": "publisher_credibility_avg", "type": "double"},
        {"name": "earliest_published_at", "type": "string"},
        {"name": "latest_published_at", "type": "string"},
        {"name": "time_span_hours", "type": "double"},
        {"name": "created_at", "type": "string"},
        {"name": "updated_at", "type": "string"},
        {"name": "clustering_algorithm", "type": "string"},
        {"name": "clustering_parameters", "type": {"type": "map", "values": "string"}},
        {"name": "embedding_model", "type": "string"},
        {"name": "embedding_version", "type": "string"},
        {"name": "parent_group_id", "type": ["null", "string"], "default": None},
        {"name": "child_group_ids", "type": {"type": "array", "items": "string"}},
        {"name": "evolution_type", "type": ["null", "string"], "default": None},
        {"name": "cluster_stability_score", "type": "double"},
        {"name": "job_id", "type": "string"},
        {"name": "trace_id", "type": "string"},
        {"name": "schema_version", "type": "string"}
    ]
}


class AvroSchemaRegistry:
    """Manages Avro schema registration and validation."""

    def __init__(self, schema_registry_url: str):
        """
        Initialize Avro schema registry.

        Args:
            schema_registry_url: Schema Registry URL
        """
        self.client = SchemaRegistryClient({"url": schema_registry_url})
        self.schema_registry_url = schema_registry_url
        logger.info(f"Initialized AvroSchemaRegistry: {schema_registry_url}")

    def register_schema(
        self,
        subject: str,
        schema: Dict[str, Any],
        schema_type: str = "AVRO"
    ) -> int:
        """
        Register a schema in Schema Registry.

        Args:
            subject: Subject name (e.g., "semantic_groups-value")
            schema: Schema definition
            schema_type: Schema type (AVRO, JSON, PROTOBUF)

        Returns:
            Schema ID
        """
        try:
            import json
            schema_str = json.dumps(schema)
            
            schema_id = self.client.register_schema(
                subject_name=subject,
                schema_str=schema_str,
                schema_type=schema_type
            )
            
            logger.info(f"Registered schema {subject}: ID={schema_id}")
            return schema_id
            
        except SchemaRegistryError as e:
            logger.error(f"Failed to register schema {subject}: {e}")
            raise

    def get_schema(self, schema_id: int) -> Dict[str, Any]:
        """
        Get schema by ID.

        Args:
            schema_id: Schema ID

        Returns:
            Schema definition
        """
        try:
            schema = self.client.get_schema(schema_id)
            logger.debug(f"Retrieved schema ID={schema_id}")
            return schema
            
        except SchemaRegistryError as e:
            logger.error(f"Failed to get schema {schema_id}: {e}")
            raise

    def validate_message(
        self,
        message: Dict[str, Any],
        schema: Dict[str, Any]
    ) -> bool:
        """
        Validate message against schema.

        Args:
            message: Message to validate
            schema: Schema definition

        Returns:
            True if valid
        """
        try:
            import jsonschema
            jsonschema.validate(instance=message, schema=schema)
            logger.debug("Message validation passed")
            return True
            
        except jsonschema.ValidationError as e:
            logger.error(f"Message validation failed: {e}")
            return False

    def ensure_schema_exists(self, subject: str, schema: Dict[str, Any]) -> int:
        """
        Ensure schema exists, register if not.

        Args:
            subject: Subject name
            schema: Schema definition

        Returns:
            Schema ID
        """
        try:
            # Try to get latest schema for subject
            schema_metadata = self.client.get_latest_schema(subject)
            logger.info(f"Schema {subject} already exists: ID={schema_metadata.schema_id}")
            return schema_metadata.schema_id
            
        except SchemaRegistryError:
            # Schema doesn't exist, register it
            logger.info(f"Schema {subject} not found, registering...")
            return self.register_schema(subject, schema)


def initialize_schemas(schema_registry_url: str) -> AvroSchemaRegistry:
    """
    Initialize and register all schemas.

    Args:
        schema_registry_url: Schema Registry URL

    Returns:
        AvroSchemaRegistry instance
    """
    registry = AvroSchemaRegistry(schema_registry_url)
    
    # Register semantic_groups schema
    registry.ensure_schema_exists(
        "semantic_groups-value",
        SEMANTIC_GROUPS_SCHEMA
    )
    
    logger.info("All schemas initialized successfully")
    return registry

