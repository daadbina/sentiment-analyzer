"""Main validator service."""

import logging
import asyncio
import time
from datetime import datetime
from src.config import get_config
from src.models import NewsValidated, NewsRejected
from src.clients.kafka_consumer import KafkaNewsConsumer
from src.clients.kafka_producer import KafkaNewsProducer
from src.clients.kafka_admin import KafkaAdminClient
from src.clients.dedup_grpc_client import DedupGrpcClient
from src.cache.redis_manager import RedisCacheManager
from src.repositories.source_registry import SourceRegistryRepository
from src.repositories.audit_log import AuditLogRepository
from src.repositories.database_initializer import DatabaseInitializer
from src.pipeline.orchestrator import ValidationPipeline
from src.pipeline.schema_stage import SchemaValidationStage
from src.pipeline.encoding_stage import EncodingValidationStage
from src.pipeline.timestamp_stage import TimestampValidationStage
from src.pipeline.language_stage import LanguageDetectionStage
from src.pipeline.source_stage import SourceVerificationStage
from src.pipeline.duplicate_stage import DuplicateDetectionStage
from src.pipeline.quality_stage import QualityScoringStage
from src.pipeline.geographic_stage import GeographicExtractionStage
from src.pipeline.scoring_stage import ValidationScoringStage
from src.validation.scoring import ValidationScorer
from src.metrics import get_metrics
from src.utils.trace import set_trace_id, generate_trace_id
from src.utils.backpressure import BackpressureManager
from ulid import ULID

logger = logging.getLogger(__name__)


