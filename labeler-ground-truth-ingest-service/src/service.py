"""Main labeler service."""

import asyncio
import signal
import sys
import time
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from ulid import ULID

from src.config import config
from src.clients.api_clients import ACLEDFetcher, GDELTFetcher, BinanceFetcher, CCXTFetcher
from src.clients.kafka_producer import KafkaProducerClient
from src.clients.kafka_consumer import SemanticGroupConsumer
from src.storage.delta_lake_writer import DeltaLakeWriter
from src.storage.postgres_writer import PostgreSQLWriter
from src.storage.audit_logger import AuditLogger
from src.storage.outbox import OutboxManager
from src.reconciliation.reconciler import LabelReconciler
from src.validation.label_validator import LabelValidator, LicenseChecker, FreshnessValidator
from src.validation.deduplication import DeduplicationEngine
from src.validation.drift_detector import DriftDetector
from src.utils.trace import get_logger, TimedOperation
from src.metrics import get_metrics
from src.exceptions import LabelError
from src.health import HealthChecker


logger = get_logger(__name__, config.logging.log_level)
metrics = get_metrics(config.metrics.prometheus_port)

# TEMP_LIMIT for debugging - set to None to process all labels
TEMP_LIMIT = None  # Process all labels


class LabelerService:
    """Main labeler service."""

    def __init__(self):
        """Initialize labeler service."""
        self.service_name = config.service.service_name
        self.service_version = config.service.service_version

        # Initialize components
        self.acled_fetcher = ACLEDFetcher()
        self.gdelt_fetcher = GDELTFetcher()
        self.binance_fetcher = BinanceFetcher()
        self.ccxt_fetcher = CCXTFetcher()  # Fallback for crypto data

        # Cache for GDELT labels - allows re-reconciliation when new semantic groups arrive
        self.cached_gdelt_labels: List[Dict[str, Any]] = []

        self.kafka_producer = KafkaProducerClient()
        self.kafka_consumer = SemanticGroupConsumer()  # Add Kafka consumer for semantic groups
        self.delta_lake_writer = DeltaLakeWriter()
        self.postgres_writer = PostgreSQLWriter()

        # Initialize outbox manager with postgres writer
        self.outbox_manager = OutboxManager(self.postgres_writer)

        self.reconciler = LabelReconciler()
        self.validator = LabelValidator()
        self.license_checker = LicenseChecker()
        self.freshness_validator = FreshnessValidator()
        # Deduplication engine will be initialized with db_pool after PostgreSQL connects
        self.deduplication_engine: Optional[DeduplicationEngine] = None
        self.drift_detector = DriftDetector()
        self.audit_logger = AuditLogger()

        # Initialize health checker
        self.health_checker = HealthChecker()

        self.running = False
        self.semantic_groups: List[Dict[str, Any]] = []
        self.semantic_groups_task: Optional[asyncio.Task] = None  # Background task for consuming semantic groups
        self.btc_fetch_task: Optional[asyncio.Task] = None  # Background task for fetching BTC data

        logger.info(
            f"Labeler service initialized",
            operation="init",
            service_name=self.service_name,
            version=self.service_version
        )

    async def start(self):
        """Start service."""
        logger.info(
            "Starting labeler service",
            operation="start"
        )

        try:
            # Connect to Kafka producer
            await self.kafka_producer.connect()

            # Connect to Kafka consumer for semantic groups
            await self.kafka_consumer.connect()

            # Connect to PostgreSQL
            await self.postgres_writer.connect()
            await self.postgres_writer._ensure_tables()

            # Initialize deduplication engine with database pool for persistence
            self.deduplication_engine = DeduplicationEngine(db_pool=self.postgres_writer.pool)
            await self.deduplication_engine.load_cache_from_db()

            # Initialize outbox table
            await self.outbox_manager.initialize()

            # Start background task to consume semantic groups from Kafka
            self.running = True
            self.semantic_groups_task = asyncio.create_task(self._consume_semantic_groups_background())
            logger.info(
                "Started background task to consume semantic groups from Kafka",
                operation="start"
            )

            # Start background task to fetch BTC data every 5 minutes
            self.btc_fetch_task = asyncio.create_task(self._fetch_btc_background())
            logger.info(
                "Started background task to fetch BTC data every 5 minutes",
                operation="start"
            )

            # Initialize audit logger with database pool
            self.audit_logger.db_pool = self.postgres_writer.pool
            await self.audit_logger.ensure_audit_table()

            # Set health checker dependencies
            self.health_checker.set_dependencies(
                kafka_producer=self.kafka_producer,
                postgres_writer=self.postgres_writer,
                schema_registry_client=self.kafka_producer.schema_registry_client
            )

            # Start metrics server
            metrics.start_server()

            # Register signal handlers (skip on Windows)
            if sys.platform != "win32":
                loop = asyncio.get_event_loop()
                loop.add_signal_handler(signal.SIGTERM, lambda: asyncio.create_task(self.shutdown()))
                loop.add_signal_handler(signal.SIGINT, lambda: asyncio.create_task(self.shutdown()))

            self.running = True

            logger.info(
                "Labeler service started successfully",
                operation="start"
            )

        except Exception as e:
            logger.error(
                f"Failed to start labeler service: {str(e)}",
                operation="start",
                error_type=type(e).__name__
            )
            raise

    async def shutdown(self):
        """Shutdown service."""
        logger.info(
            "Shutting down labeler service",
            operation="shutdown"
        )

        self.running = False

        try:
            # Cancel background semantic groups consumer task
            if self.semantic_groups_task and not self.semantic_groups_task.done():
                self.semantic_groups_task.cancel()
                try:
                    await self.semantic_groups_task
                except asyncio.CancelledError:
                    logger.info(
                        "Background semantic groups consumer task cancelled",
                        operation="shutdown"
                    )

            # Cancel background BTC fetch task
            if self.btc_fetch_task and not self.btc_fetch_task.done():
                self.btc_fetch_task.cancel()
                try:
                    await self.btc_fetch_task
                except asyncio.CancelledError:
                    logger.info(
                        "Background BTC fetch task cancelled",
                        operation="shutdown"
                    )

            # Clean up outbox (published events older than 7 days)
            try:
                await self.outbox_manager.cleanup_published_events(days_old=7)
            except Exception as e:
                logger.warning(
                    f"Failed to cleanup outbox: {str(e)}",
                    operation="shutdown"
                )

            await self.kafka_producer.disconnect()
            await self.kafka_consumer.disconnect()
            await self.postgres_writer.disconnect()

            logger.info(
                "Labeler service shut down successfully",
                operation="shutdown"
            )

        except Exception as e:
            logger.error(
                f"Error during shutdown: {str(e)}",
                operation="shutdown",
                error_type=type(e).__name__
            )

    async def fetch_labels(self) -> Dict[str, List[Dict[str, Any]]]:
        """Fetch labels from all sources."""
        labels = {
            "acled": [],
            "gdelt": [],
            "binance": []
        }

        # ACLED is skipped due to persistent HTTP 403 "Access Denied" errors
        # GDELT is used as primary source for conflict events with NER-based country extraction
        logger.info(
            "Skipping ACLED source (HTTP 403 Access Denied)",
            operation="fetch_labels",
            source="ACLED",
            reason="ACLED API access denied - using GDELT as primary source"
        )

        try:
            # Check if GDELT fetch interval has elapsed (1 hour)
            gdelt_interval_seconds = config.gdelt.fetch_interval_hours * 3600
            if self.gdelt_fetcher.should_fetch(gdelt_interval_seconds):
                with TimedOperation(logger, "fetch_gdelt", source="GDELT") as op:
                    labels["gdelt"] = await self.gdelt_fetcher.fetch()
                    self.gdelt_fetcher.record_fetch_time()
                    # Cache the fetched labels for re-reconciliation when new semantic groups arrive
                    self.cached_gdelt_labels = labels["gdelt"]
                # Record metrics after context manager exits (duration_ms is set in __exit__)
                if op.duration_ms is not None:
                    metrics.record_fetch("GDELT", len(labels["gdelt"]), op.duration_ms / 1000)
            else:
                # Use cached GDELT labels if available (for re-reconciliation with new semantic groups)
                if self.cached_gdelt_labels:
                    labels["gdelt"] = self.cached_gdelt_labels
                    logger.info(
                        "Using cached GDELT labels for reconciliation",
                        operation="fetch_labels",
                        source="GDELT",
                        cached_count=len(self.cached_gdelt_labels),
                        interval_hours=config.gdelt.fetch_interval_hours
                    )
                else:
                    logger.debug(
                        "Skipping GDELT fetch - interval not elapsed and no cache available",
                        operation="fetch_labels",
                        source="GDELT",
                        interval_hours=config.gdelt.fetch_interval_hours
                    )

        except Exception as e:
            logger.error(
                f"Failed to fetch from GDELT: {str(e)}",
                operation="fetch_labels",
                source="GDELT",
                error_type=type(e).__name__
            )

        # Binance fetching is now handled by background task _fetch_btc_background()
        # This ensures BTC data is fetched every 5 minutes independent of GDELT processing
        logger.debug(
            "Binance fetch handled by background task",
            operation="fetch_labels",
            source="Binance"
        )

        logger.info(
            "Label fetching completed",
            operation="fetch_labels",
            acled_count=len(labels["acled"]),
            gdelt_count=len(labels["gdelt"]),
            binance_count=len(labels["binance"])
        )

        return labels

    def _enrich_label_fields(self, label: Dict[str, Any], source: str) -> Dict[str, Any]:
        """
        Enrich label with missing fields per design spec.

        Populates fields that are not provided by API fetchers:
        - label_source_license: License of the source API
        - label_source_url: URL to the source
        - last_license_check: Current timestamp
        - last_updated: Current timestamp
        - schema_version: Service version
        - source_confidence: Confidence from source API
        - time_window: Default time window for realization
        - realization_metric: Default metric for realization
        - threshold: Default threshold for realization
        """
        now = datetime.utcnow().isoformat() + "Z"

        # Set source-specific license information
        license_info = {
            "gdelt": {
                "license": "CC BY 4.0",
                "url": "https://www.gdeltproject.org"
            },
            "acled": {
                "license": "CC BY 4.0",
                "url": "https://www.acleddata.com"
            },
            "binance": {
                "license": "Proprietary",
                "url": "https://www.binance.com"
            },
            "coingecko": {
                "license": "CC BY 4.0",
                "url": "https://www.coingecko.com"
            },
            "ccxt": {
                "license": "MIT",
                "url": "https://ccxt.trade"
            }
        }

        source_lower = source.lower()
        license_data = license_info.get(source_lower, {
            "license": "Unknown",
            "url": label.get("source_url", "")
        })

        # Enrich label with missing fields
        enriched = label.copy()

        # Set license information if not already set
        if not enriched.get("label_source_license"):
            enriched["label_source_license"] = license_data.get("license")

        if not enriched.get("label_source_url"):
            enriched["label_source_url"] = license_data.get("url")

        # Set license check timestamp
        if not enriched.get("last_license_check"):
            enriched["last_license_check"] = now

        # Set last updated timestamp
        if not enriched.get("last_updated"):
            enriched["last_updated"] = now

        # Set schema version
        if not enriched.get("schema_version"):
            enriched["schema_version"] = self.service_version

        # Set source confidence (from API if available, otherwise use label_confidence)
        if not enriched.get("source_confidence"):
            enriched["source_confidence"] = enriched.get("label_confidence", 0.0)

        # Set time window for realization (default: 30 days)
        if not enriched.get("time_window"):
            enriched["time_window"] = "P30D"  # ISO 8601 duration: 30 days

        # Set realization metric based on source
        if not enriched.get("realization_metric"):
            if source_lower in ["gdelt", "acled"]:
                enriched["realization_metric"] = "event_occurrence"
            elif source_lower in ["binance", "coingecko", "ccxt"]:
                enriched["realization_metric"] = "price_movement"
            else:
                enriched["realization_metric"] = "unknown"

        # Set threshold based on source
        if not enriched.get("threshold"):
            if source_lower in ["binance", "coingecko", "ccxt"]:
                # For crypto: 5% price movement threshold
                enriched["threshold"] = 5.0
            else:
                # For events: confidence threshold
                enriched["threshold"] = 0.7

        return enriched

    async def validate_labels(
        self,
        labels: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, tuple]:
        """Validate labels from all sources."""
        results = {}

        for source, source_labels in labels.items():
            try:
                with TimedOperation(logger, "validate_labels", source=source) as op:
                    valid, invalid = await self.validator.validate_batch(source_labels, source.upper())

                    # Enrich valid labels with missing fields
                    enriched_valid = [self._enrich_label_fields(label, source) for label in valid]

                    # Deduplication happens AFTER validation in process_labels, not here
                    # This keeps validation and deduplication as separate concerns per architecture

                    # Detect drift in label confidence
                    drift_detected, drift_info = self.drift_detector.detect_confidence_drift(source.upper(), enriched_valid)
                    if drift_detected:
                        logger.warning(
                            f"Drift detected in {source}",
                            operation="validate_labels",
                            drift_info=drift_info
                        )

                    # Detect volume drift
                    vol_drift, vol_info = self.drift_detector.detect_volume_drift(source.upper(), len(enriched_valid))
                    if vol_drift:
                        logger.warning(
                            f"Volume drift detected in {source}",
                            operation="validate_labels",
                            vol_info=vol_info
                        )

                    results[source] = (enriched_valid, invalid)

                    # Log to audit trail
                    if op.duration_ms is not None:
                        await self.audit_logger.log_validation(
                            source=source.upper(),
                            total_labels=len(source_labels),
                            valid_labels=len(enriched_valid),
                            invalid_labels=len(invalid),
                            duration_ms=op.duration_ms
                        )

            except Exception as e:
                logger.error(
                    f"Validation failed for {source}: {str(e)}",
                    operation="validate_labels",
                    source=source,
                    error_type=type(e).__name__
                )

        return results

    async def reconcile_labels(
        self,
        valid_labels: Dict[str, List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """Reconcile labels with semantic groups."""
        all_reconciled = []

        for source, labels in valid_labels.items():
            try:
                with TimedOperation(logger, "reconcile_labels", source=source) as op:
                    reconciled = await self.reconciler.reconcile_batch(labels, self.semantic_groups)
                    all_reconciled.extend(reconciled)

                    # Only write if there are reconciled results
                    if reconciled:
                        # Write reconciliation results to Delta Lake
                        logger.debug(
                            f"About to write {len(reconciled)} reconciliation results to Delta Lake",
                            operation="reconcile_labels",
                            source=source,
                            result_count=len(reconciled)
                        )
                        await self.delta_lake_writer.write_reconciliation_results(reconciled)
                        logger.debug(
                            f"Successfully wrote reconciliation results to Delta Lake",
                            operation="reconcile_labels",
                            source=source
                        )

                        # Write reconciliation log to PostgreSQL
                        logger.debug(
                            f"About to generate batch_id",
                            operation="reconcile_labels",
                            source=source
                        )
                        batch_id = str(uuid.uuid4())
                        logger.debug(
                            f"Generated batch_id: {batch_id}",
                            operation="reconcile_labels",
                            source=source,
                            batch_id=batch_id
                        )
                        logger.debug(
                            f"About to write {len(reconciled)} reconciliation logs to PostgreSQL",
                            operation="reconcile_labels",
                            source=source,
                            batch_id=batch_id,
                            result_count=len(reconciled)
                        )
                        await self.postgres_writer.write_reconciliation_log(batch_id, reconciled)
                        logger.debug(
                            f"Successfully wrote reconciliation logs to PostgreSQL",
                            operation="reconcile_labels",
                            source=source,
                            batch_id=batch_id
                        )

                    # Log to audit trail
                    if op.duration_ms is not None:
                        logger.debug(
                            f"About to log reconciliation to audit trail",
                            operation="reconcile_labels",
                            source=source,
                            total_labels=len(labels),
                            reconciled_labels=len(reconciled)
                        )
                        await self.audit_logger.log_reconciliation(
                            source=source.upper(),
                            total_labels=len(labels),
                            reconciled_labels=len(reconciled),
                            duration_ms=op.duration_ms
                        )
                        logger.debug(
                            f"Successfully logged reconciliation to audit trail",
                            operation="reconcile_labels",
                            source=source
                        )

            except Exception as e:
                logger.error(
                    f"Reconciliation failed for {source}: {str(e)}",
                    operation="reconcile_labels",
                    source=source,
                    error_type=type(e).__name__
                )

        return all_reconciled

    async def _consume_semantic_groups_background(self):
        """Background task to continuously consume semantic groups from Kafka.

        This ensures the labeler always has the latest semantic groups for reconciliation,
        even when clustering creates new groups while labeler is running.
        """
        logger.info(
            "Starting background semantic groups consumer",
            operation="_consume_semantic_groups_background"
        )

        # SKIP initial load from PostgreSQL - only use Kafka messages
        # This ensures labeler only processes semantic groups from the current clustering run
        logger.info(
            "=== LABELER: Skipping PostgreSQL initial load - waiting for semantic groups from Kafka ===",
            operation="_consume_semantic_groups_background"
        )

        # Continuously consume from Kafka
        while self.running:
            try:
                # ACCUMULATE all semantic groups from multiple batches before triggering reconciliation
                # This ensures we get ALL 216+ groups from clustering, not just the first 10
                accumulated_groups = []
                consecutive_empty_batches = 0
                max_wait_seconds = 4 * 3600  # 4 hours (clustering interval)
                batch_start_time = time.time()

                logger.info(
                    "=== LABELER: Starting to accumulate semantic groups from Kafka ===",
                    operation="_consume_semantic_groups_background",
                    max_wait_hours=4
                )

                # Keep consuming until 4 hours have elapsed (clustering interval)
                # This allows the labeler to wait for the next clustering cycle
                while (time.time() - batch_start_time) < max_wait_seconds and self.running:
                    new_groups = await self.kafka_consumer.consume_batch(
                        timeout_ms=1000,  # 1 second timeout per batch
                        max_messages=1000 # Large batch size to get many groups at once
                    )

                    if new_groups:
                        accumulated_groups.extend(new_groups)
                        consecutive_empty_batches = 0  # Reset counter
                        elapsed_seconds = time.time() - batch_start_time
                        logger.info(
                            f"=== LABELER: Accumulated {len(new_groups)} groups (total: {len(accumulated_groups)}) ===",
                            operation="_consume_semantic_groups_background",
                            batch_size=len(new_groups),
                            total_accumulated=len(accumulated_groups),
                            elapsed_seconds=elapsed_seconds,
                            remaining_seconds=max_wait_seconds - elapsed_seconds
                        )
                    else:
                        consecutive_empty_batches += 1
                        elapsed_seconds = time.time() - batch_start_time
                        # Use DEBUG level to reduce log noise when waiting for semantic groups
                        logger.debug(
                            f"=== LABELER: Empty batch (consecutive: {consecutive_empty_batches}) ===",
                            operation="_consume_semantic_groups_background",
                            consecutive_empty=consecutive_empty_batches,
                            elapsed_seconds=elapsed_seconds,
                            remaining_seconds=max_wait_seconds - elapsed_seconds
                        )

                # If we accumulated any groups, replace the semantic groups list and trigger reconciliation
                if accumulated_groups:
                    # Log first group for debugging
                    sample_group = accumulated_groups[0]
                    logger.info(
                        f"=== LABELER: Sample semantic group from Kafka ===",
                        operation="_consume_semantic_groups_background",
                        group_id=sample_group.get('group_id'),
                        topic_label=sample_group.get('topic_label'),
                        article_count=sample_group.get('article_count'),
                        created_at=sample_group.get('created_at'),
                        keys=list(sample_group.keys())
                    )

                    # REPLACE semantic groups list with ALL accumulated groups from Kafka
                    # This ensures we use ALL semantic groups from the latest clustering run
                    self.semantic_groups = accumulated_groups

                    logger.info(
                        f"=== LABELER: Received {len(accumulated_groups)} new semantic groups from Kafka ===",
                        operation="_consume_semantic_groups_background",
                        new_groups=len(accumulated_groups),
                        total_groups=len(self.semantic_groups)
                    )

                    # Trigger reconciliation with ALL accumulated semantic groups
                    logger.info(
                        "=== LABELER: Triggering reconciliation after receiving new semantic groups ===",
                        operation="_consume_semantic_groups_background",
                        new_groups=len(accumulated_groups)
                    )
                    await self.process_labels()
                else:
                    # No groups accumulated, sleep before next iteration
                    await asyncio.sleep(5.0)

            except asyncio.CancelledError:
                logger.info(
                    "Background semantic groups consumer cancelled",
                    operation="_consume_semantic_groups_background"
                )
                break
            except Exception as e:
                logger.error(
                    f"Error consuming semantic groups from Kafka: {str(e)}",
                    operation="_consume_semantic_groups_background",
                    error_type=type(e).__name__
                )
                # Continue running despite errors
                await asyncio.sleep(5.0)

        logger.info(
            "Background semantic groups consumer stopped",
            operation="_consume_semantic_groups_background"
        )

    async def _fetch_btc_background(self):
        """Background task to continuously fetch BTC data every 5 minutes.

        This ensures BTC price data is always fresh and up-to-date for feature engineering,
        independent of the main GDELT/ACLED processing loop which can take 30+ minutes.
        """
        logger.info(
            "Starting background BTC fetcher",
            operation="_fetch_btc_background"
        )

        # Wait a bit before first fetch to allow service to fully initialize
        await asyncio.sleep(5.0)

        while self.running:
            try:
                # Fetch BTC data from Binance
                logger.info(
                    "Fetching BTC data from Binance",
                    operation="_fetch_btc_background"
                )

                with TimedOperation(logger, "fetch_binance", source="Binance") as op:
                    btc_labels = await self.binance_fetcher.fetch()
                    self.binance_fetcher.record_fetch_time()

                if op.duration_ms is not None:
                    metrics.record_fetch("Binance", len(btc_labels), op.duration_ms / 1000)

                logger.info(
                    f"Fetched {len(btc_labels)} BTC labels from Binance",
                    operation="_fetch_btc_background",
                    label_count=len(btc_labels)
                )

                # Validate BTC labels
                valid_btc, invalid_btc = await self.validator.validate_batch(btc_labels, "BINANCE")
                logger.info(
                    f"Validated BTC labels: {len(valid_btc)} valid, {len(invalid_btc)} invalid",
                    operation="_fetch_btc_background",
                    valid_count=len(valid_btc),
                    invalid_count=len(invalid_btc)
                )

                if valid_btc:
                    # Enrich BTC labels
                    enriched_btc = [self._enrich_label_fields(label, "BINANCE") for label in valid_btc]
                    logger.info(
                        f"Enriched {len(enriched_btc)} BTC labels",
                        operation="_fetch_btc_background",
                        label_count=len(enriched_btc)
                    )

                    # Deduplicate BTC labels to avoid sending same prices repeatedly
                    unique_btc, duplicate_btc = await self.deduplication_engine.deduplicate_batch(enriched_btc)
                    logger.info(
                        f"=== LABELER: Deduplicated BTC labels - {len(unique_btc)} unique, {len(duplicate_btc)} duplicates ===",
                        operation="_fetch_btc_background",
                        unique_count=len(unique_btc),
                        duplicate_count=len(duplicate_btc),
                        total_fetched=len(enriched_btc)
                    )

                    # Only process unique labels (skip duplicates)
                    if not unique_btc:
                        logger.info(
                            "=== LABELER: No new BTC prices to process - all are duplicates ===",
                            operation="_fetch_btc_background"
                        )
                        # Sleep for 5 minutes before next fetch
                        await asyncio.sleep(300)
                        continue

                    # Use unique_btc instead of enriched_btc for all subsequent operations
                    enriched_btc = unique_btc

                    # Write to storage (Delta Lake + PostgreSQL + Outbox + Kafka)
                    try:
                        # Write to Delta Lake
                        await self.delta_lake_writer.write_labels(enriched_btc)
                        logger.info(
                            f"Wrote {len(enriched_btc)} BTC labels to Delta Lake",
                            operation="_fetch_btc_background",
                            label_count=len(enriched_btc)
                        )

                        # Write to PostgreSQL btc_truth table
                        await self.postgres_writer.write_crypto_labels(enriched_btc)
                        logger.info(
                            f"Wrote {len(enriched_btc)} BTC labels to PostgreSQL btc_truth table",
                            operation="_fetch_btc_background",
                            label_count=len(enriched_btc)
                        )

                        # Write to outbox
                        outbox_batch = []
                        for label in enriched_btc:
                            event_id = label.get("event_id")
                            trace_id = label.get("trace_id")
                            outbox_batch.append({
                                "aggregate_id": event_id,
                                "aggregate_type": "btc_price",
                                "event_type": "label_created",
                                "payload": label,
                                "trace_id": trace_id
                            })

                        await self.outbox_manager.write_events_batch(outbox_batch)
                        logger.info(
                            f"Wrote {len(enriched_btc)} BTC labels to outbox",
                            operation="_fetch_btc_background",
                            label_count=len(enriched_btc)
                        )

                        # Produce to Kafka
                        await self.kafka_producer.produce_batch(enriched_btc)
                        logger.info(
                            f"Produced {len(enriched_btc)} BTC labels to Kafka",
                            operation="_fetch_btc_background",
                            label_count=len(enriched_btc)
                        )

                    except Exception as e:
                        logger.error(
                            f"Failed to write BTC labels to storage: {str(e)}",
                            operation="_fetch_btc_background",
                            error_type=type(e).__name__
                        )

                # Sleep for 5 minutes before next fetch
                logger.info(
                    "Sleeping for 5 minutes before next BTC fetch",
                    operation="_fetch_btc_background"
                )
                await asyncio.sleep(300)  # 5 minutes = 300 seconds

            except asyncio.CancelledError:
                logger.info(
                    "Background BTC fetcher cancelled",
                    operation="_fetch_btc_background"
                )
                break
            except Exception as e:
                logger.error(
                    f"Error fetching BTC data: {str(e)}",
                    operation="_fetch_btc_background",
                    error_type=type(e).__name__
                )
                # Continue running despite errors, but wait a bit before retrying
                await asyncio.sleep(60.0)  # Wait 1 minute before retry on error

        logger.info(
            "Background BTC fetcher stopped",
            operation="_fetch_btc_background"
        )

    async def consume_semantic_groups(self):
        """Fetch semantic groups from PostgreSQL (legacy method for compatibility).

        NOTE: This method is now deprecated. Semantic groups are continuously
        updated by the background task _consume_semantic_groups_background().
        This method is kept for backward compatibility but does nothing.
        """
        # Background task handles semantic groups updates
        logger.debug(
            f"consume_semantic_groups called (no-op, background task handles updates). Current count: {len(self.semantic_groups)}",
            operation="consume_semantic_groups",
            group_count=len(self.semantic_groups)
        )

    async def process_labels(self):
        """Main label processing pipeline - triggered when semantic groups are available."""
        try:
            logger.info(
                "=== LABELER: Starting label processing pipeline ===",
                operation="process_labels",
                semantic_groups_count=len(self.semantic_groups)
            )

            # Fetch labels
            labels = await self.fetch_labels()

            # Validate labels
            validation_results = await self.validate_labels(labels)

            # Extract valid labels and separate by source
            valid_labels = {}
            all_valid_labels = []
            crypto_labels = []  # Binance/CoinGecko labels (Dataset 7)
            event_labels = []   # GDELT/ACLED labels (Dataset 6)

            for source, (valid, invalid) in validation_results.items():
                valid_labels[source] = valid
                all_valid_labels.extend(valid)

                logger.info(
                    "Labels validated",
                    operation="process_labels",
                    source=source,
                    valid_count=len(valid),
                    invalid_count=len(invalid)
                )

                # Separate crypto labels from event labels
                # Per Architecture.md: Dataset 6 (ground_truth) vs Dataset 7 (btc_truth)
                if source in ["binance", "coingecko", "ccxt"]:
                    crypto_labels.extend(valid)
                else:
                    event_labels.extend(valid)

            logger.info(
                f"=== LABELER: Processing labels with {len(self.semantic_groups)} semantic groups ===",
                operation="process_labels",
                semantic_groups_count=len(self.semantic_groups),
                event_labels_count=len(event_labels),
                crypto_labels_count=len(crypto_labels)
            )

            # Deduplication for GDELT/event labels DISABLED
            # This allows GDELT labels to be reconciled multiple times with new semantic groups
            # Per user requirement: reconcile GDELT data each time without deduplication
            unique_event_labels = []
            unique_crypto_labels = []

            if event_labels:
                # Skip deduplication for GDELT/ACLED event labels
                # This allows all GDELT labels to be reconciled every time
                unique_event_labels = event_labels
                logger.info(
                    "=== LABELER: Processing all event labels without deduplication (allows multiple reconciliation) ===",
                    operation="process_labels",
                    event_label_count=len(event_labels),
                    source="gdelt/acled"
                )

            if crypto_labels:
                # Keep deduplication enabled for crypto labels (BTC prices)
                unique_crypto_labels, duplicates = await self.deduplication_engine.deduplicate_batch(crypto_labels)
                if len(duplicates) > 0:
                    logger.info(
                        "Crypto labels deduplicated (expected for price data)",
                        operation="process_labels",
                        duplicate_count=len(duplicates),
                        source="binance/coingecko"
                    )

            # Reconcile ONLY unique event labels (GDELT, ACLED)
            # Crypto labels are NOT reconciled per Architecture.md
            reconciliation_map = {}
            if unique_event_labels and self.semantic_groups:
                logger.info(
                    "=== LABELER: Starting reconciliation ===",
                    operation="process_labels",
                    event_labels_to_reconcile=len(unique_event_labels),
                    semantic_groups_available=len(self.semantic_groups)
                )

                # Reconcile all labels
                labels_to_reconcile = unique_event_labels

                # Create a dict with only event labels for reconciliation
                event_labels_by_source = {}
                for label in labels_to_reconcile:
                    source = label.get("label_source")
                    if source not in event_labels_by_source:
                        event_labels_by_source[source] = []
                    event_labels_by_source[source].append(label)

                reconciled_labels = await self.reconcile_labels(event_labels_by_source)

                # Create mapping of event_id -> group_id for reconciled labels
                for reconciled in reconciled_labels:
                    event_id = reconciled.get("label", {}).get("event_id")
                    group_id = reconciled.get("group_id")
                    if event_id and group_id:
                        reconciliation_map[event_id] = group_id

                # Log reconciliation summary
                logger.info(
                    "=== LABELER: Reconciliation completed ===",
                    operation="process_labels",
                    reconciled_count=len(reconciliation_map),
                    total_reconciled_results=len(reconciled_labels),
                    unreconciled_count=len(unique_event_labels) - len(reconciliation_map)
                )
            elif unique_event_labels:
                logger.warning(
                    "=== LABELER: No semantic groups available for reconciliation - waiting for clustering service ===",
                    operation="process_labels",
                    event_label_count=len(unique_event_labels)
                )

            # Enrich event labels with reconciliation results
            enriched_event_labels = []
            verification_timestamp = datetime.utcnow().isoformat()
            for label in unique_event_labels:
                event_id = label.get("event_id")
                group_id = reconciliation_map.get(event_id)
                label["group_id"] = group_id  # None if not reconciled
                label["verified_at"] = verification_timestamp  # Set verification timestamp
                # Map label_conflict to label_realized for PostgreSQL storage
                # label_conflict is set by ACLED/GDELT fetchers (0 or 1)
                # label_realized is the column name in ground_truth table (BOOLEAN type)
                label_conflict_value = label.get("label_conflict", 0)
                label["label_realized"] = bool(label_conflict_value)
                enriched_event_labels.append(label)



            # Deduplicate event labels before writing to storage
            # This prevents sending duplicate GDELT/ACLED labels to PostgreSQL and Kafka
            if enriched_event_labels:
                unique_event_labels_for_storage, duplicate_event_labels = await self.deduplication_engine.deduplicate_batch(enriched_event_labels)
                logger.info(
                    f"=== LABELER: Deduplicated event labels before storage - {len(unique_event_labels_for_storage)} unique, {len(duplicate_event_labels)} duplicates ===",
                    operation="process_labels",
                    unique_count=len(unique_event_labels_for_storage),
                    duplicate_count=len(duplicate_event_labels),
                    total_enriched=len(enriched_event_labels)
                )

                # Only process unique labels (skip duplicates)
                if not unique_event_labels_for_storage:
                    logger.info(
                        "=== LABELER: No new event labels to write - all are duplicates ===",
                        operation="process_labels"
                    )
                    # Continue to crypto labels processing
                else:
                    # Use unique labels for storage
                    enriched_event_labels = unique_event_labels_for_storage

            # Write event labels to storage using outbox pattern
            if enriched_event_labels:
                logger.info(
                    f"About to write {len(enriched_event_labels)} enriched event labels to storage",
                    operation="process_labels",
                    label_count=len(enriched_event_labels)
                )

                # Write to Delta Lake
                logger.info(
                    f"About to write {len(enriched_event_labels)} labels to Delta Lake",
                    operation="process_labels",
                    label_count=len(enriched_event_labels)
                )
                await self.delta_lake_writer.write_labels(enriched_event_labels)
                logger.info(
                    f"Successfully wrote {len(enriched_event_labels)} labels to Delta Lake",
                    operation="process_labels",
                    label_count=len(enriched_event_labels)
                )

                # Write to PostgreSQL ground_truth table
                logger.info(
                    f"About to write {len(enriched_event_labels)} labels to PostgreSQL",
                    operation="process_labels",
                    label_count=len(enriched_event_labels)
                )
                await self.postgres_writer.write_labels(enriched_event_labels)
                logger.info(
                    f"Successfully wrote {len(enriched_event_labels)} labels to PostgreSQL",
                    operation="process_labels",
                    label_count=len(enriched_event_labels)
                )

                # Write to outbox for atomic Kafka production using batch operation
                logger.info(
                    f"About to write {len(enriched_event_labels)} labels to outbox (batch)",
                    operation="process_labels",
                    label_count=len(enriched_event_labels)
                )
                outbox_start = time.time()

                # Prepare batch events for outbox
                outbox_batch = []
                for label in enriched_event_labels:
                    event_id = label.get("event_id")
                    group_id = label.get("group_id")
                    trace_id = label.get("trace_id")

                    outbox_batch.append({
                        "aggregate_id": group_id or event_id,
                        "aggregate_type": "semantic_group" if group_id else "event",
                        "event_type": "label_created",
                        "payload": label,
                        "trace_id": trace_id
                    })

                # Write all events in a single batch operation
                outbox_events = await self.outbox_manager.write_events_batch(outbox_batch)

                outbox_duration = time.time() - outbox_start
                logger.info(
                    f"Successfully wrote {len(enriched_event_labels)} labels to outbox",
                    operation="process_labels",
                    label_count=len(enriched_event_labels),
                    duration_seconds=outbox_duration
                )

                # Produce event labels to Kafka
                logger.info(
                    f"About to produce {len(enriched_event_labels)} labels to Kafka",
                    operation="process_labels",
                    label_count=len(enriched_event_labels)
                )
                try:
                    await self.kafka_producer.produce_batch(enriched_event_labels)
                    logger.info(
                        f"Successfully produced batch to Kafka",
                        operation="process_labels",
                        label_count=len(enriched_event_labels)
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to produce batch to Kafka: {str(e)}",
                        operation="process_labels",
                        error_type=type(e).__name__,
                        label_count=len(enriched_event_labels),
                        traceback=str(e)
                    )
                    # Continue with outbox marking even if Kafka production fails
                    # This ensures the outbox pattern is maintained

                # Mark outbox events as published
                for event_id in outbox_events:
                    try:
                        await self.outbox_manager.mark_published(event_id)
                    except Exception as e:
                        logger.warning(
                            f"Failed to mark outbox event as published: {str(e)}",
                            operation="process_labels",
                            event_id=event_id
                        )

            # Write crypto labels to btc_truth table (NO reconciliation, NO Kafka)
            if unique_crypto_labels:
                logger.info(
                    "Writing crypto labels to btc_truth table",
                    operation="process_labels",
                    label_count=len(unique_crypto_labels)
                )

                # Add verified_at timestamp to crypto labels
                for label in unique_crypto_labels:
                    label["verified_at"] = verification_timestamp

                # Per Architecture.md Dataset 7: Crypto labels go ONLY to PostgreSQL btc_truth table
                # They are NOT written to Delta Lake (different schema) and NOT published to Kafka
                await self.postgres_writer.write_crypto_labels(unique_crypto_labels)

            logger.info(
                "Label processing pipeline completed",
                operation="process_labels",
                event_labels=len(enriched_event_labels) if enriched_event_labels else 0,
                crypto_labels=len(crypto_labels) if crypto_labels else 0,
                total_labels=len(all_valid_labels)
            )

        except Exception as e:
            logger.error(
                f"Label processing pipeline failed: {str(e)}",
                operation="process_labels",
                error_type=type(e).__name__
            )

    async def run(self):
        """Run service - keep alive while background tasks handle processing.

        The service is now event-driven:
        - Background task consumes semantic groups from Kafka
        - When new semantic groups arrive, reconciliation is triggered automatically
        - No need for periodic polling loop
        """
        logger.info(
            "=== LABELER: Service running in event-driven mode - reconciliation triggered by semantic group messages ===",
            operation="run"
        )

        # Keep service alive while background tasks run
        try:
            while self.running:
                # Just sleep and let background tasks do the work
                await asyncio.sleep(60)
        except asyncio.CancelledError:
            logger.info(
                "=== LABELER: Service run loop cancelled ===",
                operation="run"
            )

        logger.warning(
            "=== LABELER: Service run loop exited - shutting down ===",
            operation="run",
            running=self.running
        )

    async def health_check(self) -> Dict[str, Any]:
        """Health check endpoint (/health)."""
        health = await self.health_checker.get_health()
        return {
            "status": health["status"],
            "service": self.service_name,
            "version": self.service_version,
            "running": self.running,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": health["checks"]
        }

    async def readiness_check(self) -> Dict[str, Any]:
        """Readiness check endpoint (/ready)."""
        ready = await self.health_checker.get_ready()
        return {
            "ready": ready["ready"],
            "service": self.service_name,
            "version": self.service_version,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": ready["checks"]
        }

    async def liveness_check(self) -> Dict[str, Any]:
        """Liveness check endpoint (/live)."""
        live = await self.health_checker.get_live()
        return {
            "alive": live["alive"],
            "service": self.service_name,
            "version": self.service_version,
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": live["uptime_seconds"]
        }

