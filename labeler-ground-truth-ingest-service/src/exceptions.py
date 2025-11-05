"""Custom exceptions for labeler-ground-truth-ingest-service."""


class LabelError(Exception):
    """Base exception for label-related errors."""

    pass


class FetchError(LabelError):
    """Exception raised when API fetch fails."""

    def __init__(self, source: str, message: str, retry_count: int = 0):
        self.source = source
        self.message = message
        self.retry_count = retry_count
        super().__init__(f"Fetch error from {source}: {message} (retry_count={retry_count})")


class ReconciliationError(LabelError):
    """Exception raised when label reconciliation fails."""

    def __init__(self, label_id: str, group_id: str, message: str):
        self.label_id = label_id
        self.group_id = group_id
        self.message = message
        super().__init__(f"Reconciliation error for label {label_id} with group {group_id}: {message}")


class ValidationError(LabelError):
    """Exception raised when label validation fails."""

    def __init__(self, label_id: str, rule: str, message: str):
        self.label_id = label_id
        self.rule = rule
        self.message = message
        super().__init__(f"Validation error for label {label_id} (rule={rule}): {message}")


class StorageError(LabelError):
    """Exception raised when storage operation fails."""

    def __init__(self, storage_type: str, operation: str, message: str):
        self.storage_type = storage_type
        self.operation = operation
        self.message = message
        super().__init__(f"Storage error ({storage_type}.{operation}): {message}")


class LicenseError(LabelError):
    """Exception raised when license compliance check fails."""

    def __init__(self, source: str, license_type: str, message: str):
        self.source = source
        self.license_type = license_type
        self.message = message
        super().__init__(f"License error for {source} ({license_type}): {message}")


class FreshnessError(LabelError):
    """Exception raised when label freshness check fails."""

    def __init__(self, source: str, age_hours: float, threshold_hours: float):
        self.source = source
        self.age_hours = age_hours
        self.threshold_hours = threshold_hours
        super().__init__(
            f"Freshness error for {source}: age={age_hours}h exceeds threshold={threshold_hours}h"
        )


class CircuitBreakerError(LabelError):
    """Exception raised when circuit breaker is open."""

    def __init__(self, service: str, message: str):
        self.service = service
        self.message = message
        super().__init__(f"Circuit breaker open for {service}: {message}")


class SchemaRegistryError(LabelError):
    """Exception raised when schema registry operation fails."""

    def __init__(self, operation: str, schema_name: str, message: str):
        self.operation = operation
        self.schema_name = schema_name
        self.message = message
        super().__init__(f"Schema registry error ({operation} {schema_name}): {message}")


class KafkaError(LabelError):
    """Exception raised when Kafka operation fails."""

    def __init__(self, operation: str, topic: str, message: str):
        self.operation = operation
        self.topic = topic
        self.message = message
        super().__init__(f"Kafka error ({operation} on {topic}): {message}")


class DatabaseError(LabelError):
    """Exception raised when database operation fails."""

    def __init__(self, operation: str, table: str, message: str):
        self.operation = operation
        self.table = table
        self.message = message
        super().__init__(f"Database error ({operation} on {table}): {message}")

