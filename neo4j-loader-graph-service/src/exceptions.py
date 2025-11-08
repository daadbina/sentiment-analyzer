"""
Exception hierarchy for Neo4j Loader Graph Service.
All custom exceptions inherit from GraphError base class.
"""

from typing import Optional, Dict, Any


class GraphError(Exception):
    """
    Base exception for all graph-related errors.
    All custom exceptions should inherit from this class.
    """

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
    ):
        """
        Initialize GraphError.

        Args:
            message: Error message
            details: Additional error details
            trace_id: Trace ID for correlation
        """
        self.message = message
        self.details = details or {}
        self.trace_id = trace_id
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
            "trace_id": self.trace_id,
        }


class LoadError(GraphError):
    """
    Exception raised during graph loading operations.
    Used for batch and stream loading failures.
    """

    def __init__(
        self,
        message: str,
        node_id: Optional[str] = None,
        batch_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
    ):
        """
        Initialize LoadError.

        Args:
            message: Error message
            node_id: Node ID that failed to load
            batch_id: Batch ID for batch operations
            details: Additional error details
            trace_id: Trace ID for correlation
        """
        self.node_id = node_id
        self.batch_id = batch_id
        details = details or {}
        if node_id:
            details["node_id"] = node_id
        if batch_id:
            details["batch_id"] = batch_id
        super().__init__(message, details, trace_id)


class ValidationError(GraphError):
    """
    Exception raised during graph validation.
    Used for schema validation, constraint violations, and integrity checks.
    """

    def __init__(
        self,
        message: str,
        validation_type: Optional[str] = None,
        failed_constraints: Optional[list] = None,
        details: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
    ):
        """
        Initialize ValidationError.

        Args:
            message: Error message
            validation_type: Type of validation that failed
            failed_constraints: List of failed constraints
            details: Additional error details
            trace_id: Trace ID for correlation
        """
        self.validation_type = validation_type
        self.failed_constraints = failed_constraints or []
        details = details or {}
        if validation_type:
            details["validation_type"] = validation_type
        if failed_constraints:
            details["failed_constraints"] = failed_constraints
        super().__init__(message, details, trace_id)


class QueryError(GraphError):
    """
    Exception raised during Cypher query execution.
    Used for query syntax errors, execution failures, and timeout errors.
    """

    def __init__(
        self,
        message: str,
        query: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        details: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
    ):
        """
        Initialize QueryError.

        Args:
            message: Error message
            query: Cypher query that failed
            parameters: Query parameters
            details: Additional error details
            trace_id: Trace ID for correlation
        """
        self.query = query
        self.parameters = parameters
        details = details or {}
        if query:
            details["query"] = query
        if parameters:
            details["parameters"] = parameters
        super().__init__(message, details, trace_id)


class SchemaError(GraphError):
    """
    Exception raised during schema operations.
    Used for schema creation, modification, and constraint failures.
    """

    def __init__(
        self,
        message: str,
        schema_type: Optional[str] = None,
        operation: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
    ):
        """
        Initialize SchemaError.

        Args:
            message: Error message
            schema_type: Type of schema (node, relationship, constraint, index)
            operation: Schema operation (create, drop, modify)
            details: Additional error details
            trace_id: Trace ID for correlation
        """
        self.schema_type = schema_type
        self.operation = operation
        details = details or {}
        if schema_type:
            details["schema_type"] = schema_type
        if operation:
            details["operation"] = operation
        super().__init__(message, details, trace_id)


class ConflictError(GraphError):
    """
    Exception raised during conflict resolution.
    Used for concurrent update conflicts and duplicate detection.
    """

    def __init__(
        self,
        message: str,
        node_id: Optional[str] = None,
        conflict_type: Optional[str] = None,
        existing_value: Optional[Any] = None,
        new_value: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
    ):
        """
        Initialize ConflictError.

        Args:
            message: Error message
            node_id: Node ID with conflict
            conflict_type: Type of conflict (duplicate, concurrent_update)
            existing_value: Existing value in database
            new_value: New value attempting to write
            details: Additional error details
            trace_id: Trace ID for correlation
        """
        self.node_id = node_id
        self.conflict_type = conflict_type
        self.existing_value = existing_value
        self.new_value = new_value
        details = details or {}
        if node_id:
            details["node_id"] = node_id
        if conflict_type:
            details["conflict_type"] = conflict_type
        if existing_value is not None:
            details["existing_value"] = str(existing_value)
        if new_value is not None:
            details["new_value"] = str(new_value)
        super().__init__(message, details, trace_id)


