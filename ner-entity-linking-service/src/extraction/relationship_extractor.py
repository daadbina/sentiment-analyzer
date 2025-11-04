"""
Relationship extraction between entities.
"""
import logging
import re
from typing import List, Dict, Any, Tuple
from prometheus_client import Counter, Histogram, REGISTRY
import time

logger = logging.getLogger(__name__)

# Global metrics (registered once)
try:
    _relationships_extracted = REGISTRY._names_to_collectors.get("ner_relationships_extracted_total")
    if _relationships_extracted is None:
        _relationships_extracted = Counter(
            "ner_relationships_extracted_total",
            "Total relationships extracted",
            ["relationship_type"],
        )
except:
    _relationships_extracted = Counter(
        "ner_relationships_extracted_total",
        "Total relationships extracted",
        ["relationship_type"],
    )

try:
    _extraction_latency = REGISTRY._names_to_collectors.get("ner_relationship_extraction_latency_seconds")
    if _extraction_latency is None:
        _extraction_latency = Histogram(
            "ner_relationship_extraction_latency_seconds",
            "Relationship extraction latency",
        )
except:
    _extraction_latency = Histogram(
        "ner_relationship_extraction_latency_seconds",
        "Relationship extraction latency",
    )


class RelationshipExtractor:
    """Extract relationships between entities."""

    def __init__(self, window_size: int = 50):
        """
        Initialize relationship extractor.

        Args:
            window_size: Context window size in characters (default 50)
        """
        self.window_size = window_size

        # Use global metrics
        self.relationships_extracted = _relationships_extracted
        self.extraction_latency = _extraction_latency
        
        # Common relationship patterns
        self.patterns = {
            "works_at": [
                r"(\w+)\s+(?:works|worked)\s+at\s+(\w+)",
                r"(\w+)\s+(?:is|was)\s+(?:a|an)?\s+(?:CEO|president|director)\s+of\s+(\w+)",
                r"(\w+)\s+(?:employed|hired)\s+by\s+(\w+)",
            ],
            "located_in": [
                r"(\w+)\s+(?:is|located)\s+in\s+(\w+)",
                r"(\w+)\s+(?:based|headquartered)\s+in\s+(\w+)",
            ],
            "founded_by": [
                r"(\w+)\s+(?:founded|created)\s+by\s+(\w+)",
                r"(\w+)\s+(?:was|is)\s+founded\s+by\s+(\w+)",
            ],
            "owns": [
                r"(\w+)\s+(?:owns|acquired)\s+(\w+)",
                r"(\w+)\s+(?:is|was)\s+owned\s+by\s+(\w+)",
            ],
            "related_to": [
                r"(\w+)\s+(?:and|with)\s+(\w+)",
            ],
        }

    def extract_relationships(
        self,
        text: str,
        entities: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Extract relationships between entities.
        
        Args:
            text: Text to extract relationships from
            entities: List of extracted entities
            
        Returns:
            List of relationships
        """
        start_time = time.time()
        relationships = []
        
        # Extract relationships using patterns
        for rel_type, patterns in self.patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                
                for match in matches:
                    entity1 = match.group(1)
                    entity2 = match.group(2)
                    
                    # Verify entities exist in extracted entities
                    if self._entity_exists(entity1, entities) and self._entity_exists(entity2, entities):
                        relationship = {
                            "entity1": entity1,
                            "entity2": entity2,
                            "relationship_type": rel_type,
                            "confidence": 0.8,
                            "context": text[max(0, match.start()-50):min(len(text), match.end()+50)],
                        }
                        relationships.append(relationship)
                        self.relationships_extracted.labels(relationship_type=rel_type).inc()
        
        latency = time.time() - start_time
        self.extraction_latency.observe(latency)
        
        logger.debug(f"Extracted {len(relationships)} relationships")
        return relationships

    def _entity_exists(self, entity_text: str, entities: List[Dict[str, Any]]) -> bool:
        """
        Check if entity exists in extracted entities.
        
        Args:
            entity_text: Entity text to check
            entities: List of extracted entities
            
        Returns:
            True if entity exists
        """
        for entity in entities:
            if entity_text.lower() in entity.get("text", "").lower():
                return True
        return False

    def extract_coreferences(
        self,
        text: str,
        entities: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Extract coreferences (same entity mentioned multiple times).
        
        Args:
            text: Text to extract coreferences from
            entities: List of extracted entities
            
        Returns:
            List of coreference clusters
        """
        coreferences = []
        
        # Simple pronoun resolution
        pronouns = {
            "he": ["his", "him"],
            "she": ["her"],
            "it": ["its"],
            "they": ["their", "them"],
        }
        
        for entity in entities:
            entity_text = entity.get("text", "")
            entity_type = entity.get("entity_type", "")
            
            # Find pronouns that refer to this entity
            for pronoun, variants in pronouns.items():
                for variant in variants:
                    pattern = rf"\b{variant}\b"
                    matches = re.finditer(pattern, text, re.IGNORECASE)
                    
                    for match in matches:
                        coreference = {
                            "entity": entity_text,
                            "entity_type": entity_type,
                            "pronoun": variant,
                            "offset": match.start(),
                            "confidence": 0.7,
                        }
                        coreferences.append(coreference)
        
        logger.debug(f"Extracted {len(coreferences)} coreferences")
        return coreferences

    def extract_attributes(
        self,
        text: str,
        entities: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Extract entity attributes from text.
        
        Args:
            text: Text to extract attributes from
            entities: List of extracted entities
            
        Returns:
            List of entity attributes
        """
        attributes = []
        
        # Common attribute patterns
        attribute_patterns = {
            "age": r"(\w+)\s+(?:is|was)\s+(\d+)\s+years?\s+old",
            "title": r"(\w+)\s+(?:is|was)\s+(?:a|an)?\s+(\w+)",
            "location": r"(\w+)\s+(?:in|from|at)\s+(\w+)",
            "organization": r"(\w+)\s+(?:at|in|from)\s+(\w+)",
        }
        
        for attr_type, pattern in attribute_patterns.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            
            for match in matches:
                entity_name = match.group(1)
                attribute_value = match.group(2)
                
                if self._entity_exists(entity_name, entities):
                    attribute = {
                        "entity": entity_name,
                        "attribute_type": attr_type,
                        "attribute_value": attribute_value,
                        "confidence": 0.75,
                    }
                    attributes.append(attribute)
        
        logger.debug(f"Extracted {len(attributes)} attributes")
        return attributes

