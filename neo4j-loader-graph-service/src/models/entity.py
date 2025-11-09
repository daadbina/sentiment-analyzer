"""
Entity node model for Neo4j graph.
Represents named entities extracted from articles.
"""

from datetime import datetime
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field, field_validator


class EntityType(str, Enum):
    """Entity type enumeration."""
    PERSON = "PERSON"
    ORGANIZATION = "ORG"
    LOCATION = "GPE"
    MONEY = "MONEY"
    DATE = "DATE"
    EVENT = "EVENT"


class Entity(BaseModel):
    """
    Entity node model.
    
    Represents a named entity extracted from news articles.
    """
    
    id: str = Field(
        ...,
        description="Entity identifier (ULID 26 chars or UUID 36 chars)",
        min_length=26,
        max_length=36,
    )
    
    name: str = Field(
        ...,
        description="Entity name",
        max_length=512,
    )
    
    type: EntityType = Field(
        ...,
        description="Entity type (PERSON, ORG, GPE, MONEY, DATE, EVENT)",
    )
    
    aliases: List[str] = Field(
        default_factory=list,
        description="Alternative names for the entity",
    )
    
    wikidata_id: Optional[str] = Field(
        default=None,
        description="Wikidata identifier (e.g., Q42)",
        max_length=32,
    )
    
    first_seen: datetime = Field(
        default_factory=datetime.utcnow,
        description="First occurrence timestamp",
    )
    
    last_seen: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last occurrence timestamp",
    )
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate entity name is not empty."""
        if not v.strip():
            raise ValueError("Entity name cannot be empty")
        return v.strip()
    
    @field_validator("aliases")
    @classmethod
    def normalize_aliases(cls, v: List[str]) -> List[str]:
        """Normalize aliases to lowercase and remove duplicates."""
        return list(set(alias.lower().strip() for alias in v if alias.strip()))
    
    def to_neo4j_properties(self) -> dict:
        """
        Convert model to Neo4j node properties.
        
        Returns:
            Dictionary of node properties
        """
        props = self.model_dump(exclude_none=True)
        
        # Convert enum to string
        if "type" in props:
            props["type"] = props["type"].value if isinstance(props["type"], EntityType) else props["type"]
        
        # Convert datetime to ISO format string
        if "first_seen" in props:
            props["first_seen"] = props["first_seen"].isoformat()
        if "last_seen" in props:
            props["last_seen"] = props["last_seen"].isoformat()
            
        return props
    
    @classmethod
    def from_kafka_message(cls, entity_data: dict) -> "Entity":
        """
        Create Entity from Kafka message entity data.

        Maps upstream field names to model field names:
        - "text" -> "name"
        - "entity_type" -> "type"

        Args:
            entity_data: Entity dictionary from Kafka message

        Returns:
            Entity instance
        """
        # Map entity_type to EntityType enum
        # Upstream sends: PERSON, ORGANIZATION, LOCATION, etc.
        # Model expects: PERSON, ORG, GPE, MONEY, DATE, EVENT
        entity_type_str = entity_data.get("entity_type", "").upper()

        # Map common entity types to our enum
        type_mapping = {
            "PERSON": EntityType.PERSON,
            "ORGANIZATION": EntityType.ORGANIZATION,
            "ORG": EntityType.ORGANIZATION,
            "LOCATION": EntityType.LOCATION,
            "GPE": EntityType.LOCATION,
            "MONEY": EntityType.MONEY,
            "DATE": EntityType.DATE,
            "EVENT": EntityType.EVENT,
        }

        entity_type = type_mapping.get(entity_type_str, EntityType.ORGANIZATION)

        return cls(
            id=entity_data["entity_id"],
            name=entity_data["text"],  # Map "text" to "name"
            type=entity_type,
            aliases=entity_data.get("aliases", []),
            wikidata_id=entity_data.get("wikidata_id"),
        )
    
    class Config:
        """Pydantic model configuration."""
        json_schema_extra = {
            "example": {
                "id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
                "name": "Bitcoin",
                "type": "MONEY",
                "aliases": ["btc", "bitcoin"],
                "wikidata_id": "Q131723",
                "first_seen": "2025-11-07T12:00:00Z",
                "last_seen": "2025-11-07T12:00:00Z",
            }
        }

