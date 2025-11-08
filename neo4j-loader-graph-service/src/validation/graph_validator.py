"""
Graph validation for checking integrity and constraints.
"""

from typing import Dict, Any, List, Optional
import time
import structlog

from ..clients.neo4j_client import neo4j_client
from ..exceptions import ValidationError
from ..metrics import (
    graph_validation_duration_seconds,
    graph_validation_failures_total,
)

logger = structlog.get_logger(__name__)


class GraphValidator:
    """
    Validates graph integrity and constraints.
    """

    def __init__(self):
        """Initialize graph validator."""
        self.client = neo4j_client

    def validate_node_properties(
        self,
        node_label: str,
        required_properties: List[str],
        trace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Validate that nodes have required properties.
        
        Args:
            node_label: Node label to validate
            required_properties: List of required property names
            trace_id: Trace ID for correlation
            
        Returns:
            Validation summary
        """
        start_time = time.time()
        
        try:
            # Build query to find nodes missing required properties
            property_checks = " OR ".join([
                f"n.{prop} IS NULL" for prop in required_properties
            ])
            
            query = f"""
            MATCH (n:{node_label})
            WHERE {property_checks}
            RETURN count(n) as invalid_nodes
            """
            
            result = self.client.execute_query(query, trace_id=trace_id)
            
            duration = time.time() - start_time
            invalid_nodes = result.get("invalid_nodes", 0)
            
            # Record metrics
            graph_validation_duration_seconds.labels(
                validation_type="node_properties",
                node_label=node_label,
            ).observe(duration)
            
            if invalid_nodes > 0:
                graph_validation_failures_total.labels(
                    validation_type="node_properties",
                    failure_reason="missing_properties",
                ).inc(invalid_nodes)
                
                logger.warning(
                    "node_property_validation_failed",
                    node_label=node_label,
                    invalid_nodes=invalid_nodes,
                    required_properties=required_properties,
                    trace_id=trace_id,
                )
            else:
                logger.info(
                    "node_property_validation_passed",
                    node_label=node_label,
                    trace_id=trace_id,
                )
            
            return {
                "valid": invalid_nodes == 0,
                "invalid_nodes": invalid_nodes,
                "duration_ms": duration * 1000,
            }
            
        except Exception as e:
            logger.error(
                "node_property_validation_error",
                node_label=node_label,
                error=str(e),
                trace_id=trace_id,
            )
            raise ValidationError(
                message=f"Failed to validate node properties: {str(e)}",
                validation_type="node_properties",
                details={"node_label": node_label},
                trace_id=trace_id,
            ) from e

    def detect_orphan_nodes(
        self,
        node_label: str,
        trace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Detect orphan nodes (nodes with no relationships).
        
        Args:
            node_label: Node label to check
            trace_id: Trace ID for correlation
            
        Returns:
            Detection summary
        """
        start_time = time.time()
        
        try:
            query = f"""
            MATCH (n:{node_label})
            WHERE NOT (n)--()
            RETURN count(n) as orphan_nodes, collect(n.id)[..10] as sample_ids
            """
            
            result = self.client.execute_query(query, trace_id=trace_id)
            
            duration = time.time() - start_time
            orphan_nodes = result.get("orphan_nodes", 0)
            
            # Record metrics
            graph_validation_duration_seconds.labels(
                validation_type="orphan_detection",
                node_label=node_label,
            ).observe(duration)
            
            if orphan_nodes > 0:
                graph_validation_failures_total.labels(
                    validation_type="orphan_detection",
                    failure_reason="orphan_nodes_found",
                ).inc(orphan_nodes)
                
                logger.warning(
                    "orphan_nodes_detected",
                    node_label=node_label,
                    orphan_nodes=orphan_nodes,
                    sample_ids=result.get("sample_ids", []),
                    trace_id=trace_id,
                )
            else:
                logger.info(
                    "no_orphan_nodes_detected",
                    node_label=node_label,
                    trace_id=trace_id,
                )
            
            return {
                "orphan_nodes": orphan_nodes,
                "sample_ids": result.get("sample_ids", []),
                "duration_ms": duration * 1000,
            }
            
        except Exception as e:
            logger.error(
                "orphan_detection_error",
                node_label=node_label,
                error=str(e),
                trace_id=trace_id,
            )
            raise ValidationError(
                message=f"Failed to detect orphan nodes: {str(e)}",
                validation_type="orphan_detection",
                details={"node_label": node_label},
                trace_id=trace_id,
            ) from e

    def validate_relationship_integrity(
        self,
        relationship_type: str,
        trace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Validate relationship integrity (both nodes exist).
        
        Args:
            relationship_type: Relationship type to validate
            trace_id: Trace ID for correlation
            
        Returns:
            Validation summary
        """
        start_time = time.time()
        
        try:
            # This query should not find any relationships with missing nodes
            # because Neo4j enforces referential integrity
            query = f"""
            MATCH ()-[r:{relationship_type}]->()
            RETURN count(r) as total_relationships
            """
            
            result = self.client.execute_query(query, trace_id=trace_id)
            
            duration = time.time() - start_time
            
            # Record metrics
            graph_validation_duration_seconds.labels(
                validation_type="relationship_integrity",
                node_label=relationship_type,
            ).observe(duration)
            
            logger.info(
                "relationship_integrity_validated",
                relationship_type=relationship_type,
                total_relationships=result.get("total_relationships", 0),
                trace_id=trace_id,
            )
            
            return {
                "valid": True,
                "total_relationships": result.get("total_relationships", 0),
                "duration_ms": duration * 1000,
            }
            
        except Exception as e:
            logger.error(
                "relationship_integrity_validation_error",
                relationship_type=relationship_type,
                error=str(e),
                trace_id=trace_id,
            )
            raise ValidationError(
                message=f"Failed to validate relationship integrity: {str(e)}",
                validation_type="relationship_integrity",
                details={"relationship_type": relationship_type},
                trace_id=trace_id,
            ) from e

    def validate_constraints(
        self,
        trace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Validate that all constraints are in place.
        
        Args:
            trace_id: Trace ID for correlation
            
        Returns:
            Validation summary
        """
        start_time = time.time()
        
        try:
            query = """
            SHOW CONSTRAINTS
            YIELD name, type, entityType, labelsOrTypes, properties
            RETURN name, type, entityType, labelsOrTypes, properties
            """
            
            results = self.client.execute_query(query, trace_id=trace_id)
            
            duration = time.time() - start_time
            
            # Convert to list if single result
            constraints = []
            if isinstance(results, list):
                constraints = results
            elif isinstance(results, dict):
                constraints = [results]
            
            # Expected constraints (5 unique constraints on id property)
            expected_labels = ["Article", "Group", "Entity", "Actor", "Prediction"]
            found_labels = [
                c.get("labelsOrTypes", [None])[0]
                for c in constraints
                if c.get("type") == "UNIQUENESS"
            ]
            
            missing_constraints = [
                label for label in expected_labels if label not in found_labels
            ]
            
            # Record metrics
            graph_validation_duration_seconds.labels(
                validation_type="constraints",
                node_label="all",
            ).observe(duration)
            
            if missing_constraints:
                graph_validation_failures_total.labels(
                    validation_type="constraints",
                    failure_reason="missing_constraints",
                ).inc(len(missing_constraints))
                
                logger.warning(
                    "missing_constraints_detected",
                    missing_constraints=missing_constraints,
                    trace_id=trace_id,
                )
            else:
                logger.info(
                    "all_constraints_validated",
                    constraint_count=len(constraints),
                    trace_id=trace_id,
                )
            
            return {
                "valid": len(missing_constraints) == 0,
                "total_constraints": len(constraints),
                "missing_constraints": missing_constraints,
                "duration_ms": duration * 1000,
            }
            
        except Exception as e:
            logger.error(
                "constraint_validation_error",
                error=str(e),
                trace_id=trace_id,
            )
            raise ValidationError(
                message=f"Failed to validate constraints: {str(e)}",
                validation_type="constraints",
                trace_id=trace_id,
            ) from e

    def validate_all(
        self,
        trace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Run all validation checks.
        
        Args:
            trace_id: Trace ID for correlation
            
        Returns:
            Complete validation summary
        """
        start_time = time.time()
        
        results = {}
        
        # Validate constraints
        results["constraints"] = self.validate_constraints(trace_id=trace_id)
        
        # Validate node properties for each label
        node_labels = ["Article", "Group", "Entity", "Actor", "Prediction"]
        required_properties = {
            "Article": ["id", "canonical_url", "title"],
            "Group": ["id", "topic_label"],
            "Entity": ["id", "name", "type"],
            "Actor": ["id", "name", "type"],
            "Prediction": ["id", "group_id", "probability"],
        }
        
        for label in node_labels:
            results[f"{label}_properties"] = self.validate_node_properties(
                node_label=label,
                required_properties=required_properties[label],
                trace_id=trace_id,
            )
        
        # Detect orphan nodes for each label
        for label in node_labels:
            results[f"{label}_orphans"] = self.detect_orphan_nodes(
                node_label=label,
                trace_id=trace_id,
            )
        
        # Validate relationship integrity
        relationship_types = ["MENTIONS", "BELONGS_TO", "RELATED_TO", "INVOLVES", "PREDICTS", "REFERENCES"]
        for rel_type in relationship_types:
            results[f"{rel_type}_integrity"] = self.validate_relationship_integrity(
                relationship_type=rel_type,
                trace_id=trace_id,
            )
        
        duration = time.time() - start_time
        
        # Check if all validations passed
        all_valid = all(
            result.get("valid", True) for result in results.values()
        )
        
        logger.info(
            "all_validations_completed",
            all_valid=all_valid,
            duration_seconds=duration,
            trace_id=trace_id,
        )
        
        return {
            "all_valid": all_valid,
            "results": results,
            "total_duration_ms": duration * 1000,
        }


# Global graph validator instance
graph_validator = GraphValidator()

