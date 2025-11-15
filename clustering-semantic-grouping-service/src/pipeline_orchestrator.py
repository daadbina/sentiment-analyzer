"""Main clustering pipeline orchestrator."""

import hashlib
import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Tuple
import numpy as np
from uuid import uuid4

from .config import config
from .time_window_manager import TimeWindowManager
from .vector_retriever import VectorRetriever
from .clustering_engine import ClusteringEngine
from .cluster_validator import ClusterValidator
from .centroid_calculator import CentroidCalculator
from .metadata_aggregator import MetadataAggregator
from .topic_labeler import TopicLabeler
from .temporal_tracker import TemporalTracker
from .delta_lake_writer import DeltaLakeWriter
from .cluster_registry import ClusterRegistry
from .cache_manager import CacheManager
from .kafka_integration import KafkaProducer
from .kafka_entities_consumer import KafkaEntitiesConsumer
from .country_extractor import CountryExtractor
from .outlier_handler import OutlierHandler
from .incremental_clusterer import IncrementalClusterer
from .cluster_stability_scorer import ClusterStabilityScorer
from .avro_schemas import initialize_schemas
from .offset_manager import OffsetManager
from .job_manager import JobManager
from .error_handler import ErrorHandler, RetryConfig, CircuitBreaker
from .idempotency_manager import IdempotencyManager
from .tracing import create_tracing_manager

logger = logging.getLogger(__name__)


def generate_deterministic_group_id(article_ids: List[str]) -> str:
    """
    Generate deterministic group_id from article_ids.

    Same set of articles will always produce the same group_id.
    This ensures clustering idempotency and prevents duplicate semantic groups.

    Args:
        article_ids: List of article IDs in the cluster

    Returns:
        UUID string (deterministic based on article_ids)
    """
    # Sort article_ids for deterministic ordering
    sorted_ids = sorted(article_ids)

    # Create hash from sorted article_ids
    ids_str = "|".join(sorted_ids)
    hash_bytes = hashlib.sha256(ids_str.encode()).digest()

    # Convert first 16 bytes to UUID format (8-4-4-4-12 hex digits)
    hex_str = hash_bytes[:16].hex()
    uuid_str = f"{hex_str[0:8]}-{hex_str[8:12]}-{hex_str[12:16]}-{hex_str[16:20]}-{hex_str[20:32]}"

    return uuid_str


