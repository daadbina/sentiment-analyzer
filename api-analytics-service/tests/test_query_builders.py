"""Tests for query builders."""

import pytest
from src.queries import SQLBuilder, CypherBuilder, DataAggregator


class TestSQLBuilder:
    """Test SQL query builder."""

    def test_select_all(self):
        """Test SELECT * query."""
        builder = SQLBuilder("users")
        query, params = builder.build()

        assert "SELECT *" in query
        assert "FROM users" in query
        assert params == []

    def test_select_specific_fields(self):
        """Test SELECT specific fields."""
        builder = SQLBuilder("users")
        builder.select("id", "name", "email")
        query, params = builder.build()

        assert "SELECT id, name, email" in query
        assert "FROM users" in query

    def test_where_condition(self):
        """Test WHERE condition."""
        builder = SQLBuilder("users")
        builder.where("id = $1", 123)
        query, params = builder.build()

        assert "WHERE id = $1" in query
        assert params == [123]

    def test_multiple_where_conditions(self):
        """Test multiple WHERE conditions."""
        builder = SQLBuilder("users")
        builder.where("id = $1", 123)
        builder.where("status = $2", "active")
        query, params = builder.build()

        assert "WHERE id = $1 AND status = $2" in query
        assert params == [123, "active"]

    def test_order_by(self):
        """Test ORDER BY clause."""
        builder = SQLBuilder("users")
        builder.order_by("created_at", "DESC")
        query, params = builder.build()

        assert "ORDER BY created_at DESC" in query

    def test_limit_offset(self):
        """Test LIMIT and OFFSET."""
        builder = SQLBuilder("users")
        builder.limit(10)
        builder.offset(20)
        query, params = builder.build()

        assert "LIMIT 10" in query
        assert "OFFSET 20" in query

    def test_count_query(self):
        """Test COUNT query."""
        builder = SQLBuilder("users")
        builder.where("status = $1", "active")
        query, params = builder.build_count()

        assert "SELECT COUNT(*)" in query
        assert "FROM users" in query
        assert "WHERE status = $1" in query


class TestCypherBuilder:
    """Test Cypher query builder."""

    def test_match_return(self):
        """Test MATCH and RETURN."""
        builder = CypherBuilder()
        builder.match("(n:User)")
        builder.return_fields("n")
        query, params = builder.build()

        assert "MATCH (n:User)" in query
        assert "RETURN n" in query

    def test_where_condition(self):
        """Test WHERE condition."""
        builder = CypherBuilder()
        builder.match("(n:User)")
        builder.where("n.id = $user_id")
        builder.param("user_id", "123")
        builder.return_fields("n")
        query, params = builder.build()

        assert "WHERE n.id = $user_id" in query
        assert params["user_id"] == "123"

    def test_order_by_limit(self):
        """Test ORDER BY and LIMIT."""
        builder = CypherBuilder()
        builder.match("(n:User)")
        builder.order_by("n.created_at", "DESC")
        builder.limit(10)
        builder.return_fields("n")
        query, params = builder.build()

        assert "ORDER BY n.created_at DESC" in query
        assert "LIMIT 10" in query


class TestDataAggregator:
    """Test data aggregator."""

    def test_merge_results(self):
        """Test merging results."""
        set1 = [{"id": "1", "name": "Alice"}]
        set2 = [{"id": "1", "age": 30}]

        merged = DataAggregator.merge_results(set1, set2, key="id")

        assert len(merged) == 1
        assert merged[0]["id"] == "1"
        assert merged[0]["name"] == "Alice"
        assert merged[0]["age"] == 30

    def test_group_by(self):
        """Test grouping results."""
        data = [
            {"category": "A", "value": 10},
            {"category": "A", "value": 20},
            {"category": "B", "value": 30},
        ]

        grouped = DataAggregator.group_by(data, "category")

        assert len(grouped) == 2
        assert len(grouped["A"]) == 2
        assert len(grouped["B"]) == 1

    def test_filter_results(self):
        """Test filtering results."""
        data = [
            {"id": "1", "status": "active"},
            {"id": "2", "status": "inactive"},
            {"id": "3", "status": "active"},
        ]

        filtered = DataAggregator.filter_results(data, {"status": "active"})

        assert len(filtered) == 2
        assert all(item["status"] == "active" for item in filtered)

    def test_sort_results(self):
        """Test sorting results."""
        data = [
            {"id": "3", "name": "Charlie"},
            {"id": "1", "name": "Alice"},
            {"id": "2", "name": "Bob"},
        ]

        sorted_data = DataAggregator.sort_results(data, "id")

        assert sorted_data[0]["id"] == "1"
        assert sorted_data[1]["id"] == "2"
        assert sorted_data[2]["id"] == "3"

    def test_paginate(self):
        """Test pagination."""
        data = list(range(100))

        page1, total = DataAggregator.paginate(data, page=1, page_size=10)

        assert len(page1) == 10
        assert total == 100
        assert page1 == list(range(10))

    def test_aggregate(self):
        """Test aggregation."""
        data = [
            {"category": "A", "value": 10},
            {"category": "A", "value": 20},
            {"category": "B", "value": 30},
        ]

        aggregated = DataAggregator.aggregate(
            data,
            "category",
            {"value": "sum"},
        )

        assert len(aggregated) == 2
        assert aggregated[0]["value_sum"] == 30
        assert aggregated[1]["value_sum"] == 30

