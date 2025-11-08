"""
Label Reconciliation Service for Predictor Online Inference Service.

Consumes ground-truth updates from Kafka, matches with predictions,
and updates reconciliation status in PostgreSQL.
"""

import logging
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime

from ..clients.kafka_consumer import KafkaConsumerClient
from ..clients.postgres_client import PostgresClient
from ..validation.prediction_validator import PredictionValidator
from ..config import Config
from ..exceptions import KafkaError, PostgresError
from ..utils.trace import trace_span
from ..metrics import MetricsCollector

logger = logging.getLogger(__name__)


class LabelReconciliationService:
    """
    Service for reconciling predictions with ground-truth labels.
    
    Consumes ground_truth topic, matches labels with predictions,
    updates reconciliation_status, and tracks coverage rate.
    """
    
    def __init__(
        self,
        config: Config,
        kafka_consumer: KafkaConsumerClient,
        postgres_client: PostgresClient,
        prediction_validator: PredictionValidator,
        metrics: MetricsCollector
    ):
        """
        Initialize label reconciliation service.
        
        Args:
            config: Service configuration
            kafka_consumer: Kafka consumer client
            postgres_client: PostgreSQL client
            prediction_validator: Prediction validator
            metrics: Metrics collector
        """
        self.config = config
        self.kafka_consumer = kafka_consumer
        self.postgres_client = postgres_client
        self.prediction_validator = prediction_validator
        self.metrics = metrics
        self._running = False
        self._reconciliation_count = 0
        self._total_predictions = 0
        
        logger.info("Initialized LabelReconciliationService")
    
    async def start(self) -> None:
        """Start the label reconciliation service."""
        self._running = True
        
        logger.info("Starting LabelReconciliationService")
        
        try:
            await self.consume_ground_truth_updates()
        except Exception as e:
            logger.error(
                "LabelReconciliationService failed",
                extra={"error": str(e)},
                exc_info=True
            )
            raise
    
    async def stop(self) -> None:
        """Stop the label reconciliation service."""
        self._running = False
        
        logger.info("Stopping LabelReconciliationService")
    
    @trace_span("label_reconciliation_service.consume_ground_truth_updates")
    async def consume_ground_truth_updates(self) -> None:
        """
        Consume ground-truth updates from Kafka.
        
        Continuously polls ground_truth topic and processes labels.
        """
        logger.info("Starting to consume ground-truth updates")
        
        try:
            while self._running:
                # Poll for messages
                messages = await self.kafka_consumer.consume_batch(
                    topic=self.config.kafka.ground_truth_topic,
                    batch_size=100,
                    timeout_ms=1000
                )
                
                if not messages:
                    await asyncio.sleep(0.1)
                    continue
                
                logger.debug(
                    f"Received {len(messages)} ground-truth messages"
                )
                
                # Process each message
                for message in messages:
                    try:
                        await self._process_ground_truth_message(message)
                    except Exception as e:
                        logger.error(
                            "Failed to process ground-truth message",
                            extra={
                                "message_key": message.get("key"),
                                "error": str(e)
                            },
                            exc_info=True
                        )
                
                # Commit offsets
                await self.kafka_consumer.commit()
                
        except Exception as e:
            logger.error(
                "Failed to consume ground-truth updates",
                extra={"error": str(e)},
                exc_info=True
            )
            raise KafkaError(
                message=f"Failed to consume ground-truth updates: {str(e)}",
                details={}
            ) from e
    
    async def _process_ground_truth_message(
        self,
        message: Dict[str, Any]
    ) -> None:
        """
        Process a single ground-truth message.
        
        Args:
            message: Ground-truth message from Kafka
        """
        try:
            # Extract label data
            group_id = message.get("group_id")
            label_realized = message.get("label_realized")
            label_confidence = message.get("label_confidence")
            label_source = message.get("label_source")
            trace_id = message.get("trace_id")
            
            if not group_id:
                logger.warning("Ground-truth message missing group_id")
                return
            
            logger.debug(
                "Processing ground-truth label",
                extra={
                    "group_id": group_id,
                    "label_realized": label_realized,
                    "label_confidence": label_confidence,
                    "label_source": label_source,
                    "trace_id": trace_id
                }
            )
            
            # Fetch corresponding prediction from PostgreSQL
            prediction = await self._fetch_prediction(group_id, trace_id)
            
            if not prediction:
                logger.warning(
                    "No prediction found for ground-truth label",
                    extra={"group_id": group_id, "trace_id": trace_id}
                )
                return
            
            # Compare prediction with label
            validation_result = self.prediction_validator.compare_prediction_with_label(
                group_id=group_id,
                predicted_realized=prediction["predicted_realized"],
                predicted_confidence=prediction["predicted_confidence"],
                label_realized=label_realized,
                label_confidence=label_confidence,
                trace_id=trace_id
            )
            
            # Update reconciliation status in PostgreSQL
            await self._update_reconciliation_status(
                group_id=group_id,
                is_correct=validation_result["is_correct"],
                label_realized=label_realized,
                label_confidence=label_confidence,
                label_source=label_source,
                trace_id=trace_id
            )
            
            # Update metrics
            self._reconciliation_count += 1
            self.metrics.increment_label_reconciliation_total()
            
            logger.info(
                "Reconciled prediction with label",
                extra={
                    "group_id": group_id,
                    "is_correct": validation_result["is_correct"],
                    "trace_id": trace_id
                }
            )
            
        except Exception as e:
            logger.error(
                "Failed to process ground-truth message",
                extra={
                    "message": message,
                    "error": str(e)
                },
                exc_info=True
            )
            raise
    
    async def _fetch_prediction(
        self,
        group_id: str,
        trace_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch prediction from PostgreSQL.
        
        Args:
            group_id: Semantic group ID
            trace_id: Trace ID for correlation
            
        Returns:
            Prediction record or None if not found
        """
        try:
            query = """
            SELECT 
                group_id,
                predicted_realized,
                predicted_confidence,
                model_version,
                created_at
            FROM predictions
            WHERE group_id = $1
            ORDER BY created_at DESC
            LIMIT 1
            """
            
            result = await self.postgres_client.execute_query(
                query,
                [group_id],
                trace_id=trace_id
            )
            
            if result:
                return dict(result[0])
            
            return None
            
        except Exception as e:
            logger.error(
                "Failed to fetch prediction",
                extra={
                    "group_id": group_id,
                    "error": str(e),
                    "trace_id": trace_id
                },
                exc_info=True
            )
            return None
    
    async def _update_reconciliation_status(
        self,
        group_id: str,
        is_correct: bool,
        label_realized: bool,
        label_confidence: float,
        label_source: str,
        trace_id: Optional[str] = None
    ) -> None:
        """
        Update reconciliation status in PostgreSQL.
        
        Args:
            group_id: Semantic group ID
            is_correct: Whether prediction was correct
            label_realized: Ground-truth label
            label_confidence: Label confidence
            label_source: Label source
            trace_id: Trace ID for correlation
        """
        try:
            query = """
            UPDATE predictions
            SET 
                reconciliation_status = $2,
                label_realized = $3,
                label_confidence = $4,
                label_source = $5,
                reconciled_at = $6
            WHERE group_id = $1
            """
            
            reconciliation_status = "correct" if is_correct else "incorrect"
            reconciled_at = datetime.now()
            
            await self.postgres_client.execute_query(
                query,
                [
                    group_id,
                    reconciliation_status,
                    label_realized,
                    label_confidence,
                    label_source,
                    reconciled_at
                ],
                trace_id=trace_id
            )
            
            logger.debug(
                "Updated reconciliation status",
                extra={
                    "group_id": group_id,
                    "reconciliation_status": reconciliation_status,
                    "trace_id": trace_id
                }
            )
            
        except Exception as e:
            logger.error(
                "Failed to update reconciliation status",
                extra={
                    "group_id": group_id,
                    "error": str(e),
                    "trace_id": trace_id
                },
                exc_info=True
            )
            raise PostgresError(
                message=f"Failed to update reconciliation status: {str(e)}",
                details={"group_id": group_id}
            ) from e
    
    def get_reconciliation_coverage_rate(self) -> float:
        """
        Get reconciliation coverage rate.
        
        Returns:
            Coverage rate [0, 1]
        """
        if self._total_predictions == 0:
            return 0.0
        
        coverage_rate = self._reconciliation_count / self._total_predictions
        
        logger.debug(
            "Calculated reconciliation coverage rate",
            extra={
                "coverage_rate": coverage_rate,
                "reconciliation_count": self._reconciliation_count,
                "total_predictions": self._total_predictions
            }
        )
        
        return coverage_rate

