"""Tests for audit logging."""

import pytest
import logging
from src.audit.audit_logger import AuditLogger, AuditEventType


class TestAuditLogger:
    """Tests for audit logger."""

    def test_log_entity_extracted(self, caplog):
        """Test logging entity extraction."""
        with caplog.at_level(logging.INFO):
            AuditLogger.log_entity_extracted(
                trace_id="trace1",
                article_id="art1",
                entity_id="e1",
                entity_text="John Smith",
                entity_type="PERSON",
                confidence=0.95,
            )
        assert "ENTITY_EXTRACTED" in caplog.text
        assert "John Smith" in caplog.text
        assert "0.95" in caplog.text

    def test_log_entity_linked(self, caplog):
        """Test logging entity linking."""
        with caplog.at_level(logging.INFO):
            AuditLogger.log_entity_linked(
                trace_id="trace1",
                entity_id="e1",
                entity_text="John Smith",
                wikidata_id="Q123456",
                dbpedia_uri="http://dbpedia.org/resource/John_Smith",
                linking_source="wikidata",
            )
        assert "ENTITY_LINKED" in caplog.text
        assert "Q123456" in caplog.text

    def test_log_entity_linking_failed(self, caplog):
        """Test logging entity linking failure."""
        with caplog.at_level(logging.WARNING):
            AuditLogger.log_entity_linking_failed(
                trace_id="trace1",
                entity_id="e1",
                entity_text="Unknown Entity",
                reason="No matching entity found",
            )
        assert "ENTITY_LINKING_FAILED" in caplog.text
        assert "Unknown Entity" in caplog.text

    def test_log_actor_created(self, caplog):
        """Test logging actor creation."""
        with caplog.at_level(logging.INFO):
            AuditLogger.log_actor_created(
                trace_id="trace1",
                actor_id="a1",
                actor_name="John Smith",
                actor_type="PERSON",
            )
        assert "ACTOR_CREATED" in caplog.text
        assert "John Smith" in caplog.text

    def test_log_actor_updated(self, caplog):
        """Test logging actor update."""
        with caplog.at_level(logging.INFO):
            AuditLogger.log_actor_updated(
                trace_id="trace1",
                actor_id="a1",
                actor_name="John Smith",
                updated_fields=["sentiment_avg", "occurrences"],
            )
        assert "ACTOR_UPDATED" in caplog.text
        assert "sentiment_avg" in caplog.text

    def test_log_cache_hit(self, caplog):
        """Test logging cache hit."""
        with caplog.at_level(logging.INFO):
            AuditLogger.log_cache_hit(
                trace_id="trace1",
                cache_key="entity:john_smith",
                cache_type="entity_linking",
            )
        assert "CACHE_HIT" in caplog.text
        assert "entity_linking" in caplog.text

    def test_log_cache_miss(self, caplog):
        """Test logging cache miss."""
        with caplog.at_level(logging.INFO):
            AuditLogger.log_cache_miss(
                trace_id="trace1",
                cache_key="entity:unknown",
                cache_type="entity_linking",
            )
        assert "CACHE_MISS" in caplog.text

    def test_log_external_api_call(self, caplog):
        """Test logging external API call."""
        with caplog.at_level(logging.INFO):
            AuditLogger.log_external_api_call(
                trace_id="trace1",
                api_name="wikidata",
                endpoint="/query",
                method="POST",
                status_code=200,
                latency_ms=150.5,
            )
        assert "EXTERNAL_API_CALL" in caplog.text
        assert "wikidata" in caplog.text
        assert "200" in caplog.text

    def test_log_external_api_failure(self, caplog):
        """Test logging external API failure."""
        with caplog.at_level(logging.ERROR):
            AuditLogger.log_external_api_failure(
                trace_id="trace1",
                api_name="wikidata",
                endpoint="/query",
                error_message="Connection timeout",
            )
        assert "EXTERNAL_API_FAILURE" in caplog.text
        assert "Connection timeout" in caplog.text

    def test_log_circuit_breaker_opened(self, caplog):
        """Test logging circuit breaker opened."""
        with caplog.at_level(logging.WARNING):
            AuditLogger.log_circuit_breaker_state_change(
                trace_id="trace1",
                service="wikidata_client",
                old_state="CLOSED",
                new_state="OPEN",
            )
        assert "CIRCUIT_BREAKER_OPENED" in caplog.text

    def test_log_circuit_breaker_closed(self, caplog):
        """Test logging circuit breaker closed."""
        with caplog.at_level(logging.INFO):
            AuditLogger.log_circuit_breaker_state_change(
                trace_id="trace1",
                service="wikidata_client",
                old_state="HALF_OPEN",
                new_state="CLOSED",
            )
        assert "CIRCUIT_BREAKER_CLOSED" in caplog.text

    def test_log_retry_attempt(self, caplog):
        """Test logging retry attempt."""
        with caplog.at_level(logging.INFO):
            AuditLogger.log_retry_attempt(
                trace_id="trace1",
                operation="entity_linking",
                attempt_number=2,
                max_attempts=3,
                error_message="Timeout",
            )
        assert "RETRY_ATTEMPT" in caplog.text
        assert "2" in caplog.text

    def test_log_error(self, caplog):
        """Test logging error."""
        with caplog.at_level(logging.ERROR):
            AuditLogger.log_error(
                trace_id="trace1",
                error_type="ValueError",
                error_message="Invalid entity type",
                context={"entity_id": "e1"},
            )
        assert "ERROR_OCCURRED" in caplog.text
        assert "ValueError" in caplog.text

    def test_log_message_consumed(self, caplog):
        """Test logging message consumption."""
        with caplog.at_level(logging.INFO):
            AuditLogger.log_message_consumed(
                trace_id="trace1",
                topic="news_canonical",
                partition=0,
                offset=1000,
                message_size=2048,
            )
        assert "MESSAGE_CONSUMED" in caplog.text
        assert "news_canonical" in caplog.text

    def test_log_message_produced(self, caplog):
        """Test logging message production."""
        with caplog.at_level(logging.INFO):
            AuditLogger.log_message_produced(
                trace_id="trace1",
                topic="entities_extracted",
                partition=0,
                offset=500,
                message_size=1024,
            )
        assert "MESSAGE_PRODUCED" in caplog.text
        assert "entities_extracted" in caplog.text


