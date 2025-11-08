"""Data aggregation from multiple sources."""

from typing import List, Dict, Any, Optional
import logging

from src.utils.logging import get_logger

logger = get_logger(__name__)


class DataAggregator:
    """Aggregate data from multiple sources."""

    @staticmethod
    def merge_results(
        *result_sets: List[Dict[str, Any]],
        key: str = "id",
    ) -> List[Dict[str, Any]]:
        """Merge multiple result sets by key.

        Args:
            *result_sets: Result sets to merge
            key: Key to merge on

        Returns:
            Merged results
        """
        merged: Dict[str, Dict[str, Any]] = {}

        for result_set in result_sets:
            for item in result_set:
                item_key = item.get(key)
                if item_key:
                    if item_key not in merged:
                        merged[item_key] = {}
                    merged[item_key].update(item)

        return list(merged.values())

    @staticmethod
    def join_results(
        left: List[Dict[str, Any]],
        right: List[Dict[str, Any]],
        left_key: str,
        right_key: str,
        join_type: str = "inner",
    ) -> List[Dict[str, Any]]:
        """Join two result sets.

        Args:
            left: Left result set
            right: Right result set
            left_key: Left join key
            right_key: Right join key
            join_type: Join type (inner, left, right, outer)

        Returns:
            Joined results
        """
        result = []

        # Create lookup for right set
        right_lookup: Dict[Any, List[Dict[str, Any]]] = {}
        for item in right:
            key = item.get(right_key)
            if key:
                if key not in right_lookup:
                    right_lookup[key] = []
                right_lookup[key].append(item)

        # Perform join
        for left_item in left:
            left_key_val = left_item.get(left_key)
            right_items = right_lookup.get(left_key_val, [])

            if right_items:
                for right_item in right_items:
                    merged = {**left_item, **right_item}
                    result.append(merged)
            elif join_type in ["left", "outer"]:
                result.append(left_item)

        # Add unmatched right items for outer join
        if join_type in ["right", "outer"]:
            matched_keys = {item.get(left_key) for item in left}
            for key, items in right_lookup.items():
                if key not in matched_keys:
                    result.extend(items)

        return result

    @staticmethod
    def group_by(
        data: List[Dict[str, Any]],
        key: str,
    ) -> Dict[Any, List[Dict[str, Any]]]:
        """Group results by key.

        Args:
            data: Data to group
            key: Grouping key

        Returns:
            Grouped data
        """
        grouped: Dict[Any, List[Dict[str, Any]]] = {}

        for item in data:
            group_key = item.get(key)
            if group_key:
                if group_key not in grouped:
                    grouped[group_key] = []
                grouped[group_key].append(item)

        return grouped

    @staticmethod
    def aggregate(
        data: List[Dict[str, Any]],
        group_key: str,
        aggregations: Dict[str, str],
    ) -> List[Dict[str, Any]]:
        """Aggregate data with functions.

        Args:
            data: Data to aggregate
            group_key: Grouping key
            aggregations: Dict of {field: function} (count, sum, avg, min, max)

        Returns:
            Aggregated results
        """
        grouped = DataAggregator.group_by(data, group_key)
        result = []

        for group_key_val, items in grouped.items():
            agg_item = {group_key: group_key_val}

            for field, func in aggregations.items():
                values = [item.get(field) for item in items if field in item]

                if func == "count":
                    agg_item[f"{field}_count"] = len(values)
                elif func == "sum":
                    agg_item[f"{field}_sum"] = sum(
                        v for v in values if isinstance(v, (int, float))
                    )
                elif func == "avg":
                    numeric_values = [
                        v for v in values if isinstance(v, (int, float))
                    ]
                    if numeric_values:
                        agg_item[f"{field}_avg"] = sum(numeric_values) / len(
                            numeric_values
                        )
                elif func == "min":
                    numeric_values = [
                        v for v in values if isinstance(v, (int, float))
                    ]
                    if numeric_values:
                        agg_item[f"{field}_min"] = min(numeric_values)
                elif func == "max":
                    numeric_values = [
                        v for v in values if isinstance(v, (int, float))
                    ]
                    if numeric_values:
                        agg_item[f"{field}_max"] = max(numeric_values)

            result.append(agg_item)

        return result

    @staticmethod
    def filter_results(
        data: List[Dict[str, Any]],
        filters: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Filter results by conditions.

        Args:
            data: Data to filter
            filters: Dict of {field: value} for exact match

        Returns:
            Filtered results
        """
        result = []

        for item in data:
            match = True
            for field, value in filters.items():
                if item.get(field) != value:
                    match = False
                    break
            if match:
                result.append(item)

        return result

    @staticmethod
    def sort_results(
        data: List[Dict[str, Any]],
        key: str,
        reverse: bool = False,
    ) -> List[Dict[str, Any]]:
        """Sort results by key.

        Args:
            data: Data to sort
            key: Sort key
            reverse: Sort in reverse order

        Returns:
            Sorted results
        """
        return sorted(
            data,
            key=lambda x: x.get(key, ""),
            reverse=reverse,
        )

    @staticmethod
    def paginate(
        data: List[Dict[str, Any]],
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[List[Dict[str, Any]], int]:
        """Paginate results.

        Args:
            data: Data to paginate
            page: Page number (1-indexed)
            page_size: Items per page

        Returns:
            Tuple of (paginated_data, total_count)
        """
        total = len(data)
        start = (page - 1) * page_size
        end = start + page_size

        return data[start:end], total

    @staticmethod
    def flatten(
        data: List[Dict[str, Any]],
        prefix: str = "",
    ) -> List[Dict[str, Any]]:
        """Flatten nested dictionaries.

        Args:
            data: Data to flatten
            prefix: Key prefix for nested fields

        Returns:
            Flattened data
        """
        result = []

        for item in data:
            flattened = {}
            DataAggregator._flatten_dict(item, flattened, prefix)
            result.append(flattened)

        return result

    @staticmethod
    def _flatten_dict(
        d: Dict[str, Any],
        result: Dict[str, Any],
        prefix: str = "",
    ) -> None:
        """Recursively flatten dictionary.

        Args:
            d: Dictionary to flatten
            result: Result dictionary
            prefix: Key prefix
        """
        for key, value in d.items():
            new_key = f"{prefix}_{key}" if prefix else key

            if isinstance(value, dict):
                DataAggregator._flatten_dict(value, result, new_key)
            elif isinstance(value, list):
                result[new_key] = str(value)
            else:
                result[new_key] = value

