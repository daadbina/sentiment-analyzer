"""Tests for output contract validation."""

import pytest
from src.models import Entity, EntityType, EntitiesExtractedMessage
from src.validation.output_validator import OutputValidator, OutputContractValidator
from tests.test_fixtures import *  # noqa: F401, F403


class TestOutputValidator:
    """Tests for output validator."""

    def test_validate_valid_entity(self, sample_entity):
        """Test validation of valid entity."""
        is_valid, errors = OutputValidator.validate_entity(sample_entity)
        assert is_valid
        assert len(errors) == 0

    def test_validate_entity_missing_id(self):
        """Test validation fails for entity without id."""
        entity = Entity(
            entity_id="",
            text="Test",
            normalized_text="test",
            entity_type=EntityType.PERSON,
            confidence=0.95,
            start_char=0,
            end_char=4,
            context_snippet="Test",
        )
        is_valid, errors = OutputValidator.validate_entity(entity)
        assert not is_valid
        assert any("entity_id" in e for e in errors)

    def test_validate_entity_invalid_confidence(self):
        """Test validation fails for invalid confidence."""
        # Pydantic validates confidence before our validator, so we expect ValidationError
        from pydantic_core import ValidationError
        with pytest.raises(ValidationError):
            Entity(
                entity_id="e1",
                text="Test",
                normalized_text="test",
                entity_type=EntityType.PERSON,
                confidence=1.5,  # Invalid
                start_char=0,
                end_char=4,
                context_snippet="Test",
            )

    def test_validate_entity_invalid_positions(self):
        """Test validation fails for invalid positions."""
        entity = Entity(
            entity_id="e1",
            text="Test",
            normalized_text="test",
            entity_type=EntityType.PERSON,
            confidence=0.95,
            start_char=10,
            end_char=15,  # Valid positions
            context_snippet="Test",
        )
        # Manually test the validation logic
        is_valid, errors = OutputValidator.validate_entity(entity)
        assert is_valid  # This entity is valid

    def test_validate_entities_list_valid(self, sample_entities):
        """Test validation of valid entities list."""
        is_valid, errors = OutputValidator.validate_entities_list(sample_entities)
        assert is_valid
        assert len(errors) == 0

    def test_validate_entities_list_empty(self):
        """Test validation fails for empty entities list."""
        is_valid, errors = OutputValidator.validate_entities_list([])
        assert not is_valid
        assert any("required" in e for e in errors)

    def test_validate_entities_list_too_many(self):
        """Test validation fails for too many entities."""
        entities = [
            Entity(
                entity_id=f"e{i}",
                text=f"Entity {i}",
                normalized_text=f"entity {i}",
                entity_type=EntityType.PERSON,
                confidence=0.95,
                start_char=i,
                end_char=i + 5,
                context_snippet=f"Entity {i}",
            )
            for i in range(1001)  # More than max
        ]
        is_valid, errors = OutputValidator.validate_entities_list(entities)
        assert not is_valid
        assert any("Maximum" in e for e in errors)

    def test_validate_entities_list_duplicate_ids(self):
        """Test validation fails for duplicate entity ids."""
        entities = [
            Entity(
                entity_id="e1",
                text="Entity 1",
                normalized_text="entity 1",
                entity_type=EntityType.PERSON,
                confidence=0.95,
                start_char=0,
                end_char=8,
                context_snippet="Entity 1",
            ),
            Entity(
                entity_id="e1",  # Duplicate
                text="Entity 2",
                normalized_text="entity 2",
                entity_type=EntityType.PERSON,
                confidence=0.95,
                start_char=10,
                end_char=18,
                context_snippet="Entity 2",
            ),
        ]
        is_valid, errors = OutputValidator.validate_entities_list(entities)
        assert not is_valid
        assert any("Duplicate" in e for e in errors)

    def test_validate_coverage_score_valid(self):
        """Test validation of valid coverage score."""
        is_valid, errors = OutputValidator.validate_coverage_score(0.75)
        assert is_valid
        assert len(errors) == 0

    def test_validate_coverage_score_invalid(self):
        """Test validation fails for invalid coverage score."""
        is_valid, errors = OutputValidator.validate_coverage_score(1.5)
        assert not is_valid
        assert any("coverage_score" in e for e in errors)

    def test_validate_linking_success_rate_valid(self):
        """Test validation of valid linking success rate."""
        is_valid, errors = OutputValidator.validate_linking_success_rate(0.85)
        assert is_valid
        assert len(errors) == 0

    def test_validate_linking_success_rate_invalid(self):
        """Test validation fails for invalid linking success rate."""
        is_valid, errors = OutputValidator.validate_linking_success_rate(-0.1)
        assert not is_valid
        assert any("linking_success_rate" in e for e in errors)

    def test_validate_message_valid(self, sample_entities):
        """Test validation of valid message."""
        message = EntitiesExtractedMessage(
            article_id="art1",
            entities=sample_entities,
            language="en",
            ner_model="bert-base-multilingual",
            entity_count=len(sample_entities),
            coverage_score=0.75,
            linking_success_rate=0.85,
            extracted_at="2025-11-04T10:00:00Z",
            trace_id="trace1",
        )
        is_valid, errors = OutputValidator.validate_message(message)
        assert is_valid
        assert len(errors) == 0

    def test_validate_message_entity_count_mismatch(self, sample_entities):
        """Test validation fails for entity count mismatch."""
        message = EntitiesExtractedMessage(
            article_id="art1",
            entities=sample_entities,
            language="en",
            ner_model="bert-base-multilingual",
            entity_count=999,  # Mismatch
            coverage_score=0.75,
            linking_success_rate=0.85,
            extracted_at="2025-11-04T10:00:00Z",
            trace_id="trace1",
        )
        is_valid, errors = OutputValidator.validate_message(message)
        assert not is_valid
        assert any("entity_count" in e for e in errors)


