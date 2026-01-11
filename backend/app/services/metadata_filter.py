"""
Metadata filtering service for vector search.

Implements Issue #24: Filter search results by metadata fields.

This module provides:
- MongoDB-style filter operators ($eq, $ne, $gt, $gte, $lt, $lte, $in, $nin, $exists, $contains)
- Filter validation and parsing with proper error codes
- Metadata matching logic applied AFTER similarity search
- Type-safe comparisons

Per PRD Section 6 (Compliance & audit):
- Enables precise filtering of agent memory and events
- Supports compliance queries and audit trails
- Ensures deterministic and reproducible filtering

Supported MongoDB-style operators:
- $eq: equals (default if no operator)
- $ne: not equals
- $gt, $gte, $lt, $lte: numeric comparisons
- $in: value in array
- $nin: value not in array
- $exists: field exists/doesn't exist
- $contains: string contains substring (extension)
"""
from typing import Dict, Any, List, Optional
import logging

from app.core.errors import InvalidMetadataFilterError

logger = logging.getLogger(__name__)


class MetadataFilterOperator:
    """
    Supported MongoDB-style metadata filter operators.

    Issue #24: All operators use MongoDB-style $ prefix in the API.
    Internal operator names (without $) are used for matching logic.
    """
    # Core MongoDB operators
    EQ = "eq"  # Exact match (default if no operator specified)
    NE = "ne"  # Not equal to value
    GT = "gt"  # Greater than (numeric)
    GTE = "gte"  # Greater than or equal (numeric)
    LT = "lt"  # Less than (numeric)
    LTE = "lte"  # Less than or equal (numeric)
    IN = "in"  # Value in array
    NIN = "nin"  # Value not in array
    EXISTS = "exists"  # Field exists/doesn't exist (boolean)

    # Extension operators
    CONTAINS = "contains"  # String contains substring

    # Legacy aliases for backward compatibility
    EQUALS = "eq"
    NOT_EQUALS = "ne"


# All supported operators (internal names without $)
SUPPORTED_OPERATORS = {
    MetadataFilterOperator.EQ,
    MetadataFilterOperator.NE,
    MetadataFilterOperator.GT,
    MetadataFilterOperator.GTE,
    MetadataFilterOperator.LT,
    MetadataFilterOperator.LTE,
    MetadataFilterOperator.IN,
    MetadataFilterOperator.NIN,
    MetadataFilterOperator.EXISTS,
    MetadataFilterOperator.CONTAINS,
    # Legacy aliases
    "equals",
    "not_equals",
}


