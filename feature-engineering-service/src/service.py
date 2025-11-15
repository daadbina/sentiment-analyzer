"""Main feature engineering service orchestrator."""

from typing import Dict, Any, Optional
import asyncio
import time
from .clients import (
    SemanticGroupConsumer,
    FeaturesProducer,
    PostgresClient,
)
from .clients.qdrant_client import QdrantVectorClient
from .clients.entities_consumer import EntitiesConsumer
from .clients.reconciliation_consumer import ReconciliationConsumer
from .extractors import (
    SourceExtractor,
    TemporalExtractor,
    SentimentExtractor,
    EntityExtractor,
    ContentExtractor,
    EmbeddingExtractor,
    BtcPriceExtractor,
    Article,
)
from .transformers import FeatureAggregator, FeatureNormalizer
from .validation import FeatureValidator, QualityChecker
from .storage import FeastWriter, RedisWriter, FeatureReconciliation, DeltaLakeWriter, BtcFeaturesWriter
from .drift import DriftDetector
from .utils import StructuredLogger, TraceContext, FeatureLineage
from .metrics import metrics
from .exceptions import FeatureError
from .config import QdrantConfig, FeastConfig
from .feast import FeastRegistry, create_semantic_group_feature_view

logger = StructuredLogger(__name__)


