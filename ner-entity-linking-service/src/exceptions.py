"""Custom exception hierarchy for NER Entity Linking Service."""


class NERError(Exception):
    """Base exception for NER service."""

    pass


class UnsupportedLanguageError(NERError):
    """Raised when article language is not supported."""

    def __init__(self, language: str):
        self.language = language
        super().__init__(f"Unsupported language: {language}")


class NERExtractionError(NERError):
    """Raised when NER extraction fails."""

    def __init__(self, message: str, language: str = None):
        self.language = language
        super().__init__(message)


class EntityLinkingError(NERError):
    """Raised when entity linking fails."""

    def __init__(self, message: str, entity_text: str = None):
        self.entity_text = entity_text
        super().__init__(message)


class WikidataLinkingError(EntityLinkingError):
    """Raised when Wikidata linking fails."""

    pass


class DBpediaLinkingError(EntityLinkingError):
    """Raised when DBpedia linking fails."""

    pass


class ActorRepositoryError(NERError):
    """Raised when actor repository operations fail."""

    def __init__(self, message: str, operation: str = None):
        self.operation = operation
        super().__init__(message)


class CoverageValidationError(NERError):
    """Raised when coverage validation fails."""

    def __init__(self, message: str, coverage_score: float = None):
        self.coverage_score = coverage_score
        super().__init__(message)


class KafkaError(NERError):
    """Raised when Kafka operations fail."""

    pass


class ConfigurationError(NERError):
    """Raised when configuration is invalid."""

    pass


class CircuitBreakerOpenError(NERError):
    """Raised when circuit breaker is open."""

    def __init__(self, service: str):
        self.service = service
        super().__init__(f"Circuit breaker open for service: {service}")


class ProcessingTimeoutError(NERError):
    """Raised when processing exceeds timeout."""

    pass

