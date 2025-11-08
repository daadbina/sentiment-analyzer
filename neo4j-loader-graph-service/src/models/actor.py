"""
Actor node model for Neo4j graph.
Represents actors (people, organizations, countries) involved in news events.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


class Actor(BaseModel):
    """
    Actor node model.
    
    Represents an actor (person, organization, or country) in the news graph.
    """
    
    id: str = Field(
        ...,
        description="Actor ULID identifier",
        min_length=26,
        max_length=26,
    )
    
    name: str = Field(
        ...,
        description="Actor name",
        max_length=512,
    )
    
    type: str = Field(
        ...,
        description="Actor type (PERSON, ORGANIZATION, COUNTRY)",
        max_length=64,
    )
    
    country: Optional[str] = Field(
        default=None,
        description="Country code (ISO 3166-1 alpha-2)",
        min_length=2,
        max_length=2,
    )
    
    aliases: List[str] = Field(
        default_factory=list,
        description="Alternative names for the actor",
    )
    
    sentiment_avg: Optional[float] = Field(
        default=None,
        description="Average sentiment score [-1.0, +1.0]",
        ge=-1.0,
        le=1.0,
    )
    
    occurrences: int = Field(
        default=0,
        description="Number of times actor appears in articles",
        ge=0,
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
        """Validate actor name is not empty."""
        if not v.strip():
            raise ValueError("Actor name cannot be empty")
        return v.strip()
    
    @field_validator("country")
    @classmethod
    def validate_country(cls, v: Optional[str]) -> Optional[str]:
        """Validate country code format."""
        if v and not v.isupper():
            raise ValueError("Country code must be uppercase")
        return v
    
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
        
        # Convert datetime to ISO format string
        if "first_seen" in props:
            props["first_seen"] = props["first_seen"].isoformat()
        if "last_seen" in props:
            props["last_seen"] = props["last_seen"].isoformat()
            
        return props
    
    @classmethod
    def from_postgres_row(cls, row: dict) -> "Actor":
        """
        Create Actor from PostgreSQL actors table row.
        
        Args:
            row: Database row dictionary
            
        Returns:
            Actor instance
        """
        return cls(
            id=row["actor_id"],
            name=row["name"],
            type=row["type"],
            country=row.get("country"),
            aliases=row.get("aliases", []),
            sentiment_avg=row.get("sentiment_avg"),
            occurrences=row.get("occurrences", 0),
            wikidata_id=row.get("wikidata_id"),
            first_seen=row.get("first_seen", datetime.utcnow()),
            last_seen=row.get("last_seen", datetime.utcnow()),
        )
    
    class Config:
        """Pydantic model configuration."""
        json_schema_extra = {
            "example": {
                "id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
                "name": "United States",
                "type": "COUNTRY",
                "country": "US",
                "aliases": ["usa", "united states", "america"],
                "sentiment_avg": 0.2,
                "occurrences": 150,
                "wikidata_id": "Q30",
                "first_seen": "2025-11-07T12:00:00Z",
                "last_seen": "2025-11-07T12:00:00Z",
            }
        }