class FeatureEngineeringService:
    """Main feature engineering service."""

    def __init__(self):
        """Initialize service."""
        self.consumer = SemanticGroupConsumer()
        self.reconciliation_consumer = ReconciliationConsumer()  # Consumer for reconciliation_completed events
        self.producer = FeaturesProducer()
        self.postgres_client = PostgresClient()
        self.entities_consumer = EntitiesConsumer()
        qdrant_config = QdrantConfig()
        self.qdrant_client = QdrantVectorClient(config=qdrant_config)
        feast_config = FeastConfig()
        self.feature_version = feast_config.feature_version

        # Background task for reconciliation consumer
        self.reconciliation_task = None
        self.running = False

        # Initialize Feast registry
        self.feast_registry = FeastRegistry(config=feast_config)

        # Initialize extractors
        self.extractors = [
            SourceExtractor(),
            TemporalExtractor(),
            SentimentExtractor(),
            EntityExtractor(),
            ContentExtractor(),
            EmbeddingExtractor(self.postgres_client),  # Pass postgres_client for countries lookup
            BtcPriceExtractor(self.postgres_client),  # BTC price features
        ]

        # Initialize transformers
        self.aggregator = FeatureAggregator()
        self.normalizer = FeatureNormalizer()

        # Initialize validators
        self.validator = FeatureValidator()
        self.quality_checker = QualityChecker()

        # Initialize storage
        self.feast_writer = FeastWriter()  # ENABLED - using SDK push() to remote Redis
        # self.redis_writer = RedisWriter()  # DISABLED - replaced by Feast
        self.reconciliation = FeatureReconciliation()
        self.delta_writer = DeltaLakeWriter()
        self.btc_writer = BtcFeaturesWriter()  # BTC features parquet writer

        # Initialize drift detection
        self.drift_detector = DriftDetector()

        # BTC features generation state
        self.btc_features_last_generated = None
        self.btc_features_interval_seconds = 3600  # Generate every hour

    async def start(self):
        """Start the service."""
        try:
            logger.info("Starting feature engineering service")

            # Connect to all services
            self.consumer.connect()
            self.producer.connect()
            await self.postgres_client.connect()
            self.qdrant_client.connect()

            # Connect to reconciliation consumer
            await self.reconciliation_consumer.connect()
            logger.info("Reconciliation consumer connected")

            # Initialize entities consumer
            try:
                self.entities_consumer.initialize()
                logger.info("Entities consumer initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize entities consumer: {e} (entities will be empty)")

            logger.info("All connections established")

            # Start background task for reconciliation events
            self.running = True
            self.reconciliation_task = asyncio.create_task(self._consume_reconciliation_events())
            logger.info("Started background task for reconciliation events")

            # Initialize Feast registry and register feature view
            self._initialize_feast_registry()

            # Start consuming messages
            await self._consume_loop()

        except Exception as e:
            logger.error("Error starting service", error=str(e))
            raise

    def _initialize_feast_registry(self):
        """Initialize Feast registry and register feature view."""
        try:
            logger.info("Initializing Feast registry")

            # Connect to Feast registry
            logger.debug("Connecting to Feast registry")
            self.feast_registry.connect()
            logger.debug("Feast registry connected")

            # Create and register feature view
            logger.debug("Creating semantic group feature view")
            feature_view = create_semantic_group_feature_view()
            logger.debug("Feature view created", feature_view_name=feature_view.name)

            logger.debug("Registering feature view in Feast")
            self.feast_registry.register_feature_view(feature_view)
            logger.debug("Feature view registered")

            # Verify feature view is registered
            logger.debug("Verifying feature view registration")
            fv = self.feast_registry.get_feature_view("semantic_group_features")
            if fv:
                logger.info(
                    "Feature view registered successfully",
                    feature_view_name="semantic_group_features",
                    num_features=len(fv.features),
                )
            else:
                logger.warning("Feature view registration verification failed")

        except Exception as e:
            logger.error(
                "Error initializing Feast registry",
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            # Don't fail startup, just warn
            logger.warning("Continuing without Feast registry initialization")

    async def _consume_loop(self):
        """Main consumption loop."""
        try:
            # Generate initial BTC features on startup
            await self._generate_btc_features()

            while True:
                try:
                    # Consume entities batch (non-blocking)
                    if self.entities_consumer.consumer:
                        self.entities_consumer.consume_batch(timeout_seconds=0.1, max_messages=50)

                    # Check if we need to regenerate BTC features
                    await self._check_and_generate_btc_features()

                    # Consume message
                    message = self.consumer.consume_message(timeout_ms=1000)

                    if message is None:
                        continue

                    # Process message
                    await self._process_message(message)
                except Exception as e:
                    logger.warning("Error processing message, continuing", error=str(e), exc_info=True)
                    continue

        except KeyboardInterrupt:
            logger.info("Service interrupted")
        except Exception as e:
            logger.error("Fatal error in consumption loop", error=str(e), exc_info=True)
        finally:
            await self.shutdown()

    async def _process_message(self, message: Dict[str, Any]):
        """Process a semantic group message.

        Args:
            message: Semantic group message
        """
        try:
            group_id = message.get("group_id")
            trace_id = message.get("trace_id", "unknown")

            # Log incoming message details
            logger.info(
                "=== FEATURE ENGINEERING: Processing semantic group ===",
                group_id=group_id,
                trace_id=trace_id,
                message_keys=list(message.keys()),
                article_count=len(message.get("articles", [])),
            )

            with TraceContext(trace_id=trace_id, group_id=group_id, operation="compute_features") as ctx:
                # Extract features
                features = await self._extract_features(message)

                # Skip if no features extracted (e.g., group has 0 articles)
                if not features:
                    logger.info(
                        "No features extracted, skipping semantic group",
                        group_id=group_id,
                    )
                    # Commit offset to skip this message
                    self.consumer.commit_offset()
                    return

                # Log extracted features
                logger.info(
                    "Features extracted from semantic group",
                    group_id=group_id,
                    feature_count=len(features),
                    feature_names=list(features.keys())[:20],  # First 20 feature names
                    sample_features={k: features[k] for k in list(features.keys())[:5]},  # First 5 features with values
                )

                # Transform features
                features = self._transform_features(features)

                # Log transformed features
                logger.info(
                    "Features transformed",
                    group_id=group_id,
                    feature_count=len(features),
                    sample_transformed_features={k: features[k] for k in list(features.keys())[:5]},
                )

                # Validate features
                is_valid, errors = self.validator.validate(features)
                if not is_valid:
                    logger.warning(
                        "Feature validation failed",
                        group_id=group_id,
                        errors=errors,
                    )
                    metrics.validation_failures.labels(feature_type="validation").inc()
                    return

                # Write to storage
                self._write_features(group_id, features)

                # Produce to Kafka with metadata
                start_time = time.time()
                self.producer.produce_message(
                    group_id=group_id,
                    features=features,
                    feature_version=self.feature_version,
                    validation_status="VALID",
                    validation_failures=[],
                    computation_duration_ms=int((time.time() - start_time) * 1000),
                    trace_id=getattr(self, '_trace_id', ''),
                )

                # Commit offset
                self.consumer.commit_offset()

                # Update metrics
                metrics.features_computed.labels(feature_type="all").inc()

                logger.info(
                    "Message processed successfully",
                    group_id=group_id,
                    feature_count=len(features),
                )

        except Exception as e:
            logger.error("Error processing message", error=str(e), exc_info=True)
            metrics.validation_failures.labels(feature_type="extraction").inc()

    def _convert_articles(self, article_dicts: list) -> list:
        """Convert article dictionaries to Article objects.

        Args:
            article_dicts: List of article dictionaries from Qdrant

        Returns:
            List of Article objects
        """
        articles = []
        for article_dict in article_dicts:
            try:
                article_id = article_dict.get("article_id", "")

                # Get entities from cache if available
                entities = self.entities_consumer.get_entities(article_id)
                if not entities:
                    # Fallback to entities in article_dict if not in cache
                    entities = article_dict.get("entities", [])

                article = Article(
                    article_id=article_id,
                    title=article_dict.get("title", ""),
                    body=article_dict.get("body", ""),
                    language=article_dict.get("language", ""),
                    domain=article_dict.get("domain", ""),
                    source=article_dict.get("source", ""),
                    published_at=article_dict.get("published_at", ""),
                    sentiment_score=float(article_dict.get("sentiment_score", 0.0)),
                    entities=entities,
                    publisher_credibility=article_dict.get("publisher_credibility"),
                )
                articles.append(article)
            except Exception as e:
                logger.warning(
                    "Error converting article dict to Article object",
                    article_id=article_dict.get("article_id"),
                    error=str(e),
                )
                continue
        return articles

    async def _extract_features(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Extract features from message.

        Args:
            message: Semantic group message from Kafka

        Returns:
            Dictionary of extracted features
        """
        features = {}

        try:
            group_id = message.get("group_id")
            article_ids = message.get("article_ids", [])

            logger.debug(
                "Extracting features",
                group_id=group_id,
                article_count=len(article_ids),
            )

            # Fetch article metadata from Qdrant using article IDs
            article_dicts = []
            if article_ids:
                try:
                    article_dicts = self.qdrant_client.get_articles_by_ids(article_ids)
                    logger.debug(
                        "Articles fetched from Qdrant",
                        requested=len(article_ids),
                        fetched=len(article_dicts),
                    )
                except Exception as e:
                    logger.warning(
                        "Failed to fetch articles from Qdrant",
                        error=str(e),
                        article_count=len(article_ids),
                    )
                    article_dicts = []

            # Convert article dicts to Article objects
            articles = self._convert_articles(article_dicts)

            # Skip semantic groups with 0 articles - cannot extract general features
            # BTC extractor doesn't need articles, but general extractors do
            # Without articles, we'd only have BTC features which is incomplete
            if not articles or len(articles) == 0:
                logger.warning(
                    "Skipping semantic group with 0 articles - cannot extract general features",
                    group_id=group_id,
                    article_ids_count=len(article_ids),
                    fetched_articles_count=len(article_dicts),
                )
                # Return empty features dict to skip this group gracefully
                return {}

            # Extract using all extractors
            for extractor in self.extractors:
                extracted = await extractor.extract(
                    group=message,
                    articles=articles,
                    actors=[],
                )
                features.update(extracted)

            # Filter: Skip groups without countries (cannot predict conflicts between countries)
            countries = features.get("countries", "")
            if not countries or countries.strip() == "":
                logger.info(
                    "Skipping semantic group without countries - cannot predict conflicts between countries",
                    group_id=group_id,
                    feature_count=len(features),
                )
                # Return empty features dict to skip this group gracefully
                return {}

            logger.info(
                "Features extracted",
                group_id=group_id,
                feature_count=len(features),
                feature_names=list(features.keys())[:20],  # First 20 feature names
                sample_features={k: features[k] for k in list(features.keys())[:5]},  # First 5 features with values
                countries=countries,
            )
            return features

        except Exception as e:
            logger.error("Error extracting features", error=str(e), exc_info=True)
            raise FeatureError(f"Error extracting features: {str(e)}")

    def _transform_features(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Transform features.

        Args:
            features: Extracted features

        Returns:
            Transformed features
        """
        try:
            # Aggregate
            features = self.aggregator.transform(features)

            # Normalize
            features = self.normalizer.transform(features)

            logger.info("Features transformed")
            return features

        except Exception as e:
            logger.error("Error transforming features", error=str(e))
            raise FeatureError(f"Error transforming features: {str(e)}")

    def _write_features(self, group_id: str, features: Dict[str, Any]):
        """Write features to storage.

        Args:
            group_id: Semantic group ID
            features: Features to write
        """
        try:
            # Remove metadata columns that shouldn't be in the feature store
            # These are only for monitoring/validation
            metadata_columns = {
                "feature_count",
                "feature_sum",
                "feature_mean",
                "feature_min",
                "feature_max",
                "feature_range",
            }

            # Create a clean copy of features without metadata
            clean_features = {
                k: v for k, v in features.items()
                if k not in metadata_columns
            }

            logger.debug(
                "Removed metadata columns before writing",
                group_id=group_id,
                original_count=len(features),
                clean_count=len(clean_features),
                removed_columns=list(metadata_columns & set(features.keys())),
            )

            # Write to Delta Lake (offline) - for backup and historical analysis
            logger.info(
                "=== WRITING TO DELTA LAKE ===",
                group_id=group_id,
                feature_count=len(clean_features),
                sample_features={k: clean_features[k] for k in list(clean_features.keys())[:5]},
            )
            self.delta_writer.write_features(group_id, clean_features)
            logger.info("✓ Features written to Delta Lake successfully", group_id=group_id)

            # Write to Feast offline store via SDK
            logger.info(
                "=== WRITING TO FEAST OFFLINE STORE ===",
                group_id=group_id,
                feature_count=len(clean_features),
            )
            self.feast_writer.write_features(
                group_id=group_id,
                features=clean_features,
                to="offline"
            )
            metrics.feast_writes.inc()
            logger.info("✓ Features written to Feast offline store successfully", group_id=group_id)

            logger.info(
                "=== ALL FEATURES WRITTEN SUCCESSFULLY ===",
                group_id=group_id,
                feature_count=len(clean_features),
                storage_backends=["Delta Lake", "Feast (Online + Offline)"],
            )

        except Exception as e:
            logger.error(
                "Error writing features",
                error=str(e),
                group_id=group_id,
                error_type=type(e).__name__,
            )
            raise FeatureError(f"Error writing features: {str(e)}")

    async def _check_and_generate_btc_features(self):
        """Check if BTC features need to be regenerated and generate if needed."""
        try:
            current_time = time.time()

            # Check if we need to regenerate
            if self.btc_features_last_generated is None:
                # First generation failed or not yet attempted, try now
                logger.info("BTC features not yet generated successfully, attempting generation")
                await self._generate_btc_features()
                return

            time_since_last_gen = current_time - self.btc_features_last_generated

            if time_since_last_gen >= self.btc_features_interval_seconds:
                logger.info(f"BTC features interval reached ({time_since_last_gen:.0f}s >= {self.btc_features_interval_seconds}s), regenerating")
                await self._generate_btc_features()

        except Exception as e:
            logger.error("Error checking BTC features generation", error=str(e))

    async def _generate_btc_features(self):
        """Generate historical BTC features and save to parquet."""
        try:
            logger.info("=== GENERATING HISTORICAL BTC FEATURES ===")

            # Get BTC extractor
            btc_extractor = None
            for extractor in self.extractors:
                if isinstance(extractor, BtcPriceExtractor):
                    btc_extractor = extractor
                    break

            if not btc_extractor:
                logger.error("BTC extractor not found in extractors list")
                return

            # Generate features for last 1000 BTC records
            features_list = await btc_extractor.generate_historical_btc_features(limit=1000)

            if not features_list:
                logger.warning("No BTC features generated")
                return

            # Write to parquet
            self.btc_writer.write_features(features_list)

            # Update last generated timestamp
            self.btc_features_last_generated = time.time()

            logger.info(
                f"✓ BTC features generated and saved successfully: "
                f"{len(features_list)} records"
            )

        except Exception as e:
            logger.error("Error generating BTC features", error=str(e), exc_info=True)

    async def _consume_reconciliation_events(self):
        """Background task to consume reconciliation_completed events and re-process groups."""
        logger.info("Starting reconciliation events consumer")

        while self.running:
            try:
                # Consume reconciliation event
                event = self.reconciliation_consumer.consume_message(timeout=1.0)

                if event is None:
                    await asyncio.sleep(0.1)
                    continue

                # Re-process the group
                await self._reprocess_group(event)

            except asyncio.CancelledError:
                logger.info("Reconciliation consumer cancelled")
                break
            except Exception as e:
                logger.error(
                    f"Error consuming reconciliation event: {str(e)}",
                    error_type=type(e).__name__,
                    exc_info=True
                )
                await asyncio.sleep(1.0)  # Wait before retry

        logger.info("Reconciliation events consumer stopped")

    async def _reprocess_group(self, reconciliation_event: Dict[str, Any]):
        """Re-process a group when reconciliation completes.

        Args:
            reconciliation_event: Reconciliation completed event from Kafka
        """
        try:
            group_id = reconciliation_event.get("group_id")
            has_conflict = reconciliation_event.get("has_conflict")

            logger.info(
                f"Re-processing group after reconciliation",
                group_id=group_id,
                has_conflict=has_conflict
            )

            # Fetch the semantic group from Kafka or database
            # For now, we'll query the database to get the group
            group = await self._fetch_group_from_database(group_id)

            if not group:
                logger.warning(
                    f"Group not found for re-processing",
                    group_id=group_id
                )
                return

            # Extract features (this will query reconciliation_log and get updated has_conflict)
            features = await self._extract_features(group)

            if not features:
                logger.warning(
                    f"No features extracted for re-processed group",
                    group_id=group_id
                )
                return

            # Update Delta Lake with new has_conflict value
            self.delta_writer.write_features(group_id, features)

            logger.info(
                f"✓ Group re-processed successfully after reconciliation",
                group_id=group_id,
                has_conflict=features.get("has_conflict")
            )

        except Exception as e:
            logger.error(
                f"Error re-processing group: {str(e)}",
                group_id=reconciliation_event.get("group_id"),
                error_type=type(e).__name__,
                exc_info=True
            )

    async def _fetch_group_from_database(self, group_id: str) -> Optional[Dict[str, Any]]:
        """Fetch semantic group from database.

        Args:
            group_id: Group ID to fetch

        Returns:
            Group dict or None if not found
        """
        try:
            query = """
                SELECT
                    group_id,
                    article_ids,
                    article_count,
                    similarity_avg,
                    topic_label,
                    centroid_vector,
                    cluster_metadata,
                    countries,
                    created_at
                FROM semantic_groups
                WHERE group_id = $1
            """

            result = await self.postgres_client.execute_query(query, str(group_id))

            if not result or len(result) == 0:
                return None

            row = result[0]

            # Convert to message format
            # Handle None values explicitly
            article_ids = row.get("article_ids")
            if article_ids is None:
                article_ids = []

            countries = row.get("countries")
            if countries is None:
                countries = []

            group = {
                "group_id": str(row.get("group_id")),
                "article_ids": article_ids,
                "article_count": row.get("article_count") or 0,
                "similarity_avg": float(row.get("similarity_avg") or 0.0),
                "topic_label": row.get("topic_label") or "",
                "countries": countries,
                "created_at": row.get("created_at").isoformat() if row.get("created_at") else None,
            }

            return group

        except Exception as e:
            logger.error(
                f"Error fetching group from database: {str(e)}",
                group_id=group_id,
                error_type=type(e).__name__
            )
            return None

    async def shutdown(self):
        """Shutdown service."""
        try:
            logger.info("Shutting down service")

            # Stop reconciliation task
            self.running = False
            if self.reconciliation_task and not self.reconciliation_task.done():
                self.reconciliation_task.cancel()
                try:
                    await self.reconciliation_task
                except asyncio.CancelledError:
                    logger.info("Reconciliation task cancelled")

            self.consumer.close()
            self.producer.close()
            await self.postgres_client.close()
            await self.reconciliation_consumer.disconnect()
            self.entities_consumer.shutdown()
            self.feast_registry.close()
            self.feast_writer.close()  # ENABLED
            # self.redis_writer.close()  # DISABLED - replaced by Feast
            self.reconciliation.close()
            self.btc_writer.close()

            logger.info("Service shutdown complete")

        except Exception as e:
            logger.error("Error during shutdown", error=str(e))

