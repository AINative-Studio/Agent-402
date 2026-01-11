"""
Dimension validation utilities for vector operations.
Implements strict dimension enforcement per Issue #28.

This module provides utilities for validating vector dimensions across
the application, ensuring consistency and deterministic behavior.

Per DX Contract (PRD §10):
- Dimension validation is strict and deterministic
- Only supported dimensions are allowed
- Clear error messages for validation failures
- Project-level dimension configuration support
"""
from typing import List, Optional, Tuple
from app.core.errors import APIError


# Supported vector dimensions per Issue #28
SUPPORTED_DIMENSIONS = {384, 768, 1024, 1536}

# Default dimension (matches default embedding model BAAI/bge-small-en-v1.5)
DEFAULT_DIMENSION = 384

# Mapping of dimensions to common embedding models
DIMENSION_TO_MODELS = {
    384: [
        "BAAI/bge-small-en-v1.5",
        "sentence-transformers/all-MiniLM-L6-v2",
        "sentence-transformers/all-MiniLM-L12-v2"
    ],
    768: [
        "BAAI/bge-base-en-v1.5",
        "sentence-transformers/all-mpnet-base-v2",
        "sentence-transformers/all-distilroberta-v1"
    ],
    1024: [
        "BAAI/bge-large-en-v1.5"
    ],
    1536: [
        "OpenAI text-embedding-ada-002",
        "Custom models"
    ]
}


def is_dimension_supported(dimensions: int) -> bool:
    """
    Check if a dimension value is supported.

    Issue #28: Only allow supported dimensions: 384, 768, 1024, 1536.

    Args:
        dimensions: Dimension value to check

    Returns:
        True if dimension is supported, False otherwise

    Example:
        >>> is_dimension_supported(384)
        True
        >>> is_dimension_supported(512)
        False
    """
    return dimensions in SUPPORTED_DIMENSIONS


def validate_vector_dimensions(
    vector: List[float],
    declared_dimensions: int,
    vector_name: str = "vector_embedding"
) -> None:
    """
    Validate that a vector's length matches its declared dimensions.

    Issue #28 Core Validation:
    - Validate vector_embedding array length matches expected dimensions
    - Enforce strict validation before storage
    - Return clear error if length mismatch

    This function provides deterministic validation behavior per PRD §10.

    Args:
        vector: Vector embedding array to validate
        declared_dimensions: Expected dimensionality
        vector_name: Name of vector field for error messages

    Raises:
        APIError: If validation fails with DIMENSION_MISMATCH error code

    Example:
        >>> vector = [0.1, 0.2, 0.3]
        >>> validate_vector_dimensions(vector, 3)  # Passes
        >>> validate_vector_dimensions(vector, 4)  # Raises APIError
    """
    # First check if declared dimensions are supported
    if not is_dimension_supported(declared_dimensions):
        supported_str = ", ".join(str(d) for d in sorted(SUPPORTED_DIMENSIONS))
        raise APIError(
            detail=(
                f"Dimension {declared_dimensions} is not supported. "
                f"Supported dimensions: {supported_str}"
            ),
            error_code="INVALID_DIMENSION",
            status_code=400
        )

    # Check if vector is empty
    if not vector or len(vector) == 0:
        raise APIError(
            detail=f"{vector_name} cannot be empty",
            error_code="EMPTY_VECTOR",
            status_code=400
        )

    # Validate length matches declared dimensions
    actual_length = len(vector)
    if actual_length != declared_dimensions:
        # Get model suggestions for this dimension
        model_suggestions = DIMENSION_TO_MODELS.get(declared_dimensions, [])
        models_hint = ""
        if model_suggestions:
            models_hint = f" Common models with {declared_dimensions} dimensions: {', '.join(model_suggestions[:2])}"

        raise APIError(
            detail=(
                f"Vector dimension mismatch: "
                f"declared dimensions={declared_dimensions}, "
                f"but {vector_name} has {actual_length} elements. "
                f"Array length must match dimensions parameter exactly.{models_hint}"
            ),
            error_code="DIMENSION_MISMATCH",
            status_code=400,
            extra={
                "declared_dimensions": declared_dimensions,
                "actual_length": actual_length,
                "supported_dimensions": sorted(SUPPORTED_DIMENSIONS)
            }
        )


