"""Main feature engineering service orchestrator."""

from typing import Dict, Any, Optional
import asyncio
from .clients import (
    SemanticGroupConsumer,
    FeaturesProducer,
    PostgresClient,
)
from .extractors import (
    SourceExtractor,
    TemporalExtractor,
    SentimentExtractor,
    EntityExtractor,
    ContentExtractor,
    EmbeddingExtractor,
)
from .transformers import FeatureAggregator, FeatureNormalizer
from .validation import FeatureValidator, QualityChecker
from .storage import FeastWriter, RedisWriter, FeatureReconciliation
from .drift import DriftDetector
from .utils import StructuredLogger, TraceContext, FeatureLineage
from .metrics import metrics
from .exceptions import FeatureError

logger = StructuredLogger(__name__)


class FeatureEngineeringService:
    """Main feature engineering service."""

    def __init__(self):
        """Initialize service."""
        self.consumer = SemanticGroupConsumer()
        self.producer = FeaturesProducer()
        self.postgres_client = PostgresClient()

        # Initialize extractors
        self.extractors = [
            SourceExtractor(),
            TemporalExtractor(),
            SentimentExtractor(),
            EntityExtractor(),
            ContentExtractor(),
            EmbeddingExtractor(),
        ]

        # Initialize transformers
        self.aggregator = FeatureAggregator()
        self.normalizer = FeatureNormalizer()

        # Initialize validators
        self.validator = FeatureValidator()
        self.quality_checker = QualityChecker()

        # Initialize storage
        self.feast_writer = FeastWriter()
        self.redis_writer = RedisWriter()
        self.reconciliation = FeatureReconciliation()

        # Initialize drift detection
        self.drift_detector = DriftDetector()

    def start(self):
        """Start the service."""
        try:
            logger.info("Starting feature engineering service")

            # Connect to all services
            self.consumer.connect()
            self.producer.connect()
            self.postgres_client.connect()

            logger.info("All connections established")

            # Start consuming messages
            self._consume_loop()

        except Exception as e:
            logger.error("Error starting service", error=str(e))
            raise

    def _consume_loop(self):
        """Main consumption loop."""
        try:
            while True:
                try:
                    # Consume message
                    message = self.consumer.consume_message(timeout_ms=1000)

                    if message is None:
                        continue

                    # Process message
                    self._process_message(message)
                except Exception as e:
                    logger.warning("Error processing message, continuing", error=str(e))
                    continue

        except KeyboardInterrupt:
            logger.info("Service interrupted")
        except Exception as e:
            logger.error("Fatal error in consumption loop", error=str(e))
        finally:
            self.shutdown()

    def _process_message(self, message: Dict[str, Any]):
        """Process a semantic group message.

        Args:
            message: Semantic group message
        """
        try:
            group_id = message.get("group_id")
            trace_id = message.get("trace_id", "unknown")

            with TraceContext(trace_id=trace_id, group_id=group_id, operation="compute_features") as ctx:
                # Extract features
                features = self._extract_features(message)

                # Transform features
                features = self._transform_features(features)

                # Validate features
                is_valid, errors = self.validator.validate(features)
                if not is_valid:
                    logger.warning(
                        "Feature validation failed",
                        group_id=group_id,
                        errors=errors,
                    )
                    metrics.feature_validation_failures_total.inc()
                    return

                # Write to storage
                self._write_features(group_id, features)

                # Produce to Kafka
                self.producer.produce_message(group_id, features)

                # Commit offset
                self.consumer.commit_offset()

                # Update metrics
                metrics.feature_computed_total.inc()

                logger.info(
                    "Message processed successfully",
                    group_id=group_id,
                    feature_count=len(features),
                )

        except Exception as e:
            logger.error("Error processing message", error=str(e))
            metrics.feature_validation_failures_total.inc()

    def _extract_features(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Extract features from message.

        Args:
            message: Semantic group message

        Returns:
            Dictionary of extracted features
        """
        features = {}

        try:
            # Extract using all extractors
            for extractor in self.extractors:
                extracted = extractor.extract(
                    group=message.get("group"),
                    articles=message.get("articles", []),
                    actors=message.get("actors", []),
                )
                features.update(extracted)

            logger.info(
                "Features extracted",
                feature_count=len(features),
            )
            return features

        except Exception as e:
            logger.error("Error extracting features", error=str(e))
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
            # Write to Feast (offline)
            self.feast_writer.write_features(group_id, features)
            metrics.feature_feast_writes_total.inc()

            # Write to Redis (online)
            self.redis_writer.write_features(group_id, features)
            metrics.feature_redis_writes_total.inc()

            logger.info("Features written to storage", group_id=group_id)

        except Exception as e:
            logger.error("Error writing features", error=str(e), group_id=group_id)
            raise FeatureError(f"Error writing features: {str(e)}")

    def shutdown(self):
        """Shutdown service."""
        try:
            logger.info("Shutting down service")

            self.consumer.close()
            self.producer.close()
            self.postgres_client.close()
            self.feast_writer.close()
            self.redis_writer.close()
            self.reconciliation.close()

            logger.info("Service shutdown complete")

        except Exception as e:
            logger.error("Error during shutdown", error=str(e))

