"""Pagination utilities."""

from typing import Optional, List, Dict, Any, TypeVar, Generic
from pydantic import BaseModel, Field
import logging

from src.utils.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class PaginationParams(BaseModel):
    """Pagination parameters."""

    page: int = Field(1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(10, ge=1, le=100, description="Items per page")
    sort_by: Optional[str] = Field(None, description="Sort field")
    sort_order: Optional[str] = Field(
        "asc",
        regex="^(asc|desc)$",
        description="Sort order",
    )


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response."""

    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool


class Paginator:
    """Paginate results."""

    @staticmethod
    def paginate(
        items: List[T],
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[List[T], int]:
        """Paginate items.

        Args:
            items: Items to paginate
            page: Page number (1-indexed)
            page_size: Items per page

        Returns:
            Tuple of (paginated_items, total_count)
        """
        total = len(items)
        start = (page - 1) * page_size
        end = start + page_size

        paginated = items[start:end]

        logger.debug(
            "Items paginated",
            extra={
                "extra_fields": {
                    "page": page,
                    "page_size": page_size,
                    "total": total,
                    "returned": len(paginated),
                }
            },
        )

        return paginated, total

    @staticmethod
    def get_pagination_info(
        total: int,
        page: int,
        page_size: int,
    ) -> Dict[str, Any]:
        """Get pagination information.

        Args:
            total: Total items
            page: Current page
            page_size: Items per page

        Returns:
            Pagination info dictionary
        """
        total_pages = (total + page_size - 1) // page_size
        has_next = page < total_pages
        has_previous = page > 1

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "has_next": has_next,
            "has_previous": has_previous,
        }

    @staticmethod
    def build_offset_limit(
        page: int,
        page_size: int,
    ) -> tuple[int, int]:
        """Build SQL OFFSET and LIMIT.

        Args:
            page: Page number (1-indexed)
            page_size: Items per page

        Returns:
            Tuple of (offset, limit)
        """
        offset = (page - 1) * page_size
        limit = page_size

        return offset, limit


class CursorPaginator:
    """Cursor-based pagination for large datasets."""

    @staticmethod
    def encode_cursor(value: Any) -> str:
        """Encode cursor value.

        Args:
            value: Value to encode

        Returns:
            Encoded cursor
        """
        import base64

        return base64.b64encode(str(value).encode()).decode()

    @staticmethod
    def decode_cursor(cursor: str) -> str:
        """Decode cursor value.

        Args:
            cursor: Encoded cursor

        Returns:
            Decoded value

        Raises:
            ValueError: If cursor is invalid
        """
        import base64

        try:
            return base64.b64decode(cursor.encode()).decode()
        except Exception as e:
            logger.error(f"Failed to decode cursor: {str(e)}")
            raise ValueError("Invalid cursor")

    @staticmethod
    def paginate_with_cursor(
        items: List[Dict[str, Any]],
        cursor_field: str,
        limit: int = 10,
        after_cursor: Optional[str] = None,
    ) -> tuple[List[Dict[str, Any]], Optional[str], bool]:
        """Paginate using cursor.

        Args:
            items: Items to paginate
            cursor_field: Field to use for cursor
            limit: Items to return
            after_cursor: Cursor to start after

        Returns:
            Tuple of (items, next_cursor, has_more)
        """
        start_idx = 0

        if after_cursor:
            try:
                cursor_value = CursorPaginator.decode_cursor(after_cursor)
                # Find item with cursor value
                for i, item in enumerate(items):
                    if str(item.get(cursor_field)) == cursor_value:
                        start_idx = i + 1
                        break
            except ValueError:
                logger.warning("Invalid cursor provided")

        # Get items
        end_idx = start_idx + limit
        paginated = items[start_idx:end_idx]

        # Determine if there are more items
        has_more = end_idx < len(items)

        # Generate next cursor
        next_cursor = None
        if has_more and paginated:
            last_item = paginated[-1]
            cursor_value = last_item.get(cursor_field)
            next_cursor = CursorPaginator.encode_cursor(cursor_value)

        logger.debug(
            "Items paginated with cursor",
            extra={
                "extra_fields": {
                    "limit": limit,
                    "returned": len(paginated),
                    "has_more": has_more,
                }
            },
        )

        return paginated, next_cursor, has_more


class FilterBuilder:
    """Build filter conditions."""

    @staticmethod
    def build_filters(
        filters: Dict[str, Any],
    ) -> List[tuple[str, Any]]:
        """Build filter conditions from dictionary.

        Args:
            filters: Filter dictionary

        Returns:
            List of (field, value) tuples
        """
        conditions = []

        for field, value in filters.items():
            if value is not None:
                conditions.append((field, value))

        return conditions

    @staticmethod
    def apply_filters(
        items: List[Dict[str, Any]],
        filters: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Apply filters to items.

        Args:
            items: Items to filter
            filters: Filter conditions

        Returns:
            Filtered items
        """
        filtered = items

        for field, value in filters.items():
            if value is not None:
                filtered = [
                    item for item in filtered
                    if item.get(field) == value
                ]

        logger.debug(
            "Items filtered",
            extra={
                "extra_fields": {
                    "original_count": len(items),
                    "filtered_count": len(filtered),
                    "filter_count": len(filters),
                }
            },
        )

        return filtered

    @staticmethod
    def apply_search(
        items: List[Dict[str, Any]],
        search_term: str,
        search_fields: List[str],
    ) -> List[Dict[str, Any]]:
        """Apply search to items.

        Args:
            items: Items to search
            search_term: Search term
            search_fields: Fields to search in

        Returns:
            Matching items
        """
        search_lower = search_term.lower()
        results = []

        for item in items:
            for field in search_fields:
                value = item.get(field)
                if value and search_lower in str(value).lower():
                    results.append(item)
                    break

        logger.debug(
            "Items searched",
            extra={
                "extra_fields": {
                    "search_term": search_term,
                    "original_count": len(items),
                    "matched_count": len(results),
                }
            },
        )

        return results

