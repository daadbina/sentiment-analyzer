"""Output contract validation for NER Entity Linking Service."""

import logging
from typing import List, Dict, Any, Optional
from src.models import Entity, EntitiesExtractedMessage, EntityType

logger = logging.getLogger(__name__)


class OutputValidator:
    """Validates output messages against service contract."""

    # Minimum requirements for valid output
    MIN_CONFIDENCE = 0.5
    MIN_ENTITIES_PER_ARTICLE = 1
    MAX_ENTITIES_PER_ARTICLE = 1000
    MIN_COVERAGE_SCORE = 0.0
    MAX_COVERAGE_SCORE = 1.0
    MIN_LINKING_SUCCESS_RATE = 0.0
    MAX_LINKING_SUCCESS_RATE = 1.0

    @staticmethod
    def validate_entity(entity: Entity) -> tuple[bool, List[str]]:
        """Validate a single entity.

        Args:
            entity: Entity to validate

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        # Check required fields
        if not entity.entity_id:
            errors.append("entity_id is required")
        if not entity.text:
            errors.append("text is required")
        if not entity.normalized_text:
            errors.append("normalized_text is required")
        if entity.entity_type not in [e.value for e in EntityType]:
            errors.append(f"Invalid entity_type: {entity.entity_type}")

        # Check confidence
        if not (0.0 <= entity.confidence <= 1.0):
            errors.append(f"confidence must be between 0 and 1, got {entity.confidence}")

        # Check positions
        if entity.start_char < 0:
            errors.append(f"start_char must be non-negative, got {entity.start_char}")
        if entity.end_char <= entity.start_char:
            errors.append(f"end_char must be greater than start_char")

        # Check context
        if not entity.context_snippet:
            errors.append("context_snippet is required")

        return len(errors) == 0, errors

    @staticmethod
    def validate_entities_list(entities: List[Entity]) -> tuple[bool, List[str]]:
        """Validate a list of entities.

        Args:
            entities: List of entities to validate

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        # Check list size
        if len(entities) < OutputValidator.MIN_ENTITIES_PER_ARTICLE:
            errors.append(
                f"At least {OutputValidator.MIN_ENTITIES_PER_ARTICLE} entity required"
            )
        if len(entities) > OutputValidator.MAX_ENTITIES_PER_ARTICLE:
            errors.append(
                f"Maximum {OutputValidator.MAX_ENTITIES_PER_ARTICLE} entities allowed"
            )

        # Validate each entity
        for i, entity in enumerate(entities):
            is_valid, entity_errors = OutputValidator.validate_entity(entity)
            if not is_valid:
                for error in entity_errors:
                    errors.append(f"Entity {i}: {error}")

        # Check for duplicates
        entity_ids = [e.entity_id for e in entities]
        if len(entity_ids) != len(set(entity_ids)):
            errors.append("Duplicate entity_ids found")

        return len(errors) == 0, errors

    @staticmethod
    def validate_coverage_score(coverage_score: float) -> tuple[bool, List[str]]:
        """Validate coverage score.

        Args:
            coverage_score: Coverage score to validate

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        if not isinstance(coverage_score, (int, float)):
            errors.append(f"coverage_score must be numeric, got {type(coverage_score)}")
        elif not (
            OutputValidator.MIN_COVERAGE_SCORE
            <= coverage_score
            <= OutputValidator.MAX_COVERAGE_SCORE
        ):
            errors.append(
                f"coverage_score must be between "
                f"{OutputValidator.MIN_COVERAGE_SCORE} and "
                f"{OutputValidator.MAX_COVERAGE_SCORE}, got {coverage_score}"
            )

        return len(errors) == 0, errors

    @staticmethod
    def validate_linking_success_rate(rate: float) -> tuple[bool, List[str]]:
        """Validate entity linking success rate.

        Args:
            rate: Success rate to validate

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        if not isinstance(rate, (int, float)):
            errors.append(f"linking_success_rate must be numeric, got {type(rate)}")
        elif not (
            OutputValidator.MIN_LINKING_SUCCESS_RATE
            <= rate
            <= OutputValidator.MAX_LINKING_SUCCESS_RATE
        ):
            errors.append(
                f"linking_success_rate must be between "
                f"{OutputValidator.MIN_LINKING_SUCCESS_RATE} and "
                f"{OutputValidator.MAX_LINKING_SUCCESS_RATE}, got {rate}"
            )

        return len(errors) == 0, errors

    @staticmethod
    def validate_message(message: EntitiesExtractedMessage) -> tuple[bool, List[str]]:
        """Validate complete output message.

        Args:
            message: Message to validate

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        # Check required fields
        if not message.article_id:
            errors.append("article_id is required")
        if not message.trace_id:
            errors.append("trace_id is required")
        if not message.language:
            errors.append("language is required")

        # Validate entities
        is_valid, entity_errors = OutputValidator.validate_entities_list(message.entities)
        if not is_valid:
            errors.extend(entity_errors)

        # Validate coverage score
        is_valid, coverage_errors = OutputValidator.validate_coverage_score(
            message.coverage_score
        )
        if not is_valid:
            errors.extend(coverage_errors)

        # Validate linking success rate
        is_valid, linking_errors = OutputValidator.validate_linking_success_rate(
            message.linking_success_rate
        )
        if not is_valid:
            errors.extend(linking_errors)

        # Check entity count matches
        if message.entity_count != len(message.entities):
            errors.append(
                f"entity_count ({message.entity_count}) doesn't match "
                f"actual entities ({len(message.entities)})"
            )

        return len(errors) == 0, errors

    @staticmethod
    def validate_and_log(message: EntitiesExtractedMessage) -> bool:
        """Validate message and log results.

        Args:
            message: Message to validate

        Returns:
            True if valid, False otherwise
        """
        is_valid, errors = OutputValidator.validate_message(message)

        if is_valid:
            logger.info(
                f"Output validation passed for article {message.article_id}: "
                f"{len(message.entities)} entities extracted"
            )
        else:
            logger.error(
                f"Output validation failed for article {message.article_id}: "
                f"{'; '.join(errors)}"
            )

        return is_valid


class OutputContractValidator:
    """Validates output against service contract requirements."""

    # R4 Requirements
    R4_MIN_COVERAGE = 0.5  # At least 50% of entities should be extracted
    R4_MIN_LINKING_SUCCESS = 0.7  # At least 70% of entities should be linked
    R4_MIN_CONFIDENCE = 0.85  # Minimum confidence for high-quality entities

    @staticmethod
    def validate_r4_requirements(message: EntitiesExtractedMessage) -> tuple[bool, List[str]]:
        """Validate R4 requirements.

        Args:
            message: Message to validate

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        # Check coverage
        if message.coverage_score < OutputContractValidator.R4_MIN_COVERAGE:
            errors.append(
                f"Coverage score {message.coverage_score} below R4 minimum "
                f"{OutputContractValidator.R4_MIN_COVERAGE}"
            )

        # Check linking success rate
        if message.linking_success_rate < OutputContractValidator.R4_MIN_LINKING_SUCCESS:
            errors.append(
                f"Linking success rate {message.linking_success_rate} below R4 minimum "
                f"{OutputContractValidator.R4_MIN_LINKING_SUCCESS}"
            )

        # Check high-confidence entities
        high_confidence_count = sum(
            1 for e in message.entities if e.confidence >= OutputContractValidator.R4_MIN_CONFIDENCE
        )
        if high_confidence_count == 0 and len(message.entities) > 0:
            errors.append(
                f"No high-confidence entities (≥{OutputContractValidator.R4_MIN_CONFIDENCE})"
            )

        return len(errors) == 0, errors

    @staticmethod
    def validate_and_log_r4(message: EntitiesExtractedMessage) -> bool:
        """Validate R4 requirements and log results.

        Args:
            message: Message to validate

        Returns:
            True if valid, False otherwise
        """
        is_valid, errors = OutputContractValidator.validate_r4_requirements(message)

        if is_valid:
            logger.info(
                f"R4 requirements validation passed for article {message.article_id}"
            )
        else:
            logger.warning(
                f"R4 requirements validation failed for article {message.article_id}: "
                f"{'; '.join(errors)}"
            )

        return is_valid

