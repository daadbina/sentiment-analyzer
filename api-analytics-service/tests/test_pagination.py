"""Tests for pagination utilities."""

import pytest
from src.utils.pagination import (
    Paginator,
    CursorPaginator,
    FilterBuilder,
)


class TestPaginator:
    """Test offset-based paginator."""

    def test_paginate_first_page(self):
        """Test pagination of first page."""
        items = list(range(100))
        paginated, total = Paginator.paginate(items, page=1, page_size=10)

        assert len(paginated) == 10
        assert total == 100
        assert paginated == list(range(10))

    def test_paginate_middle_page(self):
        """Test pagination of middle page."""
        items = list(range(100))
        paginated, total = Paginator.paginate(items, page=5, page_size=10)

        assert len(paginated) == 10
        assert total == 100
        assert paginated == list(range(40, 50))

    def test_paginate_last_page(self):
        """Test pagination of last page."""
        items = list(range(100))
        paginated, total = Paginator.paginate(items, page=10, page_size=10)

        assert len(paginated) == 10
        assert total == 100
        assert paginated == list(range(90, 100))

    def test_paginate_partial_last_page(self):
        """Test pagination with partial last page."""
        items = list(range(95))
        paginated, total = Paginator.paginate(items, page=10, page_size=10)

        assert len(paginated) == 5
        assert total == 95
        assert paginated == list(range(90, 95))

    def test_get_pagination_info(self):
        """Test pagination info calculation."""
        info = Paginator.get_pagination_info(total=100, page=1, page_size=10)

        assert info["total"] == 100
        assert info["page"] == 1
        assert info["page_size"] == 10
        assert info["total_pages"] == 10
        assert info["has_next"] is True
        assert info["has_previous"] is False

    def test_get_pagination_info_last_page(self):
        """Test pagination info for last page."""
        info = Paginator.get_pagination_info(total=100, page=10, page_size=10)

        assert info["total"] == 100
        assert info["page"] == 10
        assert info["total_pages"] == 10
        assert info["has_next"] is False
        assert info["has_previous"] is True

    def test_build_offset_limit(self):
        """Test offset/limit calculation."""
        offset, limit = Paginator.build_offset_limit(page=1, page_size=10)

        assert offset == 0
        assert limit == 10

    def test_build_offset_limit_page_5(self):
        """Test offset/limit for page 5."""
        offset, limit = Paginator.build_offset_limit(page=5, page_size=10)

        assert offset == 40
        assert limit == 10


class TestCursorPaginator:
    """Test cursor-based paginator."""

    def test_encode_decode_cursor(self):
        """Test cursor encoding and decoding."""
        value = "user123"
        encoded = CursorPaginator.encode_cursor(value)
        decoded = CursorPaginator.decode_cursor(encoded)

        assert decoded == value

    def test_paginate_with_cursor_first_page(self):
        """Test cursor pagination first page."""
        items = [
            {"id": "1", "name": "Alice"},
            {"id": "2", "name": "Bob"},
            {"id": "3", "name": "Charlie"},
            {"id": "4", "name": "David"},
            {"id": "5", "name": "Eve"},
        ]

        paginated, next_cursor, has_more = CursorPaginator.paginate_with_cursor(
            items,
            cursor_field="id",
            limit=2,
        )

        assert len(paginated) == 2
        assert paginated[0]["id"] == "1"
        assert paginated[1]["id"] == "2"
        assert has_more is True
        assert next_cursor is not None

    def test_paginate_with_cursor_next_page(self):
        """Test cursor pagination next page."""
        items = [
            {"id": "1", "name": "Alice"},
            {"id": "2", "name": "Bob"},
            {"id": "3", "name": "Charlie"},
            {"id": "4", "name": "David"},
            {"id": "5", "name": "Eve"},
        ]

        # First page
        paginated1, next_cursor, _ = CursorPaginator.paginate_with_cursor(
            items,
            cursor_field="id",
            limit=2,
        )

        # Second page
        paginated2, _, has_more = CursorPaginator.paginate_with_cursor(
            items,
            cursor_field="id",
            limit=2,
            after_cursor=next_cursor,
        )

        assert len(paginated2) == 2
        assert paginated2[0]["id"] == "3"
        assert paginated2[1]["id"] == "4"
        assert has_more is True

    def test_paginate_with_cursor_last_page(self):
        """Test cursor pagination last page."""
        items = [
            {"id": "1", "name": "Alice"},
            {"id": "2", "name": "Bob"},
            {"id": "3", "name": "Charlie"},
        ]

        paginated, next_cursor, has_more = CursorPaginator.paginate_with_cursor(
            items,
            cursor_field="id",
            limit=5,
        )

        assert len(paginated) == 3
        assert has_more is False
        assert next_cursor is None


class TestFilterBuilder:
    """Test filter builder."""

    def test_build_filters(self):
        """Test filter building."""
        filters = {"status": "active", "category": "A"}
        conditions = FilterBuilder.build_filters(filters)

        assert len(conditions) == 2
        assert ("status", "active") in conditions
        assert ("category", "A") in conditions

    def test_build_filters_with_none(self):
        """Test filter building with None values."""
        filters = {"status": "active", "category": None}
        conditions = FilterBuilder.build_filters(filters)

        assert len(conditions) == 1
        assert ("status", "active") in conditions

    def test_apply_filters(self):
        """Test applying filters."""
        items = [
            {"id": "1", "status": "active", "category": "A"},
            {"id": "2", "status": "inactive", "category": "A"},
            {"id": "3", "status": "active", "category": "B"},
        ]

        filtered = FilterBuilder.apply_filters(
            items,
            {"status": "active"},
        )

        assert len(filtered) == 2
        assert all(item["status"] == "active" for item in filtered)

    def test_apply_multiple_filters(self):
        """Test applying multiple filters."""
        items = [
            {"id": "1", "status": "active", "category": "A"},
            {"id": "2", "status": "inactive", "category": "A"},
            {"id": "3", "status": "active", "category": "B"},
        ]

        filtered = FilterBuilder.apply_filters(
            items,
            {"status": "active", "category": "A"},
        )

        assert len(filtered) == 1
        assert filtered[0]["id"] == "1"

    def test_apply_search(self):
        """Test search functionality."""
        items = [
            {"id": "1", "name": "Alice", "email": "alice@example.com"},
            {"id": "2", "name": "Bob", "email": "bob@example.com"},
            {"id": "3", "name": "Charlie", "email": "charlie@example.com"},
        ]

        results = FilterBuilder.apply_search(
            items,
            "alice",
            ["name", "email"],
        )

        assert len(results) == 1
        assert results[0]["id"] == "1"

    def test_apply_search_multiple_fields(self):
        """Test search across multiple fields."""
        items = [
            {"id": "1", "name": "Alice", "email": "alice@example.com"},
            {"id": "2", "name": "Bob", "email": "bob@example.com"},
            {"id": "3", "name": "Charlie", "email": "charlie@example.com"},
        ]

        results = FilterBuilder.apply_search(
            items,
            "example",
            ["name", "email"],
        )

        assert len(results) == 3