def validate_dimension_consistency(
    stored_dimensions: Optional[int],
    new_dimensions: int,
    operation: str = "vector operation"
) -> None:
    """
    Validate dimension consistency for operations on existing vectors.

    Ensures that dimension changes are not allowed when updating vectors,
    supporting project-level dimension configuration per Issue #28.

    Args:
        stored_dimensions: Dimensions of existing stored vector (None if new)
        new_dimensions: Dimensions of new vector being stored
        operation: Description of operation for error messages

    Raises:
        APIError: If dimensions don't match for an update operation

    Example:
        >>> validate_dimension_consistency(384, 384, "update")  # Passes
        >>> validate_dimension_consistency(384, 768, "update")  # Raises APIError
    """
    if stored_dimensions is not None and stored_dimensions != new_dimensions:
        raise APIError(
            detail=(
                f"Cannot change vector dimensions during {operation}. "
                f"Existing vector has {stored_dimensions} dimensions, "
                f"but new vector has {new_dimensions} dimensions. "
                f"Dimension changes are not allowed."
            ),
            error_code="DIMENSION_CHANGE_NOT_ALLOWED",
            status_code=400,
            extra={
                "stored_dimensions": stored_dimensions,
                "new_dimensions": new_dimensions
            }
        )


def get_dimension_info(dimensions: int) -> dict:
    """
    Get information about a specific dimension value.

    Args:
        dimensions: Dimension value to get info for

    Returns:
        Dictionary with dimension information including:
        - supported: Whether dimension is supported
        - common_models: List of common models with this dimension
        - is_default: Whether this is the default dimension

    Example:
        >>> info = get_dimension_info(384)
        >>> info['supported']
        True
        >>> info['is_default']
        True
    """
    return {
        "dimensions": dimensions,
        "supported": is_dimension_supported(dimensions),
        "common_models": DIMENSION_TO_MODELS.get(dimensions, []),
        "is_default": dimensions == DEFAULT_DIMENSION
    }


def get_supported_dimensions_info() -> List[dict]:
    """
    Get information about all supported dimensions.

    Returns:
        List of dictionaries with dimension information

    Example:
        >>> dims = get_supported_dimensions_info()
        >>> len(dims)
        4
        >>> dims[0]['dimensions']
        384
    """
    return [
        get_dimension_info(dim)
        for dim in sorted(SUPPORTED_DIMENSIONS)
    ]


def validate_batch_dimensions(
    vectors: List[List[float]],
    declared_dimensions: int
) -> Tuple[bool, Optional[str]]:
    """
    Validate dimensions for a batch of vectors.

    Useful for batch operations where all vectors must have the same dimensions.

    Args:
        vectors: List of vector embeddings
        declared_dimensions: Expected dimensions for all vectors

    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if all vectors match declared dimensions
        - error_message: None if valid, error description if invalid

    Example:
        >>> vectors = [[0.1, 0.2], [0.3, 0.4]]
        >>> is_valid, error = validate_batch_dimensions(vectors, 2)
        >>> is_valid
        True
    """
    if not is_dimension_supported(declared_dimensions):
        supported_str = ", ".join(str(d) for d in sorted(SUPPORTED_DIMENSIONS))
        return False, (
            f"Dimension {declared_dimensions} is not supported. "
            f"Supported dimensions: {supported_str}"
        )

    for i, vector in enumerate(vectors):
        actual_length = len(vector)
        if actual_length != declared_dimensions:
            return False, (
                f"Vector at index {i}: dimension mismatch. "
                f"Expected {declared_dimensions}, got {actual_length}"
            )

    return True, None
