"""Data models for NER Entity Linking Service."""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class EntityType(str, Enum):
    """Entity type enumeration."""

    PERSON = "PERSON"
    ORGANIZATION = "ORGANIZATION"
    LOCATION = "LOCATION"
    GPE = "GPE"
    CURRENCY = "CURRENCY"
    DATE = "DATE"
    EVENT = "EVENT"


class Entity(BaseModel):
    """Extracted entity model."""

    entity_id: str
    text: str
    normalized_text: str
    entity_type: EntityType
    start_char: int
    end_char: int
    confidence: float = Field(ge=0.0, le=1.0)
    wikidata_id: Optional[str] = None
    dbpedia_uri: Optional[str] = None
    country: Optional[str] = None
    aliases: List[str] = Field(default_factory=list)
    context_snippet: str

    class Config:
        use_enum_values = True


class Relationship(BaseModel):
    """Entity relationship model."""

    source_entity_id: str
    target_entity_id: str
    relationship_type: str
    weight: float = Field(ge=0.0, le=1.0)
    context: str
    confidence: float = Field(ge=0.0, le=1.0)


class EntitiesExtractedMessage(BaseModel):
    """Kafka message for extracted entities."""

    article_id: str
    entities: List[Entity]
    language: str
    ner_model: str
    entity_count: int
    coverage_score: float = Field(ge=0.0, le=1.0)
    linking_success_rate: float = Field(ge=0.0, le=1.0)
    extracted_at: str
    trace_id: str
    schema_version: str = "1.0.0"


class Actor(BaseModel):
    """Actor (normalized entity) model."""

    actor_id: Optional[str] = None
    name: str
    normalized_name: str
    type: EntityType
    aliases: List[str] = Field(default_factory=list)
    country: Optional[str] = None
    wikidata_id: Optional[str] = None
    dbpedia_uri: Optional[str] = None
    sentiment_avg: float = Field(default=0.0, ge=-1.0, le=1.0)
    occurrences: int = Field(default=1, ge=1)
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    ner_fallback_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        use_enum_values = True


class NewsCanonicalMessage(BaseModel):
    """Input message from news_canonical topic."""

    article_id: str
    canonical_url: str
    title: str
    normalized_body: str
    language: str
    publisher_id: str
    publisher_credibility: float
    domain: str
    published_at: str
    normalized_at: str
    trace_id: str


class NERResult(BaseModel):
    """Result of NER extraction."""

    entities: List[Entity]
    coverage_score: float
    linking_success_rate: float
    extraction_duration_ms: float
    model_used: str
    language: str

