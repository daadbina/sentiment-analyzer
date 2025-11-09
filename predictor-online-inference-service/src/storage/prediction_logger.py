"""
Prediction logger for storing predictions in PostgreSQL.

Provides audit trail for all predictions with full context.
Implements Rule R12 (Provenance Integrity).
"""

import logging
from typing import Any

from ..clients import KafkaProducerClient, PostgresClient
from ..exceptions import KafkaError, PostgresError
from ..utils.trace import trace_span

logger = logging.getLogger(__name__)


class PredictionLogger:
    """
    Logger for storing predictions in PostgreSQL and Kafka.

    Provides audit trail and publishes predictions to Kafka topic.
    """

    def __init__(
        self,
        postgres_client: PostgresClient,
        kafka_producer: KafkaProducerClient,
    ):
        """
        Initialize prediction logger.

        Args:
            postgres_client: PostgreSQL client instance
            kafka_producer: Kafka producer instance
        """
        self.postgres_client = postgres_client
        self.kafka_producer = kafka_producer

        logger.info("Initialized prediction logger")

    async def log_prediction(
        self,
        prediction: dict[str, Any],
        trace_id: str | None = None,
    ) -> None:
        """
        Log prediction to PostgreSQL and Kafka.

        Args:
            prediction: Prediction dictionary containing:
                - group_id: str
                - domain: str
                - prediction_probability: float
                - prediction_confidence: float
                - model_version: str
                - predicted_at: str (ISO format)
                - features: dict
            trace_id: Optional trace ID for distributed tracing
        """
        with trace_span(
            "log_prediction",
            attributes={
                "group_id": prediction.get("group_id"),
                "trace_id": trace_id,
            },
        ):
            # Store in PostgreSQL
            await self._store_in_postgres(prediction, trace_id)

            # Publish to Kafka
            await self._publish_to_kafka(prediction, trace_id)

    async def _store_in_postgres(
        self,
        prediction: dict[str, Any],
        trace_id: str | None = None,
    ) -> None:
        """
        Store prediction in PostgreSQL.

        Args:
            prediction: Prediction dictionary
            trace_id: Optional trace ID for distributed tracing
        """
        try:
            await self.postgres_client.store_prediction(
                group_id=prediction["group_id"],
                domain=prediction["domain"],
                prediction_probability=prediction["prediction_probability"],
                prediction_confidence=prediction["prediction_confidence"],
                model_version=prediction["model_version"],
                features=prediction.get("features", {}),
                trace_id=trace_id,
            )

            logger.debug(
                f"Prediction stored in PostgreSQL: group_id={prediction['group_id']}",
                extra={"trace_id": trace_id, "group_id": prediction["group_id"]},
            )

        except PostgresError as e:
            logger.error(
                f"Failed to store prediction in PostgreSQL: "
                f"group_id={prediction['group_id']}, error={e}",
                exc_info=True,
                extra={"trace_id": trace_id},
            )
            # Don't raise - continue with Kafka publish
        except Exception as e:
            logger.error(
                f"Unexpected error storing prediction: "
                f"group_id={prediction['group_id']}, error={e}",
                exc_info=True,
                extra={"trace_id": trace_id},
            )

    async def _publish_to_kafka(
        self,
        prediction: dict[str, Any],
        trace_id: str | None = None,
    ) -> None:
        """
        Publish prediction to Kafka topic.

        Args:
            prediction: Prediction dictionary
            trace_id: Optional trace ID for distributed tracing
        """
        try:
            # Import the schema
            from src.clients.kafka_producer import PREDICTION_SCHEMA

            await self.kafka_producer.produce_prediction(
                prediction=prediction,
                value_schema=PREDICTION_SCHEMA,
                trace_id=trace_id,
            )

            logger.debug(
                f"Prediction published to Kafka: group_id={prediction['group_id']}",
                extra={"trace_id": trace_id, "group_id": prediction["group_id"]},
            )

        except KafkaError as e:
            logger.error(
                f"Failed to publish prediction to Kafka: "
                f"group_id={prediction['group_id']}, error={e}",
                exc_info=True,
                extra={"trace_id": trace_id},
            )
            # Don't raise - prediction is already in PostgreSQL
        except Exception as e:
            logger.error(
                f"Unexpected error publishing prediction: "
                f"group_id={prediction['group_id']}, error={e}",
                exc_info=True,
                extra={"trace_id": trace_id},
            )