class PipelineOrchestrator:
    """Orchestrates the complete clustering pipeline."""

    def __init__(self):
        """Initialize pipeline orchestrator."""
        # Entity cache: article_id -> entities list
        # NOW BACKED BY REDIS instead of in-memory dictionary
        # Stores entity messages consumed from entities_extracted topic
        # Used for country enrichment without re-consuming messages
        # Redis cache survives service restarts and has 7-day TTL
        self.entity_cache = {}  # Kept for backward compatibility during migration

        # Background task control
        self._entities_consumer_task = None
        self._running = False
        self._poll_count = 0

        self.time_window_manager = TimeWindowManager(
            window_size_hours=config.clustering.time_window_hours,
            overlap_hours=config.clustering.overlap_hours,
        )
        self.vector_retriever = VectorRetriever(
            host=config.qdrant.host,
            port=config.qdrant.port,
            collection_name=config.qdrant.collection_name,
        )
        self.clustering_engine = ClusteringEngine(
            algorithm=config.clustering.algorithm,
            min_cluster_size=config.clustering.min_cluster_size,
            min_samples=config.clustering.min_samples,
            cluster_selection_epsilon=config.clustering.cluster_selection_epsilon,
            metric=config.clustering.metric,
        )
        self.validator = ClusterValidator(
            min_cluster_purity=config.validation.min_cluster_purity,
            min_cluster_size=config.validation.min_cluster_size,
            max_cluster_size=config.clustering.max_cluster_size,
            max_time_span_hours=config.validation.max_time_span_hours,
            min_sources=config.validation.min_sources,
        )
        self.centroid_calculator = CentroidCalculator()
        self.metadata_aggregator = MetadataAggregator()
        self.topic_labeler = TopicLabeler()
        self.temporal_tracker = TemporalTracker(
            similarity_threshold=config.clustering.similarity_threshold
        )
        self.delta_writer = DeltaLakeWriter()
        self.registry = ClusterRegistry(
            host=config.postgres.host,
            port=config.postgres.port,
            user=config.postgres.user,
            password=config.postgres.password,
            database=config.postgres.database,
        )
        self.cache = CacheManager(
            host=config.redis.host,
            port=config.redis.port,
            password=config.redis.password,
            db=config.redis.db,
            cache_ttl_seconds=config.redis.cache_ttl_seconds,
        )
        self.producer = KafkaProducer(
            brokers=config.kafka.brokers,
            schema_registry_url=config.kafka.schema_registry_url,
            topic=config.kafka.output_topic,
        )
        self.entities_consumer = KafkaEntitiesConsumer(
            brokers=config.kafka.brokers,
            schema_registry_url=config.kafka.schema_registry_url,
            topic="entities_extracted",
            consumer_group="clustering-entities-consumer-group",
        )
        self.country_extractor = CountryExtractor()
        self.outlier_handler = OutlierHandler(
            k_neighbors=config.clustering.outlier_k_neighbors,
            distance_threshold=config.clustering.outlier_distance_threshold,
            reassignment_threshold=config.clustering.similarity_threshold,
        )
        self.incremental_clusterer = IncrementalClusterer(
            similarity_threshold=config.clustering.similarity_threshold,
            max_cluster_age_hours=config.validation.max_time_span_hours,
            merge_threshold=config.clustering.incremental_merge_threshold,
        )
        self.stability_scorer = ClusterStabilityScorer(
            min_stability_score=config.clustering.stability_min_score,
            history_window_size=config.clustering.stability_history_window,
        )

        # Initialize Phase 5-8 components
        self.schema_registry = initialize_schemas(config.kafka.schema_registry_url)
        self.offset_manager = OffsetManager(
            host=config.postgres.host,
            port=config.postgres.port,
            user=config.postgres.user,
            password=config.postgres.password,
            database=config.postgres.database,
        )
        self.job_manager = JobManager(
            host=config.postgres.host,
            port=config.postgres.port,
            user=config.postgres.user,
            password=config.postgres.password,
            database=config.postgres.database,
        )
        self.error_handler = ErrorHandler(RetryConfig(max_retries=3))
        self.circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
        self.idempotency_manager = IdempotencyManager(
            postgres_host=config.postgres.host,
            postgres_port=config.postgres.port,
            postgres_user=config.postgres.user,
            postgres_password=config.postgres.password,
            postgres_db=config.postgres.database,
            redis_host=config.redis.host,
            redis_port=config.redis.port,
            redis_db=config.redis.db,
        )
        self.tracing_manager = create_tracing_manager(
            service_name="clustering-service",
            jaeger_host="localhost",
            jaeger_port=6831,
            enabled=True,
        )

        logger.info("Initialized PipelineOrchestrator with all Phase 5-8 components")

    def run_clustering_job(
        self,
        last_run_time: datetime = None,
    ) -> Tuple[int, int, int]:
        """
        Run complete clustering job with error handling and job management.

        Args:
            last_run_time: Timestamp of last successful run

        Returns:
            Tuple of (total_clusters, valid_clusters, invalid_clusters)
        """
        job_id = None
        logger.info("Starting clustering job")

        try:
            # Check circuit breaker
            if not self.circuit_breaker.can_execute():
                logger.error("Circuit breaker is open, skipping job")
                return 0, 0, 0

            # Step 0: Consume and cache entity messages
            # This ensures entities are available for country enrichment later
            self._consume_and_cache_entities()

            # Step 1: Calculate time window
            window_start, window_end = self.time_window_manager.calculate_window(
                last_run_time
            )
            logger.info(f"Processing window: {window_start} to {window_end}")

            # Step 2: Retrieve embeddings
            embeddings, metadata = self.vector_retriever.retrieve_embeddings(
                window_start, window_end, min_credibility=config.clustering.min_credibility
            )

            if len(embeddings) == 0:
                logger.warning("No embeddings found in window")
                return 0, 0, 0

            logger.info(f"Retrieved {len(embeddings)} embeddings")
            logger.info(f"Metadata count: {len(metadata)}")

            # Ensure embeddings and metadata have the same length
            if len(embeddings) != len(metadata):
                logger.error(f"Embeddings ({len(embeddings)}) and metadata ({len(metadata)}) length mismatch")
                return 0, 0, 0

            # Step 3: Perform clustering
            labels = self.clustering_engine.cluster(embeddings)
            logger.info(f"Clustering complete: {len(set(labels))} clusters")

            # Step 3.5: Handle outliers
            # DISABLED: The outlier handler was too aggressive and marking all clusters as noise
            # Instead, let the cluster validator handle quality checks
            # outlier_purity_threshold = 0.3  # Much lower than validation threshold
            # labels = self.outlier_handler.handle_mixed_clusters(
            #     embeddings, labels, purity_threshold=outlier_purity_threshold
            # )
            logger.info(f"Outlier handling complete. Unique labels: {set(labels)}")

            # Step 4: Process clusters
            valid_clusters = []
            invalid_clusters = []

            logger.info(f"Processing {len(set(labels))} unique cluster labels")
            for cluster_id in set(labels):
                if cluster_id == -1:  # Noise points
                    logger.debug(f"Skipping noise cluster")
                    continue

                # Get cluster articles and embeddings
                mask = labels == cluster_id
                cluster_embeddings = embeddings[mask]
                # Use numpy array indexing to get metadata for this cluster
                indices = np.where(mask)[0]
                logger.info(f"Cluster {cluster_id}: mask shape={mask.shape}, indices shape={indices.shape}, metadata type={type(metadata)}, metadata len={len(metadata)}")
                if len(indices) > 0:
                    logger.info(f"First index: {indices[0]}, type: {type(indices[0])}")
                cluster_articles = [metadata[int(i)] for i in indices]

                logger.info(f"Processing cluster {cluster_id} with {len(cluster_articles)} articles")

                # Validate cluster
                is_valid, report = self.validator.validate_cluster(
                    cluster_embeddings,
                    cluster_articles,
                    datetime.utcnow(),
                )

                if not is_valid:
                    logger.warning(
                        f"Cluster {cluster_id} invalid: {report['issues']}"
                    )
                    invalid_clusters.append(cluster_id)
                    continue

                # Compute centroid
                centroid = self.centroid_calculator.compute_unweighted_centroid(
                    cluster_embeddings
                )

                # Generate topic label
                topic_label = self.topic_labeler.generate_label(
                    cluster_articles, method="extractive"
                )

                # Create cluster record with all required Avro schema fields
                cluster_metadata = self.metadata_aggregator.aggregate_cluster_metadata(
                    cluster_articles
                )

                # Extract article_ids for deterministic group_id generation
                article_ids = [a.get("article_id") for a in cluster_articles]

                cluster_record = {
                    "group_id": generate_deterministic_group_id(article_ids),
                    "article_ids": article_ids,
                    "article_count": len(cluster_articles),
                    "similarity_avg": float(report["metrics"].get("similarity_avg", 0.0)),
                    "similarity_min": float(report["metrics"].get("similarity_min", 0.0)),
                    "similarity_std": float(report["metrics"].get("similarity_std", 0.0)),
                    "topic_label": topic_label,
                    "topic_label_method": "extractive",
                    "centroid_vector": centroid.tolist(),
                    "centroid_article_id": "",  # Empty string instead of None for Delta Lake compatibility
                    "languages": cluster_metadata.get("languages", []),
                    "domains": cluster_metadata.get("domains", []),
                    "sources": cluster_metadata.get("sources", []),
                    "countries": cluster_metadata.get("countries", []),
                    "publisher_credibility_avg": float(cluster_metadata.get("publisher_credibility_avg", 0.5)),
                    "earliest_published_at": cluster_metadata.get("earliest_published_at", ""),
                    "latest_published_at": cluster_metadata.get("latest_published_at", ""),
                    "time_span_hours": float(cluster_metadata.get("time_span_hours", 0.0)),
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                    "clustering_algorithm": "hdbscan",
                    "clustering_parameters": {
                        "min_cluster_size": "3",
                        "metric": "cosine",
                    },
                    "embedding_model": "multilingual-e5-large",
                    "embedding_version": "v1.0",
                    "parent_group_id": "",  # Empty string instead of None for Delta Lake compatibility
                    "child_group_ids": [],
                    "evolution_type": "",  # Empty string instead of None for Delta Lake compatibility
                    "cluster_stability_score": 0.5,
                    "job_id": str(uuid4()),
                    "trace_id": str(uuid4()),
                    "schema_version": "1.0",
                }

                valid_clusters.append(cluster_record)

                # Update stability score
                stability_score = self.stability_scorer.compute_stability_score(
                    cluster_record["group_id"], cluster_record
                )
                cluster_record["stability_score"] = stability_score
                self.stability_scorer.update_cluster_history(
                    cluster_record["group_id"], cluster_record
                )

                # Track evolution
                self.temporal_tracker.track_cluster_evolution(
                    cluster_record["group_id"],
                    cluster_articles,
                    centroid,
                    datetime.utcnow(),
                )

            logger.info(
                f"Processed {len(valid_clusters)} valid clusters, "
                f"{len(invalid_clusters)} invalid"
            )

            # Step 4.5: Enrich clusters with countries from entities
            if valid_clusters:
                logger.info("Enriching clusters with countries from NER entities...")
                valid_clusters = self._enrich_clusters_with_countries(valid_clusters)

            # Step 5: Write to storage
            if valid_clusters:
                # Log detailed cluster information for debugging
                for cluster in valid_clusters[:3]:  # Log first 3 clusters
                    logger.info(
                        f"Cluster details: group_id={cluster.get('group_id')}, "
                        f"article_count={cluster.get('article_count')}, "
                        f"similarity_avg={cluster.get('similarity_avg')}, "
                        f"topic_label={cluster.get('topic_label')}, "
                        f"centroid_magnitude={float(np.linalg.norm(np.array(cluster.get('centroid_vector', []))))}"
                    )

                self.delta_writer.write_clusters(valid_clusters)

                # Register clusters and track which are new
                new_clusters = []
                updated_clusters = []
                for cluster in valid_clusters:
                    success, is_new = self.registry.register_cluster(cluster)
                    if success:
                        if is_new:
                            new_clusters.append(cluster)
                        else:
                            updated_clusters.append(cluster)

                # Produce ALL clusters to Kafka (both new and updates)
                # This ensures downstream services (labeler, feature-engineering) always get the latest data
                if valid_clusters:
                    logger.info(
                        f"Producing {len(valid_clusters)} clusters to Kafka: "
                        f"{len(new_clusters)} new, {len(updated_clusters)} updates"
                    )
                    self.producer.produce_batch(valid_clusters)
                    self.producer.flush()
                else:
                    logger.info("No clusters to produce to Kafka")

            logger.info("Clustering job complete")
            return len(set(labels)), len(valid_clusters), len(invalid_clusters)

        except Exception as e:
            logger.error(f"Clustering job failed: {e}", exc_info=True)
            raise

    def _consume_and_cache_entities(self) -> int:
        """
        Consume entity messages from entities_extracted topic and cache them in Redis.

        This method is called at the start of each clustering job to ensure
        entity messages are available for country enrichment later.

        Now uses Redis for persistent caching (survives restarts, 7-day TTL).

        Returns:
            Number of entity messages consumed and cached
        """
        try:
            logger.info("Consuming and caching entity messages to Redis...")

            # Consume ALL available entity messages in batches
            total_consumed = 0
            consecutive_empty_batches = 0
            max_empty_batches = 3
            batch_count = 0

            while consecutive_empty_batches < max_empty_batches:
                batch_count += 1
                entity_messages = self.entities_consumer.consume_batch(
                    batch_size=1000,
                    timeout_ms=5000
                )

                if entity_messages:
                    # Prepare batch for Redis
                    entities_batch = {}
                    for entity_msg in entity_messages:
                        article_id = entity_msg.get("article_id")
                        entities = entity_msg.get("entities", [])

                        if article_id:
                            entities_batch[article_id] = entities
                            # Also update in-memory cache for backward compatibility
                            self.entity_cache[article_id] = entities
                            total_consumed += 1

                    # Batch write to Redis for efficiency
                    if entities_batch:
                        self.cache.set_entities_batch(entities_batch)

                    consecutive_empty_batches = 0
                    logger.info(
                        f"Cached batch {batch_count}: {len(entity_messages)} entity messages to Redis "
                        f"(total consumed: {total_consumed})"
                    )
                else:
                    consecutive_empty_batches += 1
                    logger.debug(
                        f"Empty batch {consecutive_empty_batches}/{max_empty_batches} "
                        f"(batch {batch_count})"
                    )

            # Commit offsets after caching
            if total_consumed > 0:
                self.entities_consumer.commit_offsets()

            # Get Redis cache size for logging
            redis_cache_size = self.cache.get_entity_cache_size()
            logger.info(
                f"Entity caching complete: cached {total_consumed} new messages, "
                f"Redis cache size: {redis_cache_size} articles"
            )

            return total_consumed

        except Exception as e:
            logger.error(f"Error consuming and caching entities: {e}", exc_info=True)
            return 0

    def _enrich_clusters_with_countries(self, clusters: List[Dict]) -> List[Dict]:
        """
        Enrich clusters with countries extracted from NER entities.

        Now uses Redis-backed entity cache instead of in-memory cache.
        This ensures entities are available even after service restarts.

        Args:
            clusters: List of cluster dictionaries

        Returns:
            List of enriched cluster dictionaries with updated countries field
        """
        try:
            # Check Redis cache size
            redis_cache_size = self.cache.get_entity_cache_size()
            if redis_cache_size == 0:
                logger.info("Redis entity cache is empty, no entities available for enrichment")
                return clusters

            logger.info(
                f"Using Redis entity cache for country enrichment: {redis_cache_size} cached articles"
            )

            # Build article_id to cluster mapping
            article_to_cluster = {}
            for cluster in clusters:
                for article_id in cluster.get("article_ids", []):
                    article_to_cluster[article_id] = cluster

            # Extract countries from cached entities and map to clusters
            enrichment_count = 0
            articles_with_countries = 0
            cache_hits = 0
            cache_misses = 0

            for article_id, cluster in article_to_cluster.items():
                # Look up entities from Redis cache
                entities = self.cache.get_entity(article_id)

                if not entities:
                    cache_misses += 1
                    continue

                cache_hits += 1

                # Extract countries from entities
                entity_countries = self.country_extractor.extract_countries_from_entities(entities)

                if entity_countries:
                    articles_with_countries += 1

                    # Merge with existing countries (from article metadata)
                    existing_countries = set(cluster.get("countries", []))
                    new_countries = set(entity_countries)
                    merged_countries = sorted(list(existing_countries | new_countries))

                    # Update cluster (only if new countries were added)
                    if merged_countries != sorted(list(existing_countries)):
                        cluster["countries"] = merged_countries
                        enrichment_count += 1

                        logger.debug(
                            f"Enriched cluster {cluster.get('group_id')} with countries from article {article_id}: "
                            f"existing={list(existing_countries)}, new={list(new_countries)}, merged={merged_countries}"
                        )

            logger.info(
                f"Country enrichment complete (Redis-backed): "
                f"cache_hits={cache_hits}, cache_misses={cache_misses}, "
                f"articles_with_countries={articles_with_countries}, "
                f"enriched {enrichment_count} clusters out of {len(clusters)} total clusters"
            )

            # Log enrichment statistics
            clusters_with_countries = sum(1 for c in clusters if c.get("countries"))
            total_countries = sum(len(c.get("countries", [])) for c in clusters)
            logger.info(
                f"Enrichment statistics: {clusters_with_countries}/{len(clusters)} clusters have countries "
                f"({total_countries} total country codes)"
            )

            return clusters

        except Exception as e:
            logger.error(f"Error enriching clusters with countries: {e}", exc_info=True)
            # Return original clusters if enrichment fails
            return clusters

    async def start_entities_consumer_background(self):
        """Start background task to continuously consume entity messages."""
        if self._entities_consumer_task is not None:
            logger.warning("Entities consumer background task already running")
            return

        self._running = True
        self._entities_consumer_task = asyncio.create_task(self._entities_consumer_loop())
        logger.info("Started background entities consumer task")

    async def stop_entities_consumer_background(self):
        """Stop background entities consumer task."""
        if self._entities_consumer_task is None:
            return

        self._running = False

        # Wait for task to complete with timeout
        try:
            await asyncio.wait_for(self._entities_consumer_task, timeout=5.0)
        except asyncio.TimeoutError:
            logger.warning("Entities consumer task did not stop gracefully, cancelling")
            self._entities_consumer_task.cancel()
            try:
                await self._entities_consumer_task
            except asyncio.CancelledError:
                pass

        self._entities_consumer_task = None
        logger.info("Stopped background entities consumer task")

    async def _entities_consumer_loop(self):
        """Background loop to continuously consume and cache entity messages."""
        logger.info("Entities consumer loop started")

        try:
            while self._running:
                try:
                    # Consume entities in small batches with short timeout
                    # This runs in a non-blocking way
                    await asyncio.get_event_loop().run_in_executor(
                        None,
                        self._consume_entities_batch_sync,
                        50,  # batch_size
                        1000  # timeout_ms
                    )

                    # Small sleep to yield control to event loop
                    await asyncio.sleep(0.1)

                except Exception as e:
                    logger.error(f"Error in entities consumer loop: {e}", exc_info=True)
                    await asyncio.sleep(1.0)  # Back off on error

        except asyncio.CancelledError:
            logger.info("Entities consumer loop cancelled")
        except Exception as e:
            logger.error(f"Fatal error in entities consumer loop: {e}", exc_info=True)
        finally:
            logger.info("Entities consumer loop stopped")

    def _consume_entities_batch_sync(self, batch_size: int, timeout_ms: int):
        """
        Synchronous method to consume a batch of entity messages and cache to Redis.

        This is called from the async loop via run_in_executor.
        Logs every 100 polls to avoid repetitive logging.
        """
        self._poll_count += 1

        # Log every 100 polls to show activity without being repetitive
        if self._poll_count % 100 == 0:
            redis_cache_size = self.cache.get_entity_cache_size()
            logger.info(
                f"Entities consumer poll #{self._poll_count}: "
                f"Redis cache_size={redis_cache_size}"
            )

        try:
            entity_messages = self.entities_consumer.consume_batch(
                batch_size=batch_size,
                timeout_ms=timeout_ms
            )

            if entity_messages:
                # Prepare batch for Redis
                entities_batch = {}
                for entity_msg in entity_messages:
                    article_id = entity_msg.get("article_id")
                    entities = entity_msg.get("entities", [])

                    if article_id:
                        entities_batch[article_id] = entities
                        # Also update in-memory cache for backward compatibility
                        self.entity_cache[article_id] = entities

                # Batch write to Redis for efficiency
                if entities_batch:
                    self.cache.set_entities_batch(entities_batch)

                # Log when messages are actually consumed and cached
                redis_cache_size = self.cache.get_entity_cache_size()
                logger.info(
                    f"Cached {len(entity_messages)} entity messages to Redis, "
                    f"total Redis cache size: {redis_cache_size} articles"
                )

                # Commit offsets
                self.entities_consumer.commit_offsets()

        except Exception as e:
            logger.error(f"Error consuming entities batch: {e}", exc_info=True)

    def close(self):
        """Close all connections."""
        try:
            self.producer.close()
            self.entities_consumer.close()
            self.tracing_manager.shutdown()
            logger.info("Closed PipelineOrchestrator")
        except Exception as e:
            logger.error(f"Error closing PipelineOrchestrator: {e}", exc_info=True)

