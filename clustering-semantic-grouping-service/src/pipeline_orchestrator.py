"""Main clustering pipeline orchestrator."""

import logging
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


class PipelineOrchestrator:
    """Orchestrates the complete clustering pipeline."""

    def __init__(self):
        """Initialize pipeline orchestrator."""
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
        self.outlier_handler = OutlierHandler(
            k_neighbors=5,
            distance_threshold=0.5,
            reassignment_threshold=config.clustering.similarity_threshold,
        )
        self.incremental_clusterer = IncrementalClusterer(
            similarity_threshold=config.clustering.similarity_threshold,
            max_cluster_age_hours=config.validation.max_time_span_hours,
            merge_threshold=0.90,
        )
        self.stability_scorer = ClusterStabilityScorer(
            min_stability_score=0.70,
            history_window_size=10,
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

            # Step 1: Calculate time window
            window_start, window_end = self.time_window_manager.calculate_window(
                last_run_time
            )
            logger.info(f"Processing window: {window_start} to {window_end}")

            # Step 2: Retrieve embeddings
            embeddings, metadata = self.vector_retriever.retrieve_embeddings(
                window_start, window_end
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
            # Use a lower threshold for outlier handling to avoid marking all points as noise
            outlier_purity_threshold = 0.3  # Much lower than validation threshold
            labels = self.outlier_handler.handle_mixed_clusters(
                embeddings, labels, purity_threshold=outlier_purity_threshold
            )
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

                cluster_record = {
                    "group_id": str(uuid4()),
                    "article_ids": [a.get("article_id") for a in cluster_articles],
                    "article_count": len(cluster_articles),
                    "similarity_avg": float(report["metrics"].get("similarity_avg", 0.0)),
                    "similarity_min": float(report["metrics"].get("similarity_min", 0.0)),
                    "similarity_std": float(report["metrics"].get("similarity_std", 0.0)),
                    "topic_label": topic_label,
                    "topic_label_method": "extractive",
                    "centroid_vector": centroid.tolist(),
                    "centroid_article_id": None,
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
                    "parent_group_id": None,
                    "child_group_ids": [],
                    "evolution_type": None,
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

            # Step 5: Write to storage
            if valid_clusters:
                self.delta_writer.write_clusters(valid_clusters)
                for cluster in valid_clusters:
                    self.registry.register_cluster(cluster)
                self.producer.produce_batch(valid_clusters)
                self.producer.flush()

            logger.info("Clustering job complete")
            return len(set(labels)), len(valid_clusters), len(invalid_clusters)

        except Exception as e:
            logger.error(f"Clustering job failed: {e}", exc_info=True)
            raise

    def close(self):
        """Close all connections."""
        try:
            self.producer.close()
            self.tracing_manager.shutdown()
            logger.info("Closed PipelineOrchestrator")
        except Exception as e:
            logger.error(f"Error closing PipelineOrchestrator: {e}", exc_info=True)

