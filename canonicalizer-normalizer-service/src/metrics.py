"""Prometheus metrics for canonicalizer-normalizer service."""

from prometheus_client import Counter, Histogram, Gauge

# Message processing metrics
messages_processed = Counter(
    "canonicalizer_messages_processed_total",
    "Total messages processed",
    ["status"],
)

messages_published = Counter(
    "canonicalizer_messages_published_total",
    "Total messages published",
    ["topic"],
)

processing_duration = Histogram(
    "canonicalizer_processing_duration_seconds",
    "Message processing duration",
    ["stage"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0),
)

# Normalization metrics
normalization_score = Histogram(
    "canonicalizer_normalization_score",
    "Normalization quality score",
    buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
)

url_canonicalization_success = Counter(
    "canonicalizer_url_canonicalization_success_total",
    "Successful URL canonicalizations",
)

url_canonicalization_failures = Counter(
    "canonicalizer_url_canonicalization_failures_total",
    "Failed URL canonicalizations",
)

publisher_resolution_success = Counter(
    "canonicalizer_publisher_resolution_success_total",
    "Successful publisher resolutions",
)

publisher_resolution_failures = Counter(
    "canonicalizer_publisher_resolution_failures_total",
    "Failed publisher resolutions",
)

content_normalization_success = Counter(
    "canonicalizer_content_normalization_success_total",
    "Successful content normalizations",
)

content_normalization_failures = Counter(
    "canonicalizer_content_normalization_failures_total",
    "Failed content normalizations",
)

metadata_enrichment_success = Counter(
    "canonicalizer_metadata_enrichment_success_total",
    "Successful metadata enrichments",
)

metadata_enrichment_failures = Counter(
    "canonicalizer_metadata_enrichment_failures_total",
    "Failed metadata enrichments",
)

domain_classification_success = Counter(
    "canonicalizer_domain_classification_success_total",
    "Successful domain classifications",
)

domain_classification_failures = Counter(
    "canonicalizer_domain_classification_failures_total",
    "Failed domain classifications",
)

fuzzy_dedup_duplicates_found = Counter(
    "canonicalizer_fuzzy_dedup_duplicates_found_total",
    "Fuzzy duplicates found",
)

# Cache metrics
cache_hits = Counter(
    "canonicalizer_cache_hits_total",
    "Cache hits",
    ["cache_type"],
)

cache_misses = Counter(
    "canonicalizer_cache_misses_total",
    "Cache misses",
    ["cache_type"],
)

# Error metrics
errors_total = Counter(
    "canonicalizer_errors_total",
    "Total errors",
    ["error_type"],
)

dlq_messages = Counter(
    "canonicalizer_dlq_messages_total",
    "Messages sent to DLQ",
    ["reason"],
)

# Consumer lag
consumer_lag = Gauge(
    "canonicalizer_consumer_lag",
    "Kafka consumer lag",
)

# Batch metrics
batch_size = Histogram(
    "canonicalizer_batch_size",
    "Batch size",
    buckets=(10, 50, 100, 500, 1000),
)

batch_processing_duration = Histogram(
    "canonicalizer_batch_processing_duration_seconds",
    "Batch processing duration",
    buckets=(1, 5, 10, 30, 60),
)

