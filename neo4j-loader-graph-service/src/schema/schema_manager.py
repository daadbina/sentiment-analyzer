"""
Schema manager for Neo4j graph database.
Manages constraints, indexes, and schema validation.
"""

from typing import List, Dict, Any
import structlog

from ..clients.neo4j_client import neo4j_client
from ..exceptions import SchemaError

logger = structlog.get_logger(__name__)


class SchemaManager:
    """
    Manages Neo4j schema including constraints and indexes.
    """

    # Node labels
    NODE_LABELS = ["Article", "Group", "Entity", "Actor", "Prediction"]

    # Relationship types
    RELATIONSHIP_TYPES = [
        "MENTIONS",
        "BELONGS_TO",
        "RELATED_TO",
        "INVOLVES",
        "PREDICTS",
        "REFERENCES",
    ]

    # Unique constraints
    UNIQUE_CONSTRAINTS = [
        ("Article", "id"),
        ("Group", "id"),
        ("Entity", "id"),
        ("Actor", "id"),
        ("Prediction", "id"),
    ]

    # Indexes
    INDEXES = [
        ("Article", "published_at"),
        ("Article", "source"),
        ("Article", "checksum"),
        ("Group", "created_at"),
        ("Entity", "name"),
        ("Entity", "type"),
        ("Actor", "name"),
        ("Actor", "type"),
        ("Prediction", "predicted_at"),
        ("Prediction", "domain"),
    ]

    def __init__(self):
        """Initialize schema manager."""
        self.client = neo4j_client

    def create_constraints(self) -> None:
        """
        Create all unique constraints.
        
        Raises:
            SchemaError: If constraint creation fails
        """
        logger.info("creating_neo4j_constraints", count=len(self.UNIQUE_CONSTRAINTS))

        for label, property_name in self.UNIQUE_CONSTRAINTS:
            try:
                constraint_name = f"unique_{label.lower()}_{property_name}"
                query = f"""
                CREATE CONSTRAINT {constraint_name} IF NOT EXISTS
                FOR (n:{label})
                REQUIRE n.{property_name} IS UNIQUE
                """
                self.client.execute_write(query)
                logger.info(
                    "constraint_created",
                    label=label,
                    property=property_name,
                    constraint_name=constraint_name,
                )
            except Exception as e:
                logger.error(
                    "constraint_creation_failed",
                    label=label,
                    property=property_name,
                    error=str(e),
                )
                raise SchemaError(
                    message=f"Failed to create constraint on {label}.{property_name}: {str(e)}",
                    schema_type="constraint",
                    operation="create",
                    details={"label": label, "property": property_name},
                ) from e

    def create_indexes(self) -> None:
        """
        Create all indexes.
        
        Raises:
            SchemaError: If index creation fails
        """
        logger.info("creating_neo4j_indexes", count=len(self.INDEXES))

        for label, property_name in self.INDEXES:
            try:
                index_name = f"idx_{label.lower()}_{property_name}"
                query = f"""
                CREATE INDEX {index_name} IF NOT EXISTS
                FOR (n:{label})
                ON (n.{property_name})
                """
                self.client.execute_write(query)
                logger.info(
                    "index_created",
                    label=label,
                    property=property_name,
                    index_name=index_name,
                )
            except Exception as e:
                logger.error(
                    "index_creation_failed",
                    label=label,
                    property=property_name,
                    error=str(e),
                )
                raise SchemaError(
                    message=f"Failed to create index on {label}.{property_name}: {str(e)}",
                    schema_type="index",
                    operation="create",
                    details={"label": label, "property": property_name},
                ) from e

    def initialize_schema(self) -> None:
        """
        Initialize complete schema (constraints + indexes).
        
        Raises:
            SchemaError: If schema initialization fails
        """
        logger.info("initializing_neo4j_schema")
        try:
            self.create_constraints()
            self.create_indexes()
            logger.info("neo4j_schema_initialized")
        except Exception as e:
            logger.error("schema_initialization_failed", error=str(e))
            raise SchemaError(
                message=f"Schema initialization failed: {str(e)}",
                schema_type="full_schema",
                operation="initialize",
            ) from e

    def get_constraints(self) -> List[Dict[str, Any]]:
        """
        Get all existing constraints.
        
        Returns:
            List of constraint dictionaries
        """
        query = "SHOW CONSTRAINTS"
        try:
            results = self.client.execute_query(query)
            logger.debug("constraints_retrieved", count=len(results))
            return results
        except Exception as e:
            logger.error("get_constraints_failed", error=str(e))
            return []

    def get_indexes(self) -> List[Dict[str, Any]]:
        """
        Get all existing indexes.
        
        Returns:
            List of index dictionaries
        """
        query = "SHOW INDEXES"
        try:
            results = self.client.execute_query(query)
            logger.debug("indexes_retrieved", count=len(results))
            return results
        except Exception as e:
            logger.error("get_indexes_failed", error=str(e))
            return []

    def validate_schema(self) -> bool:
        """
        Validate that all required constraints and indexes exist.
        
        Returns:
            True if schema is valid, False otherwise
        """
        logger.info("validating_neo4j_schema")

        # Check constraints
        existing_constraints = self.get_constraints()
        constraint_names = {
            f"unique_{label.lower()}_{prop}"
            for label, prop in self.UNIQUE_CONSTRAINTS
        }
        existing_constraint_names = {c.get("name") for c in existing_constraints}

        missing_constraints = constraint_names - existing_constraint_names
        if missing_constraints:
            logger.warning(
                "missing_constraints",
                missing=list(missing_constraints),
            )
            return False

        # Check indexes
        existing_indexes = self.get_indexes()
        index_names = {
            f"idx_{label.lower()}_{prop}" for label, prop in self.INDEXES
        }
        existing_index_names = {i.get("name") for i in existing_indexes}

        missing_indexes = index_names - existing_index_names
        if missing_indexes:
            logger.warning(
                "missing_indexes",
                missing=list(missing_indexes),
            )
            return False

        logger.info("neo4j_schema_valid")
        return True

    def drop_all_constraints(self) -> None:
        """
        Drop all constraints (use with caution).
        
        Raises:
            SchemaError: If constraint drop fails
        """
        logger.warning("dropping_all_constraints")
        constraints = self.get_constraints()

        for constraint in constraints:
            constraint_name = constraint.get("name")
            if constraint_name:
                try:
                    query = f"DROP CONSTRAINT {constraint_name} IF EXISTS"
                    self.client.execute_write(query)
                    logger.info("constraint_dropped", name=constraint_name)
                except Exception as e:
                    logger.error(
                        "constraint_drop_failed",
                        name=constraint_name,
                        error=str(e),
                    )
                    raise SchemaError(
                        message=f"Failed to drop constraint {constraint_name}: {str(e)}",
                        schema_type="constraint",
                        operation="drop",
                        details={"constraint_name": constraint_name},
                    ) from e

    def drop_all_indexes(self) -> None:
        """
        Drop all indexes (use with caution).
        
        Raises:
            SchemaError: If index drop fails
        """
        logger.warning("dropping_all_indexes")
        indexes = self.get_indexes()

        for index in indexes:
            index_name = index.get("name")
            if index_name and not index_name.startswith("constraint_"):
                try:
                    query = f"DROP INDEX {index_name} IF EXISTS"
                    self.client.execute_write(query)
                    logger.info("index_dropped", name=index_name)
                except Exception as e:
                    logger.error(
                        "index_drop_failed",
                        name=index_name,
                        error=str(e),
                    )
                    raise SchemaError(
                        message=f"Failed to drop index {index_name}: {str(e)}",
                        schema_type="index",
                        operation="drop",
                        details={"index_name": index_name},
                    ) from e


# Global schema manager instance
schema_manager = SchemaManager()