class ConnectionError(GraphError):
    """
    Exception raised during connection failures.
    Used for Neo4j, PostgreSQL, Kafka, and Redis connection errors.
    """

    def __init__(
        self,
        message: str,
        service: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
    ):
        """
        Initialize ConnectionError.

        Args:
            message: Error message
            service: Service name (neo4j, postgres, kafka, redis)
            host: Service host
            port: Service port
            details: Additional error details
            trace_id: Trace ID for correlation
        """
        self.service = service
        self.host = host
        self.port = port
        details = details or {}
        if service:
            details["service"] = service
        if host:
            details["host"] = host
        if port:
            details["port"] = port
        super().__init__(message, details, trace_id)


class MetricsError(GraphError):
    """
    Exception raised during metrics computation.
    Used for centrality, clustering, and graph metrics failures.
    """

    def __init__(
        self,
        message: str,
        metric_type: Optional[str] = None,
        computation_stage: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
    ):
        """
        Initialize MetricsError.

        Args:
            message: Error message
            metric_type: Type of metric (centrality, clustering, graph_metrics)
            computation_stage: Stage of computation that failed
            details: Additional error details
            trace_id: Trace ID for correlation
        """
        self.metric_type = metric_type
        self.computation_stage = computation_stage
        details = details or {}
        if metric_type:
            details["metric_type"] = metric_type
        if computation_stage:
            details["computation_stage"] = computation_stage
        super().__init__(message, details, trace_id)


class SnapshotError(GraphError):
    """
    Exception raised during snapshot operations.
    Used for snapshot creation, validation, and restore failures.
    """

    def __init__(
        self,
        message: str,
        snapshot_id: Optional[str] = None,
        operation: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
    ):
        """
        Initialize SnapshotError.

        Args:
            message: Error message
            snapshot_id: Snapshot identifier
            operation: Snapshot operation (create, validate, restore)
            details: Additional error details
            trace_id: Trace ID for correlation
        """
        self.snapshot_id = snapshot_id
        self.operation = operation
        details = details or {}
        if snapshot_id:
            details["snapshot_id"] = snapshot_id
        if operation:
            details["operation"] = operation
        super().__init__(message, details, trace_id)


class CircuitBreakerError(GraphError):
    """
    Exception raised when circuit breaker is open.
    Used to prevent cascading failures.
    """

    def __init__(
        self,
        message: str,
        service: Optional[str] = None,
        failure_count: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
    ):
        """
        Initialize CircuitBreakerError.

        Args:
            message: Error message
            service: Service with open circuit breaker
            failure_count: Number of consecutive failures
            details: Additional error details
            trace_id: Trace ID for correlation
        """
        self.service = service
        self.failure_count = failure_count
        details = details or {}
        if service:
            details["service"] = service
        if failure_count is not None:
            details["failure_count"] = failure_count
        super().__init__(message, details, trace_id)


class AnalyticsError(GraphError):
    """
    Exception raised during analytics operations.
    Used for centrality, clustering, and graph analytics failures.
    """

    def __init__(
        self,
        message: str,
        analytics_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
    ):
        """
        Initialize AnalyticsError.

        Args:
            message: Error message
            analytics_type: Type of analytics (centrality, clustering, metrics)
            details: Additional error details
            trace_id: Trace ID for correlation
        """
        self.analytics_type = analytics_type
        details = details or {}
        if analytics_type:
            details["analytics_type"] = analytics_type
        super().__init__(message, details, trace_id)


class BackupError(GraphError):
    """
    Exception raised during backup operations.
    Used for backup creation, restore, and management failures.
    """

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
    ):
        """
        Initialize BackupError.

        Args:
            message: Error message
            details: Additional error details
            trace_id: Trace ID for correlation
        """
        super().__init__(message, details, trace_id)

