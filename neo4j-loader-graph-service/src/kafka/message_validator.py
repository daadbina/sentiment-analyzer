"""
Message validation for Kafka messages.
Validates message structure and required fields.
"""

from typing import Dict, Any, List, Optional
import structlog

from ..exceptions import ValidationError

logger = structlog.get_logger(__name__)


class MessageValidator:
    """
    Validates Kafka messages against expected schemas.
    """

    # Required fields for each topic
    REQUIRED_FIELDS = {
        "semantic_groups": [
            "group_id",
            "topic_label",
            "similarity_avg",
            "embedding_model",
            "embedding_version",
            "created_at",
            "article_ids",
        ],
        "entities_extracted": [
            "article_id",
            "entities",
        ],
        "predictions": [
            "prediction_id",
            "group_id",
            "probability",
            "confidence",
            "model_version",
            "domain",
            "predicted_at",
        ],
        "news_canonical": [
            "article_id",
            "canonical_url",
            "title",
            "source_published_at_utc",
            "source",
            "language",
            "checksum",
        ],
    }

    @staticmethod
    def validate_message(topic: str, message: Dict[str, Any]) -> None:
        """
        Validate message structure and required fields.
        
        Args:
            topic: Topic name
            message: Message dictionary
            
        Raises:
            ValidationError: If validation fails
        """
        if not message:
            raise ValidationError(
                message="Message is empty",
                validation_type="message_structure",
                details={"topic": topic},
            )

        # Check required fields
        required_fields = MessageValidator.REQUIRED_FIELDS.get(topic, [])
        missing_fields = [
            field for field in required_fields if field not in message
        ]

        if missing_fields:
            raise ValidationError(
                message=f"Missing required fields: {missing_fields}",
                validation_type="required_fields",
                failed_constraints=missing_fields,
                details={"topic": topic, "message_keys": list(message.keys())},
            )

        # Topic-specific validation
        if topic == "semantic_groups":
            MessageValidator._validate_semantic_groups(message)
        elif topic == "entities_extracted":
            MessageValidator._validate_entities_extracted(message)
        elif topic == "predictions":
            MessageValidator._validate_predictions(message)
        elif topic == "news_canonical":
            MessageValidator._validate_news_canonical(message)

        logger.debug("message_validated", topic=topic)

    @staticmethod
    def _validate_semantic_groups(message: Dict[str, Any]) -> None:
        """Validate semantic_groups message."""
        # Validate similarity_avg range
        similarity_avg = message.get("similarity_avg")
        if not isinstance(similarity_avg, (int, float)) or not 0.0 <= similarity_avg <= 1.0:
            raise ValidationError(
                message=f"similarity_avg must be between 0.0 and 1.0, got {similarity_avg}",
                validation_type="field_range",
                details={"field": "similarity_avg", "value": similarity_avg},
            )

        # Validate article_ids is a list
        article_ids = message.get("article_ids")
        if not isinstance(article_ids, list):
            raise ValidationError(
                message="article_ids must be a list",
                validation_type="field_type",
                details={"field": "article_ids", "type": type(article_ids).__name__},
            )

        # Validate group_id format (ULID: 26 characters or UUID: 36 characters)
        group_id = message.get("group_id")
        if not isinstance(group_id, str) or len(group_id) not in (26, 36):
            raise ValidationError(
                message=f"group_id must be 26-character ULID or 36-character UUID, got {group_id}",
                validation_type="field_format",
                details={"field": "group_id", "value": group_id},
            )

    @staticmethod
    def _validate_entities_extracted(message: Dict[str, Any]) -> None:
        """Validate entities_extracted message."""
        # Validate article_id format (ULID: 26 characters or UUID: 36 characters)
        article_id = message.get("article_id")
        if not isinstance(article_id, str) or len(article_id) not in (26, 36):
            raise ValidationError(
                message=f"article_id must be 26-character ULID or 36-character UUID, got {article_id}",
                validation_type="field_format",
                details={"field": "article_id", "value": article_id},
            )

        # Validate entities is a list
        entities = message.get("entities")
        if not isinstance(entities, list):
            raise ValidationError(
                message="entities must be a list",
                validation_type="field_type",
                details={"field": "entities", "type": type(entities).__name__},
            )

        # Validate each entity has required fields
        for idx, entity in enumerate(entities):
            required_entity_fields = ["entity_id", "name", "type"]
            missing_fields = [
                field for field in required_entity_fields if field not in entity
            ]
            if missing_fields:
                raise ValidationError(
                    message=f"Entity at index {idx} missing fields: {missing_fields}",
                    validation_type="entity_structure",
                    failed_constraints=missing_fields,
                    details={"entity_index": idx},
                )

    @staticmethod
    def _validate_predictions(message: Dict[str, Any]) -> None:
        """Validate predictions message."""
        # Validate prediction_id format (ULID: 26 characters)
        prediction_id = message.get("prediction_id")
        if not isinstance(prediction_id, str) or len(prediction_id) != 26:
            raise ValidationError(
                message=f"prediction_id must be 26-character ULID, got {prediction_id}",
                validation_type="field_format",
                details={"field": "prediction_id", "value": prediction_id},
            )

        # Validate group_id format (ULID: 26 characters or UUID: 36 characters)
        group_id = message.get("group_id")
        if not isinstance(group_id, str) or len(group_id) not in (26, 36):
            raise ValidationError(
                message=f"group_id must be 26-character ULID or 36-character UUID, got {group_id}",
                validation_type="field_format",
                details={"field": "group_id", "value": group_id},
            )

        # Validate probability range
        probability = message.get("probability")
        if not isinstance(probability, (int, float)) or not 0.0 <= probability <= 1.0:
            raise ValidationError(
                message=f"probability must be between 0.0 and 1.0, got {probability}",
                validation_type="field_range",
                details={"field": "probability", "value": probability},
            )

        # Validate confidence range
        confidence = message.get("confidence")
        if not isinstance(confidence, (int, float)) or not 0.0 <= confidence <= 1.0:
            raise ValidationError(
                message=f"confidence must be between 0.0 and 1.0, got {confidence}",
                validation_type="field_range",
                details={"field": "confidence", "value": confidence},
            )

        # Validate domain
        domain = message.get("domain")
        allowed_domains = {"btc", "conflict", "geopolitical"}
        if domain not in allowed_domains:
            raise ValidationError(
                message=f"domain must be one of {allowed_domains}, got {domain}",
                validation_type="field_value",
                details={"field": "domain", "value": domain, "allowed": list(allowed_domains)},
            )

    @staticmethod
    def _validate_news_canonical(message: Dict[str, Any]) -> None:
        """Validate news_canonical message."""
        # Validate article_id format (ULID: 26 characters or UUID: 36 characters)
        article_id = message.get("article_id")
        if not isinstance(article_id, str) or len(article_id) not in (26, 36):
            raise ValidationError(
                message=f"article_id must be 26-character ULID or 36-character UUID, got {article_id}",
                validation_type="field_format",
                details={"field": "article_id", "value": article_id},
            )

        # Validate canonical_url is not empty
        canonical_url = message.get("canonical_url")
        if not isinstance(canonical_url, str) or not canonical_url.strip():
            raise ValidationError(
                message="canonical_url must be a non-empty string",
                validation_type="field_value",
                details={"field": "canonical_url"},
            )

        # Validate language code (2 characters, lowercase)
        language = message.get("language")
        if not isinstance(language, str) or len(language) != 2 or not language.islower():
            raise ValidationError(
                message=f"language must be 2-character lowercase code, got {language}",
                validation_type="field_format",
                details={"field": "language", "value": language},
            )

        # Validate checksum is not empty
        checksum = message.get("checksum")
        if not isinstance(checksum, str) or not checksum.strip():
            raise ValidationError(
                message="checksum must be a non-empty string",
                validation_type="field_value",
                details={"field": "checksum"},
            )


# Global message validator instance
message_validator = MessageValidator()

