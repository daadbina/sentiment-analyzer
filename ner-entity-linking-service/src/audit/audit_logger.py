"""Audit logging for NER Entity Linking Service."""

import logging
import json
from datetime import datetime
from typing import Any, Dict, Optional, List
from enum import Enum

logger = logging.getLogger(__name__)


class AuditEventType(str, Enum):
    """Audit event types."""

    ENTITY_EXTRACTED = "ENTITY_EXTRACTED"
    ENTITY_LINKED = "ENTITY_LINKED"
    ENTITY_LINKING_FAILED = "ENTITY_LINKING_FAILED"
    ACTOR_CREATED = "ACTOR_CREATED"
    ACTOR_UPDATED = "ACTOR_UPDATED"
    ACTOR_DELETED = "ACTOR_DELETED"
    CACHE_HIT = "CACHE_HIT"
    CACHE_MISS = "CACHE_MISS"
    DATABASE_QUERY = "DATABASE_QUERY"
    EXTERNAL_API_CALL = "EXTERNAL_API_CALL"
    EXTERNAL_API_FAILURE = "EXTERNAL_API_FAILURE"
    CIRCUIT_BREAKER_OPENED = "CIRCUIT_BREAKER_OPENED"
    CIRCUIT_BREAKER_CLOSED = "CIRCUIT_BREAKER_CLOSED"
    RETRY_ATTEMPT = "RETRY_ATTEMPT"
    MESSAGE_CONSUMED = "MESSAGE_CONSUMED"
    MESSAGE_PRODUCED = "MESSAGE_PRODUCED"
    ERROR_OCCURRED = "ERROR_OCCURRED"
    CONFIGURATION_LOADED = "CONFIGURATION_LOADED"
    SERVICE_STARTED = "SERVICE_STARTED"
    SERVICE_STOPPED = "SERVICE_STOPPED"


