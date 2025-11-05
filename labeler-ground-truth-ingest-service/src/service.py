"""Main labeler service."""

import asyncio
import signal
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional
from ulid import ULID

from src.config import config
from src.clients.api_clients import ACLEDFetcher, GDELTFetcher, BinanceFetcher, CCXTFetcher
from src.clients.kafka_producer import KafkaProducerClient
from src.storage.delta_lake_writer import DeltaLakeWriter
from src.storage.postgres_writer import PostgreSQLWriter
from src.storage.audit_logger import AuditLogger
from src.reconciliation.reconciler import LabelReconciler
from src.validation.label_validator import LabelValidator, LicenseChecker, FreshnessValidator
from src.validation.deduplication import DeduplicationEngine
from src.validation.drift_detector import DriftDetector
from src.utils.trace import get_logger, TimedOperation
from src.metrics import get_metrics
from src.exceptions import LabelError


logger = get_logger(__name__, config.logging.log_level)
metrics = get_metrics(config.metrics.prometheus_port)


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

        self.kafka_producer = KafkaProducerClient()
        self.delta_lake_writer = DeltaLakeWriter()
        self.postgres_writer = PostgreSQLWriter()

        self.reconciler = LabelReconciler()
        self.validator = LabelValidator()
        self.license_checker = LicenseChecker()
        self.freshness_validator = FreshnessValidator()
        self.deduplication_engine = DeduplicationEngine()
        self.drift_detector = DriftDetector()
        self.audit_logger = AuditLogger()

        self.running = False
        self.semantic_groups: List[Dict[str, Any]] = []

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
            # Connect to Kafka
            await self.kafka_producer.connect()

            # Connect to PostgreSQL
            await self.postgres_writer.connect()
            await self.postgres_writer._ensure_tables()

            # Initialize audit logger with database pool
            self.audit_logger.db_pool = self.postgres_writer.pool
            await self.audit_logger.ensure_audit_table()

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
            await self.kafka_producer.disconnect()
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

        try:
            # Fetch from ACLED
            with TimedOperation(logger, "fetch_acled", source="ACLED") as op:
                labels["acled"] = await self.acled_fetcher.fetch()
            # Record metrics after context manager exits (duration_ms is set in __exit__)
            if op.duration_ms is not None:
                metrics.record_fetch("ACLED", len(labels["acled"]), op.duration_ms / 1000)

        except Exception as e:
            logger.error(
                f"Failed to fetch from ACLED: {str(e)}",
                operation="fetch_labels",
                source="ACLED",
                error_type=type(e).__name__
            )

        try:
            # Fetch from GDELT
            with TimedOperation(logger, "fetch_gdelt", source="GDELT") as op:
                labels["gdelt"] = await self.gdelt_fetcher.fetch()
            # Record metrics after context manager exits (duration_ms is set in __exit__)
            if op.duration_ms is not None:
                metrics.record_fetch("GDELT", len(labels["gdelt"]), op.duration_ms / 1000)

        except Exception as e:
            logger.error(
                f"Failed to fetch from GDELT: {str(e)}",
                operation="fetch_labels",
                source="GDELT",
                error_type=type(e).__name__
            )

        try:
            # Fetch from Binance (primary)
            with TimedOperation(logger, "fetch_binance", source="Binance") as op:
                labels["binance"] = await self.binance_fetcher.fetch()
            # Record metrics after context manager exits (duration_ms is set in __exit__)
            if op.duration_ms is not None:
                metrics.record_fetch("Binance", len(labels["binance"]), op.duration_ms / 1000)

        except Exception as e:
            logger.error(
                f"Failed to fetch from Binance: {str(e)}",
                operation="fetch_labels",
                source="Binance",
                error_type=type(e).__name__
            )

            # Fallback to CCXT if Binance fails
            try:
                logger.info(
                    "Falling back to CCXT for crypto data",
                    operation="fetch_labels",
                    source="CCXT"
                )
                with TimedOperation(logger, "fetch_ccxt_fallback", source="CCXT") as op:
                    labels["binance"] = await self.ccxt_fetcher.fetch()
                # Record metrics after context manager exits
                if op.duration_ms is not None:
                    metrics.record_fetch("CCXT", len(labels["binance"]), op.duration_ms / 1000)

            except Exception as ccxt_error:
                logger.error(
                    f"CCXT fallback also failed: {str(ccxt_error)}",
                    operation="fetch_labels",
                    source="CCXT",
                    error_type=type(ccxt_error).__name__
                )

        logger.info(
            "Label fetching completed",
            operation="fetch_labels",
            acled_count=len(labels["acled"]),
            gdelt_count=len(labels["gdelt"]),
            binance_count=len(labels["binance"])
        )

        return labels

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

                    # Deduplicate valid labels
                    unique, duplicates = self.deduplication_engine.deduplicate_batch(valid)

                    # Detect drift in label confidence
                    drift_detected, drift_info = self.drift_detector.detect_confidence_drift(source.upper(), unique)
                    if drift_detected:
                        logger.warning(
                            f"Drift detected in {source}",
                            operation="validate_labels",
                            drift_info=drift_info
                        )

                    # Detect volume drift
                    vol_drift, vol_info = self.drift_detector.detect_volume_drift(source.upper(), len(unique))
                    if vol_drift:
                        logger.warning(
                            f"Volume drift detected in {source}",
                            operation="validate_labels",
                            vol_info=vol_info
                        )

                    results[source] = (unique, invalid + duplicates)

                    # Log to audit trail
                    if op.duration_ms is not None:
                        await self.audit_logger.log_validation(
                            source=source.upper(),
                            total_labels=len(source_labels),
                            valid_labels=len(unique),
                            invalid_labels=len(invalid) + len(duplicates),
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
                        await self.delta_lake_writer.write_reconciliation_results(reconciled)

                        # Write reconciliation log to PostgreSQL
                        batch_id = str(ULID())
                        await self.postgres_writer.write_reconciliation_log(batch_id, reconciled)

                    # Log to audit trail
                    if op.duration_ms is not None:
                        await self.audit_logger.log_reconciliation(
                            source=source.upper(),
                            total_labels=len(labels),
                            reconciled_labels=len(reconciled),
                            duration_ms=op.duration_ms
                        )

            except Exception as e:
                logger.error(
                    f"Reconciliation failed for {source}: {str(e)}",
                    operation="reconcile_labels",
                    source=source,
                    error_type=type(e).__name__
                )

        return all_reconciled

    async def process_labels(self):
        """Main label processing pipeline."""
        try:
            logger.info(
                "Starting label processing pipeline",
                operation="process_labels"
            )

            # Fetch labels
            labels = await self.fetch_labels()

            # Validate labels
            validation_results = await self.validate_labels(labels)

            # Extract valid labels
            valid_labels = {}
            for source, (valid, invalid) in validation_results.items():
                valid_labels[source] = valid

            # Reconcile labels
            reconciled_labels = await self.reconcile_labels(valid_labels)

            # Write to storage
            if reconciled_labels:
                # Write to Delta Lake
                await self.delta_lake_writer.write_labels(reconciled_labels)

                # Write to PostgreSQL
                await self.postgres_writer.write_labels(reconciled_labels)

                # Produce to Kafka
                await self.kafka_producer.produce_batch(reconciled_labels)

            logger.info(
                "Label processing pipeline completed",
                operation="process_labels",
                total_reconciled=len(reconciled_labels)
            )

        except Exception as e:
            logger.error(
                f"Label processing pipeline failed: {str(e)}",
                operation="process_labels",
                error_type=type(e).__name__
            )

    async def run(self):
        """Run service main loop."""
        logger.info(
            "Labeler service main loop started",
            operation="run"
        )

        while self.running:
            try:
                await self.process_labels()

                # Sleep before next iteration
                await asyncio.sleep(60)

            except Exception as e:
                logger.error(
                    f"Error in main loop: {str(e)}",
                    operation="run",
                    error_type=type(e).__name__
                )
                await asyncio.sleep(60)

    async def health_check(self) -> Dict[str, Any]:
        """Health check endpoint."""
        return {
            "status": "healthy" if self.running else "unhealthy",
            "service": self.service_name,
            "version": self.service_version,
            "timestamp": datetime.utcnow().isoformat()
        }

    async def readiness_check(self) -> Dict[str, Any]:
        """Readiness check endpoint."""
        ready = (
            self.running and
            self.kafka_producer.producer is not None and
            self.postgres_writer.pool is not None
        )

        return {
            "ready": ready,
            "service": self.service_name,
            "timestamp": datetime.utcnow().isoformat()
        }

