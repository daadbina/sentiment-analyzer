"""
Prometheus metrics for Neo4j Loader Graph Service.
All metrics are exposed on the configured Prometheus port.
"""

from prometheus_client import Counter, Histogram, Gauge, Info
from typing import Optional


# Service Information
service_info = Info(
    "neo4j_loader_service",
    "Neo4j Loader Graph Service information",
)

# Node Creation Metrics
graph_nodes_created_total = Counter(
    "graph_nodes_created_total",
    "Total number of nodes created in the graph",
    labelnames=["node_type"],
)

# Relationship Creation Metrics
graph_relationships_created_total = Counter(
    "graph_relationships_created_total",
    "Total number of relationships created in the graph",
    labelnames=["relationship_type"],
)

# Graph Loading Metrics
graph_load_duration_seconds = Histogram(
    "graph_load_duration_seconds",
    "Duration of graph loading operations in seconds",
    labelnames=["operation_type", "batch_size"],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0),
)

# Validation Metrics
graph_validation_failures_total = Counter(
    "graph_validation_failures_total",
    "Total number of graph validation failures",
    labelnames=["validation_type", "failure_reason"],
)

graph_validation_duration_seconds = Histogram(
    "graph_validation_duration_seconds",
    "Duration of graph validation operations in seconds",
    labelnames=["validation_type"],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
)

# Centrality Computation Metrics
graph_centrality_computation_duration_seconds = Histogram(
    "graph_centrality_computation_duration_seconds",
    "Duration of centrality computation in seconds",
    labelnames=["centrality_type"],
    buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0),
)

# Clustering Detection Metrics
graph_clustering_detection_duration_seconds = Histogram(
    "graph_clustering_detection_duration_seconds",
    "Duration of community detection in seconds",
    labelnames=["algorithm"],
    buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0, 900.0),
)

# Analytics Metrics
graph_analytics_duration_seconds = Histogram(
    "graph_analytics_duration_seconds",
    "Duration of graph analytics operations in seconds",
    labelnames=["analytics_type"],
    buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0),
)

graph_centrality_computation_total = Counter(
    "graph_centrality_computation_total",
    "Total number of centrality computations",
    labelnames=["centrality_type"],
)

graph_clustering_computation_total = Counter(
    "graph_clustering_computation_total",
    "Total number of clustering computations",
    labelnames=["algorithm"],
)

graph_analytics_nodes_processed = Counter(
    "graph_analytics_nodes_processed",
    "Total number of nodes processed in analytics",
    labelnames=["analytics_type"],
)

# Validation Orphan Metrics
graph_validation_orphans_detected_total = Counter(
    "graph_validation_orphans_detected_total",
    "Total number of orphaned nodes detected",
)

# Query Cache Metrics
graph_query_cache_hits_total = Counter(
    "graph_query_cache_hits_total",
    "Total number of query cache hits",
)

graph_query_cache_misses_total = Counter(
    "graph_query_cache_misses_total",
    "Total number of query cache misses",
)

graph_query_duration_seconds = Histogram(
    "graph_query_duration_seconds",
    "Duration of graph query execution in seconds",
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# Snapshot Metrics
graph_snapshot_duration_seconds = Histogram(
    "graph_snapshot_duration_seconds",
    "Duration of snapshot creation in seconds",
    buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0),
)

graph_snapshot_size_bytes = Gauge(
    "graph_snapshot_size_bytes",
    "Size of the latest graph snapshot in bytes",
)

graph_snapshot_node_count = Gauge(
    "graph_snapshot_node_count",
    "Number of nodes in the latest snapshot",
    labelnames=["node_type"],
)

graph_snapshot_relationship_count = Gauge(
    "graph_snapshot_relationship_count",
    "Number of relationships in the latest snapshot",
    labelnames=["relationship_type"],
)

# Query Metrics
graph_query_latency_ms = Histogram(
    "graph_query_latency_ms",
    "Cypher query latency in milliseconds",
    labelnames=["query_type"],
    buckets=(10, 50, 100, 250, 500, 1000, 2500, 5000, 10000),
)

graph_query_total = Counter(
    "graph_query_total",
    "Total number of Cypher queries executed",
    labelnames=["query_type", "status"],
)

# Write Failure Metrics
graph_write_failures_total = Counter(
    "graph_write_failures_total",
    "Total number of failed graph writes",
    labelnames=["operation_type", "failure_reason"],
)

graph_write_retries_total = Counter(
    "graph_write_retries_total",
    "Total number of write retry attempts",
    labelnames=["operation_type"],
)

# Kafka Consumer Metrics
kafka_messages_consumed_total = Counter(
    "kafka_messages_consumed_total",
    "Total number of Kafka messages consumed",
    labelnames=["topic"],
)

kafka_consumer_lag = Gauge(
    "kafka_consumer_lag",
    "Kafka consumer lag per topic partition",
    labelnames=["topic", "partition"],
)

