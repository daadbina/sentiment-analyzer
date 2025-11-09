"""SQL query builder with parameterized queries."""

from typing import Optional, List, Dict, Any, Tuple
from enum import Enum


class SortOrder(str, Enum):
    """Sort order enumeration."""

    ASC = "ASC"
    DESC = "DESC"


class SQLBuilder:
    """Build parameterized SQL queries safely."""

    def __init__(self, table: str):
        """Initialize SQL builder.

        Args:
            table: Table name
        """
        self.table = table
        self.select_fields: List[str] = ["*"]
        self.where_conditions: List[str] = []
        self.where_params: List[Any] = []
        self.order_by_fields: List[Tuple[str, SortOrder]] = []
        self.limit_value: Optional[int] = None
        self.offset_value: Optional[int] = None
        self.joins: List[str] = []

    def select(self, *fields: str) -> "SQLBuilder":
        """Set SELECT fields.

        Args:
            *fields: Field names

        Returns:
            Self for chaining
        """
        if fields:
            self.select_fields = list(fields)
        return self

    def where(self, condition: str, *params: Any) -> "SQLBuilder":
        """Add WHERE condition.

        Args:
            condition: WHERE condition (use $1, $2, etc. for parameters)
            *params: Parameter values

        Returns:
            Self for chaining
        """
        self.where_conditions.append(condition)
        self.where_params.extend(params)
        return self

    def order_by(
        self,
        field: str,
        order: SortOrder | str = SortOrder.ASC,
    ) -> "SQLBuilder":
        """Add ORDER BY clause.

        Args:
            field: Field name
            order: Sort order (SortOrder enum or string "ASC"/"DESC")

        Returns:
            Self for chaining
        """
        # Convert string to enum if needed
        if isinstance(order, str):
            order = SortOrder(order.upper())

        self.order_by_fields.append((field, order))
        return self

    def limit(self, limit: int) -> "SQLBuilder":
        """Set LIMIT.

        Args:
            limit: Limit value

        Returns:
            Self for chaining
        """
        self.limit_value = limit
        return self

    def offset(self, offset: int) -> "SQLBuilder":
        """Set OFFSET.

        Args:
            offset: Offset value

        Returns:
            Self for chaining
        """
        self.offset_value = offset
        return self

    def join(self, join_clause: str) -> "SQLBuilder":
        """Add JOIN clause.

        Args:
            join_clause: JOIN clause

        Returns:
            Self for chaining
        """
        self.joins.append(join_clause)
        return self

    def build(self) -> Tuple[str, List[Any]]:
        """Build SQL query.

        Returns:
            Tuple of (query, parameters)
        """
        # Build SELECT clause
        select_clause = f"SELECT {', '.join(self.select_fields)}"

        # Build FROM clause
        from_clause = f"FROM {self.table}"

        # Build JOIN clauses
        join_clause = " ".join(self.joins) if self.joins else ""

        # Build WHERE clause
        where_clause = ""
        if self.where_conditions:
            where_clause = "WHERE " + " AND ".join(self.where_conditions)

        # Build ORDER BY clause
        order_clause = ""
        if self.order_by_fields:
            order_parts = [
                f"{field} {order.value}"
                for field, order in self.order_by_fields
            ]
            order_clause = "ORDER BY " + ", ".join(order_parts)

        # Build LIMIT clause
        limit_clause = ""
        if self.limit_value is not None:
            limit_clause = f"LIMIT {self.limit_value}"

        # Build OFFSET clause
        offset_clause = ""
        if self.offset_value is not None:
            offset_clause = f"OFFSET {self.offset_value}"

        # Combine all parts
        query_parts = [
            select_clause,
            from_clause,
            join_clause,
            where_clause,
            order_clause,
            limit_clause,
            offset_clause,
        ]

        query = " ".join(part for part in query_parts if part)

        return query, self.where_params

    def build_count(self) -> Tuple[str, List[Any]]:
        """Build COUNT query.

        Returns:
            Tuple of (query, parameters)
        """
        # Build FROM clause
        from_clause = f"FROM {self.table}"

        # Build JOIN clauses
        join_clause = " ".join(self.joins) if self.joins else ""

        # Build WHERE clause
        where_clause = ""
        if self.where_conditions:
            where_clause = "WHERE " + " AND ".join(self.where_conditions)

        # Combine all parts
        query_parts = [
            "SELECT COUNT(*)",
            from_clause,
            join_clause,
            where_clause,
        ]

        query = " ".join(part for part in query_parts if part)

        return query, self.where_params


class InsertBuilder:
    """Build INSERT queries."""

    def __init__(self, table: str):
        """Initialize insert builder.

        Args:
            table: Table name
        """
        self.table = table
        self.fields: List[str] = []
        self.values: List[Any] = []

    def add_field(self, field: str, value: Any) -> "InsertBuilder":
        """Add field and value.

        Args:
            field: Field name
            value: Field value

        Returns:
            Self for chaining
        """
        self.fields.append(field)
        self.values.append(value)
        return self

    def build(self) -> Tuple[str, List[Any]]:
        """Build INSERT query.

        Returns:
            Tuple of (query, parameters)
        """
        placeholders = ", ".join([f"${i+1}" for i in range(len(self.fields))])
        fields_str = ", ".join(self.fields)

        query = f"INSERT INTO {self.table} ({fields_str}) VALUES ({placeholders})"

        return query, self.values


class UpdateBuilder:
    """Build UPDATE queries."""

    def __init__(self, table: str):
        """Initialize update builder.

        Args:
            table: Table name
        """
        self.table = table
        self.set_fields: List[str] = []
        self.set_values: List[Any] = []
        self.where_conditions: List[str] = []
        self.where_params: List[Any] = []

    def set(self, field: str, value: Any) -> "UpdateBuilder":
        """Add SET clause.

        Args:
            field: Field name
            value: Field value

        Returns:
            Self for chaining
        """
        self.set_fields.append(field)
        self.set_values.append(value)
        return self

    def where(self, condition: str, *params: Any) -> "UpdateBuilder":
        """Add WHERE condition.

        Args:
            condition: WHERE condition
            *params: Parameter values

        Returns:
            Self for chaining
        """
        self.where_conditions.append(condition)
        self.where_params.extend(params)
        return self

    def build(self) -> Tuple[str, List[Any]]:
        """Build UPDATE query.

        Returns:
            Tuple of (query, parameters)
        """
        set_parts = [
            f"{field} = ${i+1}"
            for i, field in enumerate(self.set_fields)
        ]
        set_clause = ", ".join(set_parts)

        where_clause = ""
        if self.where_conditions:
            where_offset = len(self.set_values)
            where_parts = []
            for i, cond in enumerate(self.where_conditions):
                # Replace placeholders in condition
                where_parts.append(cond)
            where_clause = "WHERE " + " AND ".join(where_parts)

        query = f"UPDATE {self.table} SET {set_clause}"
        if where_clause:
            query += f" {where_clause}"

        params = self.set_values + self.where_params

        return query, params