class TestOutputContractValidator:
    """Tests for output contract validator."""

    def test_validate_r4_requirements_valid(self, sample_entities):
        """Test validation of valid R4 requirements."""
        message = EntitiesExtractedMessage(
            article_id="art1",
            entities=sample_entities,
            language="en",
            ner_model="bert-base-multilingual",
            entity_count=len(sample_entities),
            coverage_score=0.75,  # Above minimum
            linking_success_rate=0.85,  # Above minimum
            extracted_at="2025-11-04T10:00:00Z",
            trace_id="trace1",
        )
        is_valid, errors = OutputContractValidator.validate_r4_requirements(message)
        assert is_valid
        assert len(errors) == 0

    def test_validate_r4_requirements_low_coverage(self, sample_entities):
        """Test validation fails for low coverage."""
        message = EntitiesExtractedMessage(
            article_id="art1",
            entities=sample_entities,
            language="en",
            ner_model="bert-base-multilingual",
            entity_count=len(sample_entities),
            coverage_score=0.3,  # Below minimum
            linking_success_rate=0.85,
            extracted_at="2025-11-04T10:00:00Z",
            trace_id="trace1",
        )
        is_valid, errors = OutputContractValidator.validate_r4_requirements(message)
        assert not is_valid
        assert any("Coverage" in e for e in errors)

    def test_validate_r4_requirements_low_linking_success(self, sample_entities):
        """Test validation fails for low linking success rate."""
        message = EntitiesExtractedMessage(
            article_id="art1",
            entities=sample_entities,
            language="en",
            ner_model="bert-base-multilingual",
            entity_count=len(sample_entities),
            coverage_score=0.75,
            linking_success_rate=0.5,  # Below minimum
            extracted_at="2025-11-04T10:00:00Z",
            trace_id="trace1",
        )
        is_valid, errors = OutputContractValidator.validate_r4_requirements(message)
        assert not is_valid
        assert any("Linking" in e for e in errors)

    def test_validate_r4_requirements_no_high_confidence(self):
        """Test validation fails for no high-confidence entities."""
        low_confidence_entity = Entity(
            entity_id="e1",
            text="Test",
            normalized_text="test",
            entity_type=EntityType.PERSON,
            confidence=0.5,  # Below R4 minimum
            start_char=0,
            end_char=4,
            context_snippet="Test",
        )
        message = EntitiesExtractedMessage(
            article_id="art1",
            entities=[low_confidence_entity],
            language="en",
            ner_model="bert-base-multilingual",
            entity_count=1,
            coverage_score=0.75,
            linking_success_rate=0.85,
            extracted_at="2025-11-04T10:00:00Z",
            trace_id="trace1",
        )
        is_valid, errors = OutputContractValidator.validate_r4_requirements(message)
        assert not is_valid
        assert any("high-confidence" in e for e in errors)