class ValidatorService:
    """Main validator service."""

    def __init__(self):
        """Initialize validator service."""
        self.config = get_config()
        self.consumer = KafkaNewsConsumer()
        self.producer = KafkaNewsProducer()
        self.dedup_client = DedupGrpcClient()
        self.cache_manager = RedisCacheManager()
        self.source_registry = SourceRegistryRepository()
        self.audit_log = AuditLogRepository()
        self.metrics = get_metrics()
        self.pipeline: ValidationPipeline = None

        # Initialize backpressure manager
        self.backpressure = BackpressureManager(
            lag_threshold=10000,  # 10k messages
            throttle_delay_ms=100,
            max_throttle_delay_ms=5000,
        )

        # Batch commit configuration
        self.batch_commit_size = 10  # Commit every 10 messages
        self.batch_commit_timeout_ms = 5000  # Or every 5 seconds
        self.message_batch = []  # Buffer for batch commits
        self.last_batch_commit_time = time.time()

        self._initialize_pipeline()

    def _initialize_pipeline(self) -> None:
        """Initialize validation pipeline."""
        stages = [
            SchemaValidationStage(),
            EncodingValidationStage(),
            TimestampValidationStage(),
            LanguageDetectionStage(),
            SourceVerificationStage(self.source_registry),
            DuplicateDetectionStage(self.dedup_client, self.cache_manager),
            QualityScoringStage(),
            GeographicExtractionStage(),
            ValidationScoringStage(),
        ]
        self.pipeline = ValidationPipeline(stages)

    async def initialize(self) -> None:
        """Initialize service."""
        try:
            # Initialize Kafka topics
            try:
                kafka_admin = KafkaAdminClient()
                if kafka_admin.ensure_topics_exist():
                    logger.info("Kafka topics initialized")
                else:
                    logger.warning("Kafka topic initialization had issues, continuing...")
                kafka_admin.close()
            except Exception as e:
                logger.warning(f"Kafka topic initialization failed: {e}")

            # Initialize database tables and indexes
            try:
                if await DatabaseInitializer.initialize():
                    logger.info("Database tables and indexes initialized")
                else:
                    logger.warning("Database initialization had issues, continuing...")
            except Exception as e:
                logger.warning(f"Database initialization failed: {e}")

            # Initialize source registry
            try:
                await self.source_registry.initialize()
                logger.info("Source registry initialized")
            except Exception as e:
                logger.warning(f"Source registry initialization failed: {e}")

            # Initialize audit log
            try:
                await self.audit_log.initialize()
                logger.info("Audit log initialized")
            except Exception as e:
                logger.warning(f"Audit log initialization failed: {e}")

            # Initialize dedup client
            try:
                await self.dedup_client.initialize()
                logger.info("Dedup client initialized")
            except Exception as e:
                logger.warning(f"Dedup client initialization failed: {e}")

            # Subscribe to Kafka topic
            try:
                self.consumer.subscribe(["news_raw"])
                logger.info("Subscribed to news_raw topic")
            except Exception as e:
                logger.warning(f"Kafka subscription failed: {e}")

            logger.info("Validator service initialized (with optional components)")
        except Exception as e:
            logger.error(f"Critical initialization error: {e}")
            raise

    async def process_message(self) -> None:
        """Process single message from Kafka."""
        try:
            # Poll for message
            msg = self.consumer.poll(timeout_ms=1000)
            if not msg:
                return

            logger.debug(f"Received message from partition {msg.partition()}, offset {msg.offset()}")

            # Deserialize
            raw_message = self.consumer.deserialize_message(msg)
            logger.info(f"Processing article: {raw_message.url} from {raw_message.source}")

            # Generate trace ID
            trace_id = generate_trace_id()
            set_trace_id(trace_id)

            # Create validation context
            from src.models import ValidationContext

            context = ValidationContext(
                article_id=raw_message.article_id,
                trace_id=trace_id,
                job_id=raw_message.ingest_job_id,
                raw_message=raw_message,
            )

            # Execute pipeline
            result = await self.pipeline.execute(context)
            logger.info(f"Validation complete: score={result.validation_score:.2f}, errors={len(result.errors)}")

            # Route result
            await self._route_result(result, context)

            # Add to batch for batch commit
            self.message_batch.append(msg)

            # Check if batch should be committed
            current_time = time.time()
            time_since_last_commit = (current_time - self.last_batch_commit_time) * 1000  # Convert to ms

            if len(self.message_batch) >= self.batch_commit_size or time_since_last_commit >= self.batch_commit_timeout_ms:
                await self._commit_batch()

            # Update metrics
            self.metrics.messages_consumed_total.inc()
            logger.debug(f"Message processed, batch size: {len(self.message_batch)}, total consumed: {self.metrics.messages_consumed_total._value.get()}")

        except Exception as e:
            logger.error(f"Message processing error: {e}", exc_info=True)
            self.metrics.messages_rejected_total.inc()

    async def _commit_batch(self) -> None:
        """Commit batch of messages to Kafka.

        Commits all messages in the batch buffer asynchronously.
        """
        if not self.message_batch:
            return

        try:
            self.consumer.commit_batch(self.message_batch, asynchronous=True)
            logger.info(f"Batch committed: {len(self.message_batch)} messages")
            self.message_batch = []
            self.last_batch_commit_time = time.time()
        except Exception as e:
            logger.error(f"Batch commit failed: {e}")
            # Don't clear batch on error - will retry on next batch

    def _determine_routing(self, result) -> str:
        """Determine routing decision based on validation result.

        Args:
            result: Validation result

        Returns:
            Routing decision: "accept", "reprocess", or "reject"
        """
        if result.errors:
            logger.info(f"Routing decision: reject (errors detected: {result.errors[0]})")
            return "reject"

        routing = ValidationScorer.decide_routing(result.validation_score)
        logger.info(f"Routing decision: {routing} (score: {result.validation_score:.2f})")
        return routing

    def _create_validated_message(self, result, context) -> NewsValidated:
        """Create validated message from validation result.

        Args:
            result: Validation result
            context: Validation context

        Returns:
            NewsValidated message
        """
        return NewsValidated(
            article_id=context.raw_message.article_id,
            canonical_url=context.raw_message.canonical_url,
            title=context.raw_message.title,
            body=context.raw_message.body,
            url=context.raw_message.url,
            source=context.raw_message.source,
            language=context.language or context.raw_message.language,
            language_confidence=context.language_confidence or 0.0,
            language_detection_method=context.language_detection_method or "none",
            source_published_at_raw=context.raw_message.published_at,
            source_published_at_utc=context.source_published_at_utc or "",
            ingested_at=context.ingested_at,
            validated_at=datetime.utcnow().isoformat(),
            country=context.raw_message.country,
            checksum=context.raw_message.checksum,
            validation_score=result.validation_score,
            validation_details=context.validation_details,
            schema_version=context.raw_message.schema_version,
            ingest_job_id=context.raw_message.ingest_job_id,
            validation_job_id=context.raw_message.ingest_job_id,
            trace_id=result.trace_id,
            publisher_id=context.raw_message.publisher_id,
        )

    def _create_original_message_dict(self, context) -> dict:
        """Create original message dict for rejection.

        Args:
            context: Validation context

        Returns:
            Original message dictionary
        """
        return {
            "id": context.raw_message.article_id,
            "title": context.raw_message.title,
            "body": context.raw_message.body,
            "url": context.raw_message.url,
            "published_at": context.raw_message.published_at,
            "language": context.raw_message.language,
            "source": context.raw_message.source,
            "feed_id": None,
            "job_id": context.raw_message.ingest_job_id,
            "validation_score": context.raw_message.validation_score,
            "crawled_at": context.raw_message.crawled_at,
            "checksum": context.raw_message.checksum,
        }

    def _get_rejection_reason(self, result, routing: str) -> str:
        """Get rejection reason based on result and routing.

        Args:
            result: Validation result
            routing: Routing decision

        Returns:
            Rejection reason string
        """
        if result.errors:
            return result.errors[0]
        elif routing == "reprocess":
            return f"Reprocess required (score: {result.validation_score:.2f})"
        else:
            return f"Quality score below threshold (score: {result.validation_score:.2f})"

    def _create_rejected_message(self, result, context, routing: str, rejection_reason: str) -> NewsRejected:
        """Create rejected message from validation result.

        Args:
            result: Validation result
            context: Validation context
            routing: Routing decision
            rejection_reason: Reason for rejection

        Returns:
            NewsRejected message
        """
        original_msg_dict = self._create_original_message_dict(context)

        return NewsRejected(
            article_id=result.article_id,
            url=context.raw_message.url,
            source=context.raw_message.source,
            rejected_at=datetime.utcnow().isoformat(),
            validation_score=result.validation_score,
            rejection_reason=rejection_reason,
            error_codes=[],
            error_details={},
            retry_count=0,
            original_message=original_msg_dict,
            trace_id=result.trace_id,
            validation_job_id=result.job_id,
            schema_version="1.0.0",
        )

    async def _route_result(self, result, context) -> None:
        """Route validation result to appropriate topic.

        Args:
            result: Validation result
            context: Validation context
        """
        try:
            routing = self._determine_routing(result)

            if routing == "accept":
                await self._handle_accepted_result(result, context)
            else:
                await self._handle_rejected_result(result, context, routing)

            self.producer.flush()

        except Exception as e:
            logger.error(f"Result routing error: {e}", exc_info=True)

    async def _handle_accepted_result(self, result, context) -> None:
        """Handle accepted validation result.

        Args:
            result: Validation result
            context: Validation context
        """
        validated_msg = self._create_validated_message(result, context)
        self.producer.publish_validated(validated_msg)
        self.metrics.messages_validated_total.inc()
        logger.info(f"[VALIDATED] Article validated and published to news_validated: {validated_msg.url}")

        await self.audit_log.log_validation(
            result.article_id,
            result.trace_id,
            result.job_id,
            result.validation_score,
            True,
            result.errors,
            result.warnings,
        )

    async def _handle_rejected_result(self, result, context, routing: str) -> None:
        """Handle rejected validation result.

        Args:
            result: Validation result
            context: Validation context
            routing: Routing decision
        """
        rejection_reason = self._get_rejection_reason(result, routing)
        rejected_msg = self._create_rejected_message(result, context, routing, rejection_reason)

        self.producer.publish_rejected(rejected_msg)
        self.metrics.messages_rejected_total.inc()
        logger.info(f"[{routing.upper()}] Article routed to news_rejected: {rejected_msg.url} - Reason: {rejected_msg.rejection_reason}")

        await self.audit_log.log_rejection(
            result.article_id,
            result.trace_id,
            result.job_id,
            rejected_msg.rejection_reason,
            rejected_msg.error_codes,
        )

    async def run(self) -> None:
        """Run validator service."""
        try:
            await self.initialize()

            logger.info("Validator service started")

            while True:
                # Update consumer lag metrics
                lag_dict = self.consumer.get_consumer_lag()
                self.backpressure.update_consumer_lag(lag_dict)

                # Update metrics
                for partition, lag in lag_dict.items():
                    self.metrics.consumer_lag.labels(partition=str(partition)).set(lag)

                # Apply backpressure if needed
                await self.backpressure.apply_throttle()

                # Process message
                await self.process_message()
                await asyncio.sleep(0.1)

        except KeyboardInterrupt:
            logger.info("Validator service stopped")
        except Exception as e:
            logger.error(f"Service error: {e}")
        finally:
            await self.shutdown()

    def get_health_status(self) -> dict:
        """
        Get health status of the service.

        Returns:
            dict: Health status with component details.
        """
        backpressure_status = self.backpressure.get_status()

        return {
            "status": "healthy",
            "service": "ingest-validator",
            "version": self.config.service_version,
            "components": {
                "kafka_consumer": "healthy",
                "kafka_producer": "healthy",
                "pipeline": "healthy",
            },
            "backpressure": backpressure_status,
        }

    def is_ready(self) -> bool:
        """
        Check if service is ready to handle requests.

        Returns:
            bool: True if ready.
        """
        # Service is ready if all critical components are initialized
        return (
            self.consumer is not None
            and self.producer is not None
            and self.pipeline is not None
        )

    def replay_from_offset(self, partition: int, offset: int) -> dict:
        """
        Replay messages from specific offset.

        Args:
            partition: Partition number
            offset: Offset to start replay from

        Returns:
            dict: Replay status information
        """
        try:
            current_offset = self.consumer.get_current_offset(partition)
            self.consumer.seek_to_offset(partition, offset)
            logger.info(
                f"Replay initiated: partition={partition}, "
                f"from_offset={offset}, previous_offset={current_offset}"
            )
            self.metrics.replay_initiated.inc()
            return {
                "status": "success",
                "partition": partition,
                "replay_offset": offset,
                "previous_offset": current_offset,
                "message": f"Replay started from offset {offset}",
            }
        except Exception as e:
            logger.error(f"Replay failed: {e}")
            self.metrics.replay_failed.inc()
            return {
                "status": "error",
                "partition": partition,
                "error": str(e),
                "message": f"Replay failed: {e}",
            }

    def get_partition_offsets(self, partition: int) -> dict:
        """
        Get current and committed offsets for a partition.

        Args:
            partition: Partition number

        Returns:
            dict: Offset information
        """
        try:
            current_offset = self.consumer.get_current_offset(partition)
            return {
                "status": "success",
                "partition": partition,
                "current_offset": current_offset,
            }
        except Exception as e:
            logger.error(f"Failed to get partition offsets: {e}")
            return {
                "status": "error",
                "partition": partition,
                "error": str(e),
            }

    async def validate_batch(self, messages: list) -> dict:
        """
        Validate a batch of messages.

        Args:
            messages: List of NewsRaw messages to validate

        Returns:
            dict: Batch validation results with validated and rejected counts
        """
        if not messages:
            return {
                "status": "success",
                "total_messages": 0,
                "validated_count": 0,
                "rejected_count": 0,
                "results": [],
            }

        try:
            results = []
            validated_count = 0
            rejected_count = 0

            for msg in messages:
                try:
                    # Process each message through the pipeline
                    trace_id = generate_trace_id()
                    set_trace_id(trace_id)

                    # Create validation context
                    context = self.pipeline.create_context(msg)
                    context.trace_id = trace_id

                    # Execute pipeline
                    result = await self.pipeline.execute(context)

                    # Route based on validation score
                    if result.validation_score >= self.config.validation.score_accept:
                        routing = "validated"
                        validated_count += 1
                        validated_msg = NewsValidated(
                            article_id=msg.article_id,
                            canonical_url=msg.url,
                            title=msg.title,
                            body=msg.body,
                            url=msg.url,
                            source=msg.source,
                            language=result.language,
                            language_confidence=result.language_confidence,
                            language_detection_method=result.language_detection_method,
                            source_published_at_raw=msg.published_at,
                            source_published_at_utc=result.source_published_at_utc,
                            ingested_at=datetime.utcnow().isoformat() + "Z",
                            validated_at=datetime.utcnow().isoformat() + "Z",
                            country=result.country,
                            checksum=msg.checksum,
                            validation_score=result.validation_score,
                            validation_details=result.validation_details,
                            schema_version="1.0.0",
                            ingest_job_id=msg.ingest_job_id,
                            validation_job_id=str(ULID()),
                            trace_id=trace_id,
                            publisher_id=result.publisher_id,
                        )
                        self.producer.publish_validated(validated_msg)
                        results.append(
                            {
                                "article_id": msg.article_id,
                                "status": "validated",
                                "validation_score": result.validation_score,
                            }
                        )
                    else:
                        routing = "rejected"
                        rejected_count += 1
                        rejected_msg = NewsRejected(
                            article_id=msg.article_id,
                            url=msg.url,
                            source=msg.source,
                            rejected_at=datetime.utcnow().isoformat() + "Z",
                            validation_score=result.validation_score,
                            rejection_reason=result.rejection_reason or "Low validation score",
                            error_codes=result.error_codes,
                            error_details=result.error_details,
                            retry_count=0,
                            original_message=msg.dict(),
                            trace_id=trace_id,
                            validation_job_id=str(ULID()),
                            schema_version="1.0.0",
                        )
                        self.producer.publish_rejected(rejected_msg)
                        results.append(
                            {
                                "article_id": msg.article_id,
                                "status": "rejected",
                                "validation_score": result.validation_score,
                                "reason": result.rejection_reason,
                            }
                        )

                    self.metrics.messages_processed.inc()

                except Exception as e:
                    logger.error(f"Error processing message in batch: {e}")
                    rejected_count += 1
                    results.append(
                        {
                            "article_id": msg.article_id if hasattr(msg, "article_id") else "unknown",
                            "status": "error",
                            "error": str(e),
                        }
                    )

            logger.info(
                f"Batch validation complete: total={len(messages)}, "
                f"validated={validated_count}, rejected={rejected_count}"
            )

            return {
                "status": "success",
                "total_messages": len(messages),
                "validated_count": validated_count,
                "rejected_count": rejected_count,
                "results": results,
            }

        except Exception as e:
            logger.error(f"Batch validation failed: {e}")
            return {
                "status": "error",
                "total_messages": len(messages),
                "error": str(e),
                "message": f"Batch validation failed: {e}",
            }

    async def shutdown(self) -> None:
        """Shutdown service."""
        try:
            # Commit any remaining messages in batch
            if self.message_batch:
                logger.info(f"Committing {len(self.message_batch)} remaining messages before shutdown")
                await self._commit_batch()

            self.consumer.close()
            self.producer.close()
            await self.dedup_client.close()
            self.cache_manager.close()
            await self.source_registry.close()
            await self.audit_log.close()
            logger.info("Validator service shutdown complete")
        except Exception as e:
            logger.error(f"Shutdown error: {e}")