class TestAuditEventType:
    """Tests for audit event types."""

    def test_event_type_values(self):
        """Test audit event type values."""
        assert AuditEventType.ENTITY_EXTRACTED.value == "ENTITY_EXTRACTED"
        assert AuditEventType.ENTITY_LINKED.value == "ENTITY_LINKED"
        assert AuditEventType.ACTOR_CREATED.value == "ACTOR_CREATED"
        assert AuditEventType.CACHE_HIT.value == "CACHE_HIT"
        assert AuditEventType.ERROR_OCCURRED.value == "ERROR_OCCURRED"

    def test_event_type_enum(self):
        """Test audit event type enum."""
        for event_type in AuditEventType:
            assert isinstance(event_type.value, str)
            assert len(event_type.value) > 0


class TestAuditLoggingIntegration:
    """Integration tests for audit logging."""

    def test_full_entity_processing_audit_trail(self, caplog):
        """Test full entity processing audit trail."""
        trace_id = "trace_full_processing"
        
        with caplog.at_level(logging.INFO):
            # Message consumed
            AuditLogger.log_message_consumed(
                trace_id=trace_id,
                topic="news_canonical",
                partition=0,
                offset=100,
                message_size=2048,
            )
            
            # Entity extracted
            AuditLogger.log_entity_extracted(
                trace_id=trace_id,
                article_id="art1",
                entity_id="e1",
                entity_text="John Smith",
                entity_type="PERSON",
                confidence=0.95,
            )
            
            # Cache miss
            AuditLogger.log_cache_miss(
                trace_id=trace_id,
                cache_key="entity:john_smith",
                cache_type="entity_linking",
            )
            
            # External API call
            AuditLogger.log_external_api_call(
                trace_id=trace_id,
                api_name="wikidata",
                endpoint="/query",
                method="POST",
                status_code=200,
                latency_ms=150.0,
            )
            
            # Entity linked
            AuditLogger.log_entity_linked(
                trace_id=trace_id,
                entity_id="e1",
                entity_text="John Smith",
                wikidata_id="Q123456",
                dbpedia_uri=None,
                linking_source="wikidata",
            )
            
            # Actor created
            AuditLogger.log_actor_created(
                trace_id=trace_id,
                actor_id="a1",
                actor_name="John Smith",
                actor_type="PERSON",
            )
            
            # Message produced
            AuditLogger.log_message_produced(
                trace_id=trace_id,
                topic="entities_extracted",
                partition=0,
                offset=50,
                message_size=1024,
            )
        
        # Verify all events were logged
        assert "MESSAGE_CONSUMED" in caplog.text
        assert "ENTITY_EXTRACTED" in caplog.text
        assert "CACHE_MISS" in caplog.text
        assert "EXTERNAL_API_CALL" in caplog.text
        assert "ENTITY_LINKED" in caplog.text
        assert "ACTOR_CREATED" in caplog.text
        assert "MESSAGE_PRODUCED" in caplog.text

