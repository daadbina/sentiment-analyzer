"""
Message router for handling Kafka messages.
Routes messages to appropriate handlers based on topic.
"""

from typing import Dict, Any, Optional
import structlog

from ..kafka.message_validator import message_validator
from ..builders.node_builder import node_builder
from ..builders.relationship_builder import relationship_builder
from ..loaders.stream_loader import stream_loader
from ..exceptions import ValidationError, LoadError
from ..metrics import record_validation_failure

logger = structlog.get_logger(__name__)


class MessageRouter:
    """
    Routes Kafka messages to appropriate handlers.
    """

    def __init__(self):
        """Initialize message router."""
        self.handlers = {
            "semantic_groups": self.handle_semantic_groups,
            "entities_extracted": self.handle_entities_extracted,
            "predictions": self.handle_predictions,
            "news_canonical": self.handle_news_canonical,
        }

    def route_message(
        self,
        topic: str,
        message: Dict[str, Any],
        trace_id: Optional[str] = None,
    ) -> None:
        """
        Route message to appropriate handler.

        Args:
            topic: Kafka topic name
            message: Message payload
            trace_id: Trace ID for correlation
        """
        try:
            # Validate message
            message_validator.validate_message(topic, message)

            # Route to handler
            handler = self.handlers.get(topic)
            if handler:
                handler(message, trace_id=trace_id)
            else:
                logger.warning(
                    "no_handler_for_topic",
                    topic=topic,
                    trace_id=trace_id,
                )

        except ValidationError as e:
            record_validation_failure(
                validation_type=e.validation_type or "message_validation",
                failure_reason=e.message,
            )
            logger.error(
                "message_validation_failed",
                topic=topic,
                error=str(e),
                trace_id=trace_id,
            )
        except Exception as e:
            logger.error(
                "message_routing_failed",
                topic=topic,
                error=str(e),
                trace_id=trace_id,
            )

    def handle_semantic_groups(
        self,
        message: Dict[str, Any],
        trace_id: Optional[str] = None,
    ) -> None:
        """
        Handle semantic_groups message.
        Creates Group node and BELONGS_TO relationships.

        Args:
            message: Message from semantic_groups topic
            trace_id: Trace ID for correlation
        """
        try:
            # Build Group node
            group = node_builder.build_group_node(message)
            group_data = group.to_neo4j_properties()

            # Add Group node to stream
            stream_loader.add_node(
                node_label="Group",
                node_data=group_data,
                trace_id=trace_id,
            )

            # Create BELONGS_TO relationships for each article
            article_ids = message.get("article_ids", [])
            for article_id in article_ids:
                relationship_data = {
                    "from_id": article_id,
                    "to_id": group.id,
                    "properties": {"membership_score": 1.0},
                }

                stream_loader.add_relationship(
                    from_label="Article",
                    to_label="Group",
                    rel_type="BELONGS_TO",
                    relationship_data=relationship_data,
                    trace_id=trace_id,
                )

            logger.info(
                "semantic_groups_message_handled",
                group_id=group.id,
                article_count=len(article_ids),
                trace_id=trace_id,
            )

        except Exception as e:
            logger.error(
                "semantic_groups_handling_failed",
                error=str(e),
                trace_id=trace_id,
            )
            raise

    def handle_entities_extracted(
        self,
        message: Dict[str, Any],
        trace_id: Optional[str] = None,
    ) -> None:
        """
        Handle entities_extracted message.
        Creates Entity nodes and MENTIONS relationships.

        Args:
            message: Message from entities_extracted topic
            trace_id: Trace ID for correlation
        """
        try:
            article_id = message.get("article_id")

            # Build Entity nodes
            entities = node_builder.build_entity_nodes(message)

            for idx, entity in enumerate(entities):
                entity_data = entity.to_neo4j_properties()

                # Add Entity node to stream
                stream_loader.add_node(
                    node_label="Entity",
                    node_data=entity_data,
                    trace_id=trace_id,
                )

                # Create MENTIONS relationship
                relationship_data = {
                    "from_id": article_id,
                    "to_id": entity.id,
                    "properties": {"frequency": 1, "confidence": 1.0},
                }

                stream_loader.add_relationship(
                    from_label="Article",
                    to_label="Entity",
                    rel_type="MENTIONS",
                    relationship_data=relationship_data,
                    trace_id=trace_id,
                )

            logger.info(
                "entities_extracted_message_handled",
                article_id=article_id,
                entity_count=len(entities),
                trace_id=trace_id,
            )

        except Exception as e:
            logger.error(
                "entities_extracted_handling_failed",
                error=str(e),
                trace_id=trace_id,
            )
            raise

    def handle_predictions(
        self,
        message: Dict[str, Any],
        trace_id: Optional[str] = None,
    ) -> None:
        """
        Handle predictions message.
        Creates Prediction node and PREDICTS relationship.

        Args:
            message: Message from predictions topic
            trace_id: Trace ID for correlation
        """
        try:
            # Build Prediction node
            prediction = node_builder.build_prediction_node(message)
            prediction_data = prediction.to_neo4j_properties()

            # Add Prediction node to stream
            stream_loader.add_node(
                node_label="Prediction",
                node_data=prediction_data,
                trace_id=trace_id,
            )

            # Create PREDICTS relationship
            relationship_data = {
                "from_id": prediction.id,
                "to_id": prediction.group_id,
                "properties": {
                    "prediction_score": prediction.probability,
                    "confidence": prediction.confidence,
                },
            }

            stream_loader.add_relationship(
                from_label="Prediction",
                to_label="Group",
                rel_type="PREDICTS",
                relationship_data=relationship_data,
                trace_id=trace_id,
            )

            logger.info(
                "predictions_message_handled",
                prediction_id=prediction.id,
                group_id=prediction.group_id,
                trace_id=trace_id,
            )

        except Exception as e:
            logger.error(
                "predictions_handling_failed",
                error=str(e),
                trace_id=trace_id,
            )
            raise

    def handle_news_canonical(
        self,
        message: Dict[str, Any],
        trace_id: Optional[str] = None,
    ) -> None:
        """
        Handle news_canonical message.
        Creates Article node.

        Args:
            message: Message from news_canonical topic
            trace_id: Trace ID for correlation
        """
        try:
            # Build Article node
            article = node_builder.build_article_node(message)
            article_data = article.to_neo4j_properties()

            # Add Article node to stream
            stream_loader.add_node(
                node_label="Article",
                node_data=article_data,
                trace_id=trace_id,
            )

            logger.info(
                "news_canonical_message_handled",
                article_id=article.id,
                source=article.source,
                trace_id=trace_id,
            )

        except Exception as e:
            logger.error(
                "news_canonical_handling_failed",
                error=str(e),
                trace_id=trace_id,
            )
            raise


# Global message router instance
message_router = MessageRouter()