class MetadataFilter:
    """
    Service for filtering vectors by metadata.

    Issue #24 Requirements:
    - Support common filter operations (equals, contains, in)
    - Apply filters AFTER similarity search
    - Return only vectors matching all metadata criteria
    - Validate filter format
    - Handle cases with no matches gracefully

    Filter Format Examples:
    1. Simple equality (default):
       {"agent_id": "agent_1"}

    2. Explicit operators:
       {
           "agent_id": {"$eq": "agent_1"},
           "score": {"$gte": 0.8},
           "tags": {"$in": ["fintech", "compliance"]}
       }

    3. Multiple conditions (AND logic):
       {
           "agent_id": "agent_1",
           "source": "memory",
           "status": {"$in": ["active", "pending"]}
       }
    """

    @staticmethod
    def validate_filter(metadata_filter: Optional[Dict[str, Any]]) -> None:
        """
        Validate metadata filter format.

        Issue #24: Validates MongoDB-style filter format.
        Raises InvalidMetadataFilterError (422 INVALID_METADATA_FILTER) for invalid formats.

        Args:
            metadata_filter: Filter dictionary to validate

        Raises:
            InvalidMetadataFilterError: If filter format is invalid (HTTP 422)
        """
        if metadata_filter is None:
            return

        if not isinstance(metadata_filter, dict):
            raise InvalidMetadataFilterError(
                "metadata_filter must be a dictionary"
            )

        if not metadata_filter:
            # Empty dict is valid - no filtering
            return

        # Validate each filter condition
        for field, condition in metadata_filter.items():
            if not isinstance(field, str):
                raise InvalidMetadataFilterError(
                    f"Filter field must be a string, got: {type(field).__name__}"
                )

            if field.startswith("$"):
                raise InvalidMetadataFilterError(
                    f"Top-level operator '{field}' not supported. "
                    "Use field-level operators like: {'field': {'$eq': 'value'}}"
                )

            # Condition can be:
            # 1. Direct value (implies equals): {"field": "value"}
            # 2. Operator dict: {"field": {"$eq": "value"}}
            if isinstance(condition, dict):
                # Validate operator format
                for operator, value in condition.items():
                    if not operator.startswith("$"):
                        raise InvalidMetadataFilterError(
                            f"Operator must start with '$', got: {operator}. "
                            f"Example: {{'$eq': 'value'}}"
                        )

                    # Remove $ prefix for validation
                    op_name = operator[1:]
                    if op_name not in SUPPORTED_OPERATORS:
                        supported_ops = ["$eq", "$ne", "$gt", "$gte", "$lt", "$lte", "$in", "$nin", "$exists", "$contains"]
                        raise InvalidMetadataFilterError(
                            f"Unsupported operator: {operator}. "
                            f"Supported operators: {', '.join(supported_ops)}"
                        )

                    # Validate operator-specific constraints
                    if op_name == MetadataFilterOperator.IN:
                        if not isinstance(value, list):
                            raise InvalidMetadataFilterError(
                                f"Operator '$in' requires a list value, got: {type(value).__name__}"
                            )
                    elif op_name == MetadataFilterOperator.NIN:
                        if not isinstance(value, list):
                            raise InvalidMetadataFilterError(
                                f"Operator '$nin' requires a list value, got: {type(value).__name__}"
                            )
                    elif op_name in {
                        MetadataFilterOperator.GT,
                        MetadataFilterOperator.GTE,
                        MetadataFilterOperator.LT,
                        MetadataFilterOperator.LTE
                    }:
                        if not isinstance(value, (int, float)):
                            raise InvalidMetadataFilterError(
                                f"Operator '{operator}' requires a numeric value, got: {type(value).__name__}"
                            )
                    elif op_name == MetadataFilterOperator.EXISTS:
                        if not isinstance(value, bool):
                            raise InvalidMetadataFilterError(
                                f"Operator '$exists' requires a boolean value, got: {type(value).__name__}"
                            )
                    elif op_name == MetadataFilterOperator.CONTAINS:
                        if not isinstance(value, str):
                            raise InvalidMetadataFilterError(
                                f"Operator '$contains' requires a string value, got: {type(value).__name__}"
                            )

    @staticmethod
    def matches_filter(
        vector_metadata: Dict[str, Any],
        metadata_filter: Optional[Dict[str, Any]]
    ) -> bool:
        """
        Check if vector metadata matches all filter conditions.

        Issue #24: Apply metadata filters AFTER similarity search.

        Args:
            vector_metadata: Metadata from the vector
            metadata_filter: Filter conditions to apply

        Returns:
            True if vector matches all conditions, False otherwise
        """
        if not metadata_filter:
            # No filter means all vectors match
            return True

        # All conditions must match (AND logic)
        for field, condition in metadata_filter.items():
            if not MetadataFilter._matches_field_condition(
                vector_metadata, field, condition
            ):
                return False

        return True

    @staticmethod
    def _matches_field_condition(
        vector_metadata: Dict[str, Any],
        field: str,
        condition: Any
    ) -> bool:
        """
        Check if a single field matches its condition.

        Issue #24: Supports all MongoDB-style operators.

        Args:
            vector_metadata: Metadata from the vector
            field: Field name to check
            condition: Condition value or operator dict

        Returns:
            True if field matches condition, False otherwise
        """
        # Get field value from metadata
        field_value = vector_metadata.get(field)

        # Handle direct value (implies equals)
        if not isinstance(condition, dict):
            return MetadataFilter._compare_equals(field_value, condition)

        # Handle operator-based conditions
        for operator, expected_value in condition.items():
            op_name = operator[1:]  # Remove $ prefix

            # Handle $eq and legacy 'equals'
            if op_name in (MetadataFilterOperator.EQ, "equals"):
                if not MetadataFilter._compare_equals(field_value, expected_value):
                    return False

            # Handle $ne and legacy 'not_equals'
            elif op_name in (MetadataFilterOperator.NE, "not_equals"):
                if MetadataFilter._compare_equals(field_value, expected_value):
                    return False

            elif op_name == MetadataFilterOperator.CONTAINS:
                if not MetadataFilter._compare_contains(field_value, expected_value):
                    return False

            elif op_name == MetadataFilterOperator.IN:
                if not MetadataFilter._compare_in(field_value, expected_value):
                    return False

            # Handle $nin (not in array) - Issue #24
            elif op_name == MetadataFilterOperator.NIN:
                if not MetadataFilter._compare_nin(field_value, expected_value):
                    return False

            elif op_name == MetadataFilterOperator.GT:
                if not MetadataFilter._compare_gt(field_value, expected_value):
                    return False

            elif op_name == MetadataFilterOperator.GTE:
                if not MetadataFilter._compare_gte(field_value, expected_value):
                    return False

            elif op_name == MetadataFilterOperator.LT:
                if not MetadataFilter._compare_lt(field_value, expected_value):
                    return False

            elif op_name == MetadataFilterOperator.LTE:
                if not MetadataFilter._compare_lte(field_value, expected_value):
                    return False

            elif op_name == MetadataFilterOperator.EXISTS:
                if not MetadataFilter._compare_exists(field_value, expected_value):
                    return False

        return True

    @staticmethod
    def _compare_equals(field_value: Any, expected_value: Any) -> bool:
        """Check if field value equals expected value."""
        return field_value == expected_value

    @staticmethod
    def _compare_contains(field_value: Any, substring: str) -> bool:
        """Check if field value (string) contains substring."""
        if not isinstance(field_value, str):
            return False
        if not isinstance(substring, str):
            return False
        return substring in field_value

    @staticmethod
    def _compare_in(field_value: Any, expected_list: List[Any]) -> bool:
        """Check if field value is in expected list."""
        if not isinstance(expected_list, list):
            return False
        return field_value in expected_list

    @staticmethod
    def _compare_nin(field_value: Any, expected_list: List[Any]) -> bool:
        """
        Check if field value is NOT in expected list.

        Issue #24: Implements $nin operator for MongoDB-style filtering.

        Args:
            field_value: The value from the metadata field
            expected_list: List of values the field should NOT match

        Returns:
            True if field value is not in the list, False otherwise
        """
        if not isinstance(expected_list, list):
            return False
        return field_value not in expected_list

    @staticmethod
    def _compare_gt(field_value: Any, threshold: float) -> bool:
        """Check if field value is greater than threshold."""
        if not isinstance(field_value, (int, float)):
            return False
        return field_value > threshold

    @staticmethod
    def _compare_gte(field_value: Any, threshold: float) -> bool:
        """Check if field value is greater than or equal to threshold."""
        if not isinstance(field_value, (int, float)):
            return False
        return field_value >= threshold

    @staticmethod
    def _compare_lt(field_value: Any, threshold: float) -> bool:
        """Check if field value is less than threshold."""
        if not isinstance(field_value, (int, float)):
            return False
        return field_value < threshold

    @staticmethod
    def _compare_lte(field_value: Any, threshold: float) -> bool:
        """Check if field value is less than or equal to threshold."""
        if not isinstance(field_value, (int, float)):
            return False
        return field_value <= threshold

    @staticmethod
    def _compare_exists(field_value: Any, should_exist: bool) -> bool:
        """Check if field exists or doesn't exist."""
        field_exists = field_value is not None
        return field_exists == should_exist

    @staticmethod
    def filter_results(
        results: List[Dict[str, Any]],
        metadata_filter: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Filter search results by metadata conditions.

        Issue #24: Apply metadata filters AFTER similarity search to refine results.

        Args:
            results: List of search results with metadata
            metadata_filter: Filter conditions to apply

        Returns:
            Filtered list of results matching all conditions
        """
        if not metadata_filter:
            return results

        filtered = []
        for result in results:
            vector_metadata = result.get("metadata", {})
            if MetadataFilter.matches_filter(vector_metadata, metadata_filter):
                filtered.append(result)

        logger.info(
            f"Metadata filter applied: {len(results)} -> {len(filtered)} results",
            extra={
                "original_count": len(results),
                "filtered_count": len(filtered),
                "filter": metadata_filter
            }
        )

        return filtered


# Convenience instance
metadata_filter = MetadataFilter()
