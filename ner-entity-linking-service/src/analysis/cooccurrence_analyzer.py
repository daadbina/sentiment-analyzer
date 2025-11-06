"""
Co-occurrence analysis for entities.
"""
import logging
from typing import List, Dict, Any, Tuple
from collections import defaultdict
from prometheus_client import Counter, Histogram, REGISTRY
import time

logger = logging.getLogger(__name__)

# Global metrics (registered once)
try:
    _cooccurrences_found = REGISTRY._names_to_collectors.get("ner_cooccurrences_found_total")
    if _cooccurrences_found is None:
        _cooccurrences_found = Counter(
            "ner_cooccurrences_found_total",
            "Total entity co-occurrences found",
        )
except:
    _cooccurrences_found = Counter(
        "ner_cooccurrences_found_total",
        "Total entity co-occurrences found",
    )

try:
    _analysis_latency = REGISTRY._names_to_collectors.get("ner_cooccurrence_analysis_latency_seconds")
    if _analysis_latency is None:
        _analysis_latency = Histogram(
            "ner_cooccurrence_analysis_latency_seconds",
            "Co-occurrence analysis latency",
        )
except:
    _analysis_latency = Histogram(
        "ner_cooccurrence_analysis_latency_seconds",
        "Co-occurrence analysis latency",
    )


class CooccurrenceAnalyzer:
    """Analyze entity co-occurrences in text."""

    def __init__(self, window_size: int = 50, cooccurrence_threshold: int = 3):
        """
        Initialize co-occurrence analyzer.

        Args:
            window_size: Context window size in characters (default 50)
            cooccurrence_threshold: Minimum co-occurrence count for clustering (from config)
        """
        self.window_size = window_size
        self.cooccurrence_threshold = cooccurrence_threshold

        # Use global metrics
        self.cooccurrences_found = _cooccurrences_found
        self.analysis_latency = _analysis_latency

    def analyze_cooccurrences(
        self,
        text: str,
        entities: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Analyze entity co-occurrences in text.
        
        Args:
            text: Text to analyze
            entities: List of extracted entities
            
        Returns:
            List of co-occurrence pairs
        """
        start_time = time.time()
        cooccurrences = []
        
        # Sort entities by position
        sorted_entities = sorted(entities, key=lambda e: e.get("start_char", 0))
        
        # Find co-occurrences within window
        for i, entity1 in enumerate(sorted_entities):
            for entity2 in sorted_entities[i+1:]:
                distance = entity2.get("start_char", 0) - entity1.get("end_char", 0)
                
                # Check if entities are within window
                if 0 < distance <= self.window_size:
                    cooccurrence = {
                        "entity1": entity1.get("text", ""),
                        "entity1_type": entity1.get("entity_type", ""),
                        "entity2": entity2.get("text", ""),
                        "entity2_type": entity2.get("entity_type", ""),
                        "distance": distance,
                        "confidence": self._calculate_confidence(distance),
                        "context": text[
                            max(0, entity1.get("start_char", 0) - 20):
                            min(len(text), entity2.get("end_char", 0) + 20)
                        ],
                    }
                    cooccurrences.append(cooccurrence)
                    self.cooccurrences_found.inc()
        
        latency = time.time() - start_time
        self.analysis_latency.observe(latency)
        
        logger.debug(f"Found {len(cooccurrences)} co-occurrences")
        return cooccurrences

    def _calculate_confidence(self, distance: int) -> float:
        """
        Calculate confidence based on distance.
        
        Args:
            distance: Distance between entities
            
        Returns:
            Confidence score (0-1)
        """
        # Closer entities have higher confidence
        if distance <= 10:
            return 0.95
        elif distance <= 20:
            return 0.85
        elif distance <= 30:
            return 0.75
        else:
            return 0.65

    def build_cooccurrence_matrix(
        self,
        documents: List[Tuple[str, List[Dict[str, Any]]]],
    ) -> Dict[Tuple[str, str], int]:
        """
        Build co-occurrence matrix from multiple documents.
        
        Args:
            documents: List of (text, entities) tuples
            
        Returns:
            Co-occurrence matrix as dictionary
        """
        matrix = defaultdict(int)
        
        for text, entities in documents:
            cooccurrences = self.analyze_cooccurrences(text, entities)
            
            for cooc in cooccurrences:
                entity1 = cooc["entity1"]
                entity2 = cooc["entity2"]
                
                # Create symmetric key
                key = tuple(sorted([entity1, entity2]))
                matrix[key] += 1
        
        logger.debug(f"Built co-occurrence matrix with {len(matrix)} pairs")
        return dict(matrix)

    def get_related_entities(
        self,
        entity_name: str,
        cooccurrence_matrix: Dict[Tuple[str, str], int],
        top_k: int = 5,
    ) -> List[Tuple[str, int]]:
        """
        Get entities most frequently co-occurring with given entity.
        
        Args:
            entity_name: Entity to find related entities for
            cooccurrence_matrix: Co-occurrence matrix
            top_k: Number of top related entities to return
            
        Returns:
            List of (entity_name, count) tuples
        """
        related = []
        
        for (entity1, entity2), count in cooccurrence_matrix.items():
            if entity1 == entity_name:
                related.append((entity2, count))
            elif entity2 == entity_name:
                related.append((entity1, count))
        
        # Sort by count descending
        related.sort(key=lambda x: x[1], reverse=True)
        
        return related[:top_k]

    def calculate_entity_importance(
        self,
        cooccurrence_matrix: Dict[Tuple[str, str], int],
    ) -> Dict[str, float]:
        """
        Calculate entity importance based on co-occurrence frequency.
        
        Args:
            cooccurrence_matrix: Co-occurrence matrix
            
        Returns:
            Dictionary of entity importance scores
        """
        importance = defaultdict(float)
        
        for (entity1, entity2), count in cooccurrence_matrix.items():
            importance[entity1] += count
            importance[entity2] += count
        
        # Normalize
        if importance:
            max_importance = max(importance.values())
            for entity in importance:
                importance[entity] /= max_importance
        
        logger.debug(f"Calculated importance for {len(importance)} entities")
        return dict(importance)

    def detect_entity_clusters(
        self,
        cooccurrence_matrix: Dict[Tuple[str, str], int],
        threshold: int = None,
    ) -> List[List[str]]:
        """
        Detect clusters of frequently co-occurring entities.

        Args:
            cooccurrence_matrix: Co-occurrence matrix
            threshold: Minimum co-occurrence count for edge (uses instance default if None)

        Returns:
            List of entity clusters
        """
        # Use instance threshold if not provided
        if threshold is None:
            threshold = self.cooccurrence_threshold

        # Build adjacency list
        graph = defaultdict(set)

        for (entity1, entity2), count in cooccurrence_matrix.items():
            if count >= threshold:
                graph[entity1].add(entity2)
                graph[entity2].add(entity1)
        
        # Find connected components (clusters)
        visited = set()
        clusters = []
        
        def dfs(node, cluster):
            visited.add(node)
            cluster.append(node)
            for neighbor in graph[node]:
                if neighbor not in visited:
                    dfs(neighbor, cluster)
        
        for entity in graph:
            if entity not in visited:
                cluster = []
                dfs(entity, cluster)
                if len(cluster) > 1:
                    clusters.append(cluster)
        
        logger.debug(f"Detected {len(clusters)} entity clusters")
        return clusters