class AuditLogger:
    """Audit logger for tracking service operations."""

    @staticmethod
    def log_event(
        event_type: AuditEventType,
        trace_id: str,
        details: Dict[str, Any],
        severity: str = "INFO",
    ) -> None:
        """Log an audit event.

        Args:
            event_type: Type of event
            trace_id: Trace ID for correlation
            details: Event details
            severity: Log severity level
        """
        audit_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type.value,
            "trace_id": trace_id,
            "severity": severity,
            "details": details,
        }

        log_message = json.dumps(audit_record)

        if severity == "ERROR":
            logger.error(f"AUDIT: {log_message}")
        elif severity == "WARNING":
            logger.warning(f"AUDIT: {log_message}")
        else:
            logger.info(f"AUDIT: {log_message}")

    @staticmethod
    def log_entity_extracted(
        trace_id: str,
        article_id: str,
        entity_id: str,
        entity_text: str,
        entity_type: str,
        confidence: float,
    ) -> None:
        """Log entity extraction.

        Args:
            trace_id: Trace ID
            article_id: Article ID
            entity_id: Entity ID
            entity_text: Entity text
            entity_type: Entity type
            confidence: Confidence score
        """
        details = {
            "article_id": article_id,
            "entity_id": entity_id,
            "entity_text": entity_text,
            "entity_type": entity_type,
            "confidence": confidence,
        }
        AuditLogger.log_event(AuditEventType.ENTITY_EXTRACTED, trace_id, details)

    @staticmethod
    def log_entity_linked(
        trace_id: str,
        entity_id: str,
        entity_text: str,
        wikidata_id: Optional[str],
        dbpedia_uri: Optional[str],
        linking_source: str,
    ) -> None:
        """Log entity linking.

        Args:
            trace_id: Trace ID
            entity_id: Entity ID
            entity_text: Entity text
            wikidata_id: Wikidata ID
            dbpedia_uri: DBpedia URI
            linking_source: Source of linking (wikidata, dbpedia, opensanctions)
        """
        details = {
            "entity_id": entity_id,
            "entity_text": entity_text,
            "wikidata_id": wikidata_id,
            "dbpedia_uri": dbpedia_uri,
            "linking_source": linking_source,
        }
        AuditLogger.log_event(AuditEventType.ENTITY_LINKED, trace_id, details)

    @staticmethod
    def log_entity_linking_failed(
        trace_id: str,
        entity_id: str,
        entity_text: str,
        reason: str,
    ) -> None:
        """Log entity linking failure.

        Args:
            trace_id: Trace ID
            entity_id: Entity ID
            entity_text: Entity text
            reason: Failure reason
        """
        details = {
            "entity_id": entity_id,
            "entity_text": entity_text,
            "reason": reason,
        }
        AuditLogger.log_event(
            AuditEventType.ENTITY_LINKING_FAILED, trace_id, details, severity="WARNING"
        )

    @staticmethod
    def log_actor_created(
        trace_id: str,
        actor_id: str,
        actor_name: str,
        actor_type: str,
    ) -> None:
        """Log actor creation.

        Args:
            trace_id: Trace ID
            actor_id: Actor ID
            actor_name: Actor name
            actor_type: Actor type
        """
        details = {
            "actor_id": actor_id,
            "actor_name": actor_name,
            "actor_type": actor_type,
        }
        AuditLogger.log_event(AuditEventType.ACTOR_CREATED, trace_id, details)

    @staticmethod
    def log_actor_updated(
        trace_id: str,
        actor_id: str,
        actor_name: str,
        updated_fields: List[str],
    ) -> None:
        """Log actor update.

        Args:
            trace_id: Trace ID
            actor_id: Actor ID
            actor_name: Actor name
            updated_fields: List of updated fields
        """
        details = {
            "actor_id": actor_id,
            "actor_name": actor_name,
            "updated_fields": updated_fields,
        }
        AuditLogger.log_event(AuditEventType.ACTOR_UPDATED, trace_id, details)

    @staticmethod
    def log_cache_hit(
        trace_id: str,
        cache_key: str,
        cache_type: str,
    ) -> None:
        """Log cache hit.

        Args:
            trace_id: Trace ID
            cache_key: Cache key
            cache_type: Type of cache (entity_linking, model, etc.)
        """
        details = {
            "cache_key": cache_key,
            "cache_type": cache_type,
        }
        AuditLogger.log_event(AuditEventType.CACHE_HIT, trace_id, details)

    @staticmethod
    def log_cache_miss(
        trace_id: str,
        cache_key: str,
        cache_type: str,
    ) -> None:
        """Log cache miss.

        Args:
            trace_id: Trace ID
            cache_key: Cache key
            cache_type: Type of cache
        """
        details = {
            "cache_key": cache_key,
            "cache_type": cache_type,
        }
        AuditLogger.log_event(AuditEventType.CACHE_MISS, trace_id, details)

    @staticmethod
    def log_external_api_call(
        trace_id: str,
        api_name: str,
        endpoint: str,
        method: str,
        status_code: int,
        latency_ms: float,
    ) -> None:
        """Log external API call.

        Args:
            trace_id: Trace ID
            api_name: API name
            endpoint: API endpoint
            method: HTTP method
            status_code: Response status code
            latency_ms: Latency in milliseconds
        """
        details = {
            "api_name": api_name,
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "latency_ms": latency_ms,
        }
        AuditLogger.log_event(AuditEventType.EXTERNAL_API_CALL, trace_id, details)

    @staticmethod
    def log_external_api_failure(
        trace_id: str,
        api_name: str,
        endpoint: str,
        error_message: str,
    ) -> None:
        """Log external API failure.

        Args:
            trace_id: Trace ID
            api_name: API name
            endpoint: API endpoint
            error_message: Error message
        """
        details = {
            "api_name": api_name,
            "endpoint": endpoint,
            "error_message": error_message,
        }
        AuditLogger.log_event(
            AuditEventType.EXTERNAL_API_FAILURE, trace_id, details, severity="ERROR"
        )

    @staticmethod
    def log_circuit_breaker_state_change(
        trace_id: str,
        service: str,
        old_state: str,
        new_state: str,
    ) -> None:
        """Log circuit breaker state change.

        Args:
            trace_id: Trace ID
            service: Service name
            old_state: Old state
            new_state: New state
        """
        event_type = (
            AuditEventType.CIRCUIT_BREAKER_OPENED
            if new_state == "OPEN"
            else AuditEventType.CIRCUIT_BREAKER_CLOSED
        )
        details = {
            "service": service,
            "old_state": old_state,
            "new_state": new_state,
        }
        severity = "WARNING" if new_state == "OPEN" else "INFO"
        AuditLogger.log_event(event_type, trace_id, details, severity=severity)

    @staticmethod
    def log_retry_attempt(
        trace_id: str,
        operation: str,
        attempt_number: int,
        max_attempts: int,
        error_message: str,
    ) -> None:
        """Log retry attempt.

        Args:
            trace_id: Trace ID
            operation: Operation name
            attempt_number: Current attempt number
            max_attempts: Maximum attempts
            error_message: Error message
        """
        details = {
            "operation": operation,
            "attempt_number": attempt_number,
            "max_attempts": max_attempts,
            "error_message": error_message,
        }
        AuditLogger.log_event(AuditEventType.RETRY_ATTEMPT, trace_id, details)

    @staticmethod
    def log_error(
        trace_id: str,
        error_type: str,
        error_message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log error.

        Args:
            trace_id: Trace ID
            error_type: Error type
            error_message: Error message
            context: Additional context
        """
        details = {
            "error_type": error_type,
            "error_message": error_message,
            "context": context or {},
        }
        AuditLogger.log_event(AuditEventType.ERROR_OCCURRED, trace_id, details, severity="ERROR")

    @staticmethod
    def log_message_consumed(
        trace_id: str,
        topic: str,
        partition: int,
        offset: int,
        message_size: int,
    ) -> None:
        """Log message consumption.

        Args:
            trace_id: Trace ID
            topic: Kafka topic
            partition: Partition number
            offset: Message offset
            message_size: Message size in bytes
        """
        details = {
            "topic": topic,
            "partition": partition,
            "offset": offset,
            "message_size": message_size,
        }
        AuditLogger.log_event(AuditEventType.MESSAGE_CONSUMED, trace_id, details)

    @staticmethod
    def log_message_produced(
        trace_id: str,
        topic: str,
        partition: int,
        offset: int,
        message_size: int,
    ) -> None:
        """Log message production.

        Args:
            trace_id: Trace ID
            topic: Kafka topic
            partition: Partition number
            offset: Message offset
            message_size: Message size in bytes
        """
        details = {
            "topic": topic,
            "partition": partition,
            "offset": offset,
            "message_size": message_size,
        }
        AuditLogger.log_event(AuditEventType.MESSAGE_PRODUCED, trace_id, details)