kafka_message_processing_duration_seconds = Histogram(
    "kafka_message_processing_duration_seconds",
    "Duration of Kafka message processing in seconds",
    labelnames=["topic", "message_type"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

# Kafka Producer Metrics
kafka_messages_produced_total = Counter(
    "kafka_messages_produced_total",
    "Total number of Kafka messages produced",
    labelnames=["topic"],
)

# Neo4j Connection Metrics
neo4j_connection_pool_size = Gauge(
    "neo4j_connection_pool_size",
    "Current Neo4j connection pool size",
)

neo4j_connection_pool_in_use = Gauge(
    "neo4j_connection_pool_in_use",
    "Number of Neo4j connections currently in use",
)

neo4j_connection_errors_total = Counter(
    "neo4j_connection_errors_total",
    "Total number of Neo4j connection errors",
    labelnames=["error_type"],
)

# PostgreSQL Connection Metrics
postgres_connection_pool_size = Gauge(
    "postgres_connection_pool_size",
    "Current PostgreSQL connection pool size",
)

postgres_connection_pool_in_use = Gauge(
    "postgres_connection_pool_in_use",
    "Number of PostgreSQL connections currently in use",
)

postgres_query_duration_seconds = Histogram(
    "postgres_query_duration_seconds",
    "PostgreSQL query duration in seconds",
    labelnames=["query_type"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

# Circuit Breaker Metrics
circuit_breaker_state = Gauge(
    "circuit_breaker_state",
    "Circuit breaker state (1=active for current state)",
    labelnames=["circuit_name", "state"],
)

circuit_breaker_failures_total = Counter(
    "circuit_breaker_failures_total",
    "Total number of circuit breaker failures",
    labelnames=["circuit_name"],
)

# Rate Limiter Metrics
rate_limiter_queue_size = Gauge(
    "rate_limiter_queue_size",
    "Current size of rate limiter queue",
    labelnames=["limiter_name"],
)

rate_limiter_wait_time_seconds = Histogram(
    "rate_limiter_wait_time_seconds",
    "Time spent waiting for rate limiter tokens in seconds",
    labelnames=["limiter_name"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# Kafka Producer Metrics (additional)
kafka_produce_duration_seconds = Histogram(
    "kafka_produce_duration_seconds",
    "Duration of Kafka message production in seconds",
    labelnames=["topic"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

kafka_produce_failures_total = Counter(
    "kafka_produce_failures_total",
    "Total number of Kafka message production failures",
    labelnames=["topic", "error_type"],
)

# Batch Processing Metrics
batch_processing_size = Histogram(
    "batch_processing_size",
    "Size of batches processed",
    labelnames=["batch_type"],
    buckets=(10, 50, 100, 250, 500, 1000, 2500, 5000),
)

batch_processing_duration_seconds = Histogram(
    "batch_processing_duration_seconds",
    "Duration of batch processing in seconds",
    labelnames=["batch_type"],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
)

# Orphan Detection Metrics
graph_orphaned_nodes_total = Gauge(
    "graph_orphaned_nodes_total",
    "Total number of orphaned nodes detected",
    labelnames=["node_type"],
)

# Conflict Resolution Metrics
graph_conflicts_resolved_total = Counter(
    "graph_conflicts_resolved_total",
    "Total number of conflicts resolved",
    labelnames=["conflict_type", "resolution_strategy"],
)

# Backup Metrics
backup_duration_seconds = Histogram(
    "backup_duration_seconds",
    "Duration of backup operations in seconds",
    buckets=(10, 30, 60, 120, 300, 600, 1800, 3600),
)

backup_size_bytes = Gauge(
    "backup_size_bytes",
    "Size of the latest backup in bytes",
)

backup_success_total = Counter(
    "backup_success_total",
    "Total number of successful backups",
)

backup_failure_total = Counter(
    "backup_failure_total",
    "Total number of failed backups",
    labelnames=["failure_reason"],
)


def initialize_service_info(version: str, environment: str):
    """
    Initialize service information metrics.

    Args:
        version: Service version
        environment: Deployment environment (dev, staging, prod)
    """
    service_info.info(
        {
            "version": version,
            "environment": environment,
            "service": "neo4j-loader-graph-service",
        }
    )


def record_node_created(node_type: str):
    """Record a node creation."""
    graph_nodes_created_total.labels(node_type=node_type).inc()


def record_relationship_created(relationship_type: str):
    """Record a relationship creation."""
    graph_relationships_created_total.labels(relationship_type=relationship_type).inc()


def record_write_failure(operation_type: str, failure_reason: str):
    """Record a write failure."""
    graph_write_failures_total.labels(
        operation_type=operation_type, failure_reason=failure_reason
    ).inc()


def record_validation_failure(validation_type: str, failure_reason: str):
    """Record a validation failure."""
    graph_validation_failures_total.labels(
        validation_type=validation_type, failure_reason=failure_reason
    ).inc()


def record_kafka_message_consumed(topic: str):
    """Record a Kafka message consumption."""
    kafka_messages_consumed_total.labels(topic=topic).inc()


def record_kafka_message_produced(topic: str, status: str):
    """Record a Kafka message production."""
    kafka_messages_produced_total.labels(topic=topic, status=status).inc()


def update_consumer_lag(topic: str, partition: int, lag: int):
    """Update Kafka consumer lag."""
    kafka_consumer_lag.labels(topic=topic, partition=str(partition)).set(lag)


def record_conflict_resolved(conflict_type: str, resolution_strategy: str):
    """Record a conflict resolution."""
    graph_conflicts_resolved_total.labels(
        conflict_type=conflict_type, resolution_strategy=resolution_strategy
    ).inc()

