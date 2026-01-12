"""
Math utilities for embedding operations.

Provides mathematical functions for vector operations, including:
- Cosine similarity calculation
- Vector normalization
- Distance metrics
"""
from typing import List
import math


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Calculate cosine similarity between two vectors.

    Cosine similarity measures the cosine of the angle between two vectors,
    ranging from -1 (opposite) to 1 (identical). For normalized embeddings,
    this typically ranges from 0 to 1.

    Formula: cos(θ) = (A · B) / (||A|| × ||B||)

    Args:
        vec1: First vector (embedding)
        vec2: Second vector (embedding)

    Returns:
        Cosine similarity score (typically 0.0 to 1.0 for embeddings)
        - 1.0: Vectors are identical in direction
        - 0.0: Vectors are orthogonal (no similarity)
        - -1.0: Vectors are opposite in direction

    Raises:
        ValueError: If vectors have different dimensions
        ValueError: If either vector is zero (has no magnitude)

    Example:
        >>> vec1 = [1.0, 0.0, 0.0]
        >>> vec2 = [1.0, 0.0, 0.0]
        >>> cosine_similarity(vec1, vec2)
        1.0

        >>> vec1 = [1.0, 0.0]
        >>> vec2 = [0.0, 1.0]
        >>> cosine_similarity(vec1, vec2)
        0.0
    """
    if len(vec1) != len(vec2):
        raise ValueError(
            f"Vectors must have same dimensions. "
            f"Got vec1: {len(vec1)}, vec2: {len(vec2)}"
        )

    if len(vec1) == 0:
        raise ValueError("Vectors cannot be empty")

    # Calculate dot product
    dot_product = sum(a * b for a, b in zip(vec1, vec2))

    # Calculate magnitudes
    magnitude1 = math.sqrt(sum(a * a for a in vec1))
    magnitude2 = math.sqrt(sum(b * b for b in vec2))

    # Check for zero vectors
    if magnitude1 == 0.0:
        raise ValueError("First vector has zero magnitude (all zeros)")

    if magnitude2 == 0.0:
        raise ValueError("Second vector has zero magnitude (all zeros)")

    # Calculate cosine similarity
    similarity = dot_product / (magnitude1 * magnitude2)

    # Clamp to [-1.0, 1.0] to handle floating point precision issues
    # (should already be in this range mathematically)
    similarity = max(-1.0, min(1.0, similarity))

    return similarity


def euclidean_distance(vec1: List[float], vec2: List[float]) -> float:
    """
    Calculate Euclidean distance between two vectors.

    Args:
        vec1: First vector
        vec2: Second vector

    Returns:
        Euclidean distance (always >= 0.0)

    Raises:
        ValueError: If vectors have different dimensions
    """
    if len(vec1) != len(vec2):
        raise ValueError(
            f"Vectors must have same dimensions. "
            f"Got vec1: {len(vec1)}, vec2: {len(vec2)}"
        )

    return math.sqrt(sum((a - b) ** 2 for a, b in zip(vec1, vec2)))


def dot_product(vec1: List[float], vec2: List[float]) -> float:
    """
    Calculate dot product of two vectors.

    Args:
        vec1: First vector
        vec2: Second vector

    Returns:
        Dot product (scalar value)

    Raises:
        ValueError: If vectors have different dimensions
    """
    if len(vec1) != len(vec2):
        raise ValueError(
            f"Vectors must have same dimensions. "
            f"Got vec1: {len(vec1)}, vec2: {len(vec2)}"
        )

    return sum(a * b for a, b in zip(vec1, vec2))


def vector_magnitude(vec: List[float]) -> float:
    """
    Calculate magnitude (L2 norm) of a vector.

    Args:
        vec: Input vector

    Returns:
        Magnitude of the vector (always >= 0.0)
    """
    return math.sqrt(sum(x * x for x in vec))


def normalize_vector(vec: List[float]) -> List[float]:
    """
    Normalize a vector to unit length.

    Args:
        vec: Input vector

    Returns:
        Normalized vector with magnitude 1.0

    Raises:
        ValueError: If vector has zero magnitude
    """
    magnitude = vector_magnitude(vec)

    if magnitude == 0.0:
        raise ValueError("Cannot normalize zero vector")

    return [x / magnitude for x in vec]
