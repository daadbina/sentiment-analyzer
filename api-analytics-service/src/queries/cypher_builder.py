"""Cypher query builder for Neo4j."""

from typing import Optional, List, Dict, Any, Tuple


class CypherBuilder:
    """Build Cypher queries for Neo4j."""

    def __init__(self):
        """Initialize Cypher builder."""
        self.match_clauses: List[str] = []
        self.where_conditions: List[str] = []
        self.return_fields: List[str] = []
        self.order_by_fields: List[Tuple[str, str]] = []
        self.limit_value: Optional[int] = None
        self.skip_value: Optional[int] = None
        self.parameters: Dict[str, Any] = {}

    def match(self, pattern: str) -> "CypherBuilder":
        """Add MATCH clause.

        Args:
            pattern: Match pattern

        Returns:
            Self for chaining
        """
        self.match_clauses.append(pattern)
        return self

    def where(self, condition: str) -> "CypherBuilder":
        """Add WHERE condition.

        Args:
            condition: WHERE condition

        Returns:
            Self for chaining
        """
        self.where_conditions.append(condition)
        return self

    def return_fields(self, *fields: str) -> "CypherBuilder":
        """Set RETURN fields.

        Args:
            *fields: Field names

        Returns:
            Self for chaining
        """
        self.return_fields = list(fields)
        return self

    def order_by(self, field: str, order: str = "ASC") -> "CypherBuilder":
        """Add ORDER BY clause.

        Args:
            field: Field name
            order: Sort order (ASC or DESC)

        Returns:
            Self for chaining
        """
        self.order_by_fields.append((field, order))
        return self

    def limit(self, limit: int) -> "CypherBuilder":
        """Set LIMIT.

        Args:
            limit: Limit value

        Returns:
            Self for chaining
        """
        self.limit_value = limit
        return self

    def skip(self, skip: int) -> "CypherBuilder":
        """Set SKIP.

        Args:
            skip: Skip value

        Returns:
            Self for chaining
        """
        self.skip_value = skip
        return self

    def param(self, name: str, value: Any) -> "CypherBuilder":
        """Add parameter.

        Args:
            name: Parameter name
            value: Parameter value

        Returns:
            Self for chaining
        """
        self.parameters[name] = value
        return self

    def build(self) -> Tuple[str, Dict[str, Any]]:
        """Build Cypher query.

        Returns:
            Tuple of (query, parameters)
        """
        query_parts = []

        # Add MATCH clauses
        if self.match_clauses:
            query_parts.append("MATCH " + ", ".join(self.match_clauses))

        # Add WHERE clauses
        if self.where_conditions:
            query_parts.append("WHERE " + " AND ".join(self.where_conditions))

        # Add RETURN clause
        if self.return_fields:
            query_parts.append("RETURN " + ", ".join(self.return_fields))

        # Add ORDER BY clause
        if self.order_by_fields:
            order_parts = [
                f"{field} {order}"
                for field, order in self.order_by_fields
            ]
            query_parts.append("ORDER BY " + ", ".join(order_parts))

        # Add SKIP clause
        if self.skip_value is not None:
            query_parts.append(f"SKIP {self.skip_value}")

        # Add LIMIT clause
        if self.limit_value is not None:
            query_parts.append(f"LIMIT {self.limit_value}")

        query = "\n".join(query_parts)

        return query, self.parameters


class PathFinder:
    """Find paths between nodes in graph."""

    def __init__(self):
        """Initialize path finder."""
        self.from_node: Optional[str] = None
        self.to_node: Optional[str] = None
        self.max_length: int = 5
        self.relationship_types: List[str] = []
        self.parameters: Dict[str, Any] = {}

    def from_node_id(self, node_id: str) -> "PathFinder":
        """Set source node.

        Args:
            node_id: Node ID

        Returns:
            Self for chaining
        """
        self.from_node = node_id
        self.parameters["from_id"] = node_id
        return self

    def to_node_id(self, node_id: str) -> "PathFinder":
        """Set target node.

        Args:
            node_id: Node ID

        Returns:
            Self for chaining
        """
        self.to_node = node_id
        self.parameters["to_id"] = node_id
        return self

    def max_path_length(self, length: int) -> "PathFinder":
        """Set maximum path length.

        Args:
            length: Maximum length

        Returns:
            Self for chaining
        """
        self.max_length = length
        return self

    def with_relationship_types(self, *types: str) -> "PathFinder":
        """Filter by relationship types.

        Args:
            *types: Relationship types

        Returns:
            Self for chaining
        """
        self.relationship_types = list(types)
        return self

    def build(self) -> Tuple[str, Dict[str, Any]]:
        """Build path finding query.

        Returns:
            Tuple of (query, parameters)
        """
        rel_filter = ""
        if self.relationship_types:
            rel_types = "|".join(self.relationship_types)
            rel_filter = f":{rel_types}"

        query = f"""
            MATCH path = shortestPath((from)-[{rel_filter}*1..{self.max_length}]-(to))
            WHERE from.id = $from_id AND to.id = $to_id
            RETURN path
        """

        return query, self.parameters


class CentralityCalculator:
    """Calculate graph centrality metrics."""

    @staticmethod
    def degree_centrality(node_label: str) -> Tuple[str, Dict[str, Any]]:
        """Calculate degree centrality.

        Args:
            node_label: Node label

        Returns:
            Tuple of (query, parameters)
        """
        query = f"""
            MATCH (n:{node_label})
            RETURN n.id, size((n)--()) as degree
            ORDER BY degree DESC
        """
        return query, {}

    @staticmethod
    def betweenness_centrality(
        node_label: str,
        limit: int = 10,
    ) -> Tuple[str, Dict[str, Any]]:
        """Calculate betweenness centrality.

        Args:
            node_label: Node label
            limit: Result limit

        Returns:
            Tuple of (query, parameters)
        """
        query = f"""
            MATCH (n:{node_label})
            WITH n, size((n)--()) as degree
            RETURN n.id, degree
            ORDER BY degree DESC
            LIMIT {limit}
        """
        return query, {}

    @staticmethod
    def closeness_centrality(
        node_label: str,
        limit: int = 10,
    ) -> Tuple[str, Dict[str, Any]]:
        """Calculate closeness centrality.

        Args:
            node_label: Node label
            limit: Result limit

        Returns:
            Tuple of (query, parameters)
        """
        query = f"""
            MATCH (n:{node_label})
            WITH n, size((n)--()) as connections
            RETURN n.id, connections
            ORDER BY connections DESC
            LIMIT {limit}
        """
        return query, {}

