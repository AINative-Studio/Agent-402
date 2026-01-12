"""
Tests for math utilities module.

Test Coverage:
- cosine_similarity function
- euclidean_distance function
- dot_product function
- vector_magnitude function
- normalize_vector function

Per TDD best practices:
- Test edge cases
- Test error handling
- Verify mathematical correctness
"""
import pytest
import math
from app.core.math_utils import (
    cosine_similarity,
    euclidean_distance,
    dot_product,
    vector_magnitude,
    normalize_vector
)


class TestCosineSimilarity:
    """Tests for cosine_similarity function."""

    def test_identical_vectors(self):
        """Test that identical vectors have similarity 1.0."""
        vec1 = [1.0, 2.0, 3.0]
        vec2 = [1.0, 2.0, 3.0]

        similarity = cosine_similarity(vec1, vec2)

        assert similarity == pytest.approx(1.0, abs=1e-6)

    def test_orthogonal_vectors(self):
        """Test that orthogonal vectors have similarity 0.0."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]

        similarity = cosine_similarity(vec1, vec2)

        assert similarity == pytest.approx(0.0, abs=1e-6)

    def test_opposite_vectors(self):
        """Test that opposite vectors have similarity -1.0."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [-1.0, 0.0, 0.0]

        similarity = cosine_similarity(vec1, vec2)

        assert similarity == pytest.approx(-1.0, abs=1e-6)

    def test_parallel_vectors_different_magnitudes(self):
        """Test that parallel vectors with different magnitudes have similarity 1.0."""
        vec1 = [1.0, 2.0, 3.0]
        vec2 = [2.0, 4.0, 6.0]  # Scaled version of vec1

        similarity = cosine_similarity(vec1, vec2)

        assert similarity == pytest.approx(1.0, abs=1e-6)

    def test_similarity_is_symmetric(self):
        """Test that cosine_similarity(A, B) == cosine_similarity(B, A)."""
        vec1 = [1.0, 2.0, 3.0]
        vec2 = [4.0, 5.0, 6.0]

        sim1 = cosine_similarity(vec1, vec2)
        sim2 = cosine_similarity(vec2, vec1)

        assert sim1 == pytest.approx(sim2, abs=1e-6)

    def test_different_dimensions_raises_error(self):
        """Test that vectors with different dimensions raise ValueError."""
        vec1 = [1.0, 2.0, 3.0]
        vec2 = [1.0, 2.0]

        with pytest.raises(ValueError, match="same dimensions"):
            cosine_similarity(vec1, vec2)

    def test_empty_vectors_raises_error(self):
        """Test that empty vectors raise ValueError."""
        vec1 = []
        vec2 = []

        with pytest.raises(ValueError, match="cannot be empty"):
            cosine_similarity(vec1, vec2)

    def test_zero_vector_raises_error(self):
        """Test that zero vectors raise ValueError."""
        vec1 = [0.0, 0.0, 0.0]
        vec2 = [1.0, 2.0, 3.0]

        with pytest.raises(ValueError, match="zero magnitude"):
            cosine_similarity(vec1, vec2)

    def test_negative_values(self):
        """Test cosine similarity with negative values."""
        vec1 = [-1.0, -2.0, -3.0]
        vec2 = [1.0, 2.0, 3.0]

        similarity = cosine_similarity(vec1, vec2)

        # Opposite directions should give -1.0
        assert similarity == pytest.approx(-1.0, abs=1e-6)

    def test_mixed_positive_negative(self):
        """Test cosine similarity with mixed positive/negative values."""
        vec1 = [1.0, -1.0, 0.0]
        vec2 = [1.0, 1.0, 0.0]

        similarity = cosine_similarity(vec1, vec2)

        # Should be 0 since perpendicular
        assert similarity == pytest.approx(0.0, abs=1e-6)

    def test_large_dimension_vectors(self):
        """Test cosine similarity with large dimension vectors."""
        vec1 = [1.0] * 1000
        vec2 = [1.0] * 1000

        similarity = cosine_similarity(vec1, vec2)

        assert similarity == pytest.approx(1.0, abs=1e-6)


class TestEuclideanDistance:
    """Tests for euclidean_distance function."""

    def test_identical_vectors(self):
        """Test that identical vectors have distance 0.0."""
        vec1 = [1.0, 2.0, 3.0]
        vec2 = [1.0, 2.0, 3.0]

        distance = euclidean_distance(vec1, vec2)

        assert distance == pytest.approx(0.0, abs=1e-6)

    def test_unit_distance(self):
        """Test euclidean distance for unit distance."""
        vec1 = [0.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]

        distance = euclidean_distance(vec1, vec2)

        assert distance == pytest.approx(1.0, abs=1e-6)

    def test_pythagorean_triple(self):
        """Test euclidean distance with Pythagorean triple."""
        vec1 = [0.0, 0.0]
        vec2 = [3.0, 4.0]

        distance = euclidean_distance(vec1, vec2)

        assert distance == pytest.approx(5.0, abs=1e-6)

    def test_different_dimensions_raises_error(self):
        """Test that vectors with different dimensions raise ValueError."""
        vec1 = [1.0, 2.0, 3.0]
        vec2 = [1.0, 2.0]

        with pytest.raises(ValueError, match="same dimensions"):
            euclidean_distance(vec1, vec2)


class TestDotProduct:
    """Tests for dot_product function."""

    def test_simple_dot_product(self):
        """Test basic dot product calculation."""
        vec1 = [1.0, 2.0, 3.0]
        vec2 = [4.0, 5.0, 6.0]

        result = dot_product(vec1, vec2)

        # 1*4 + 2*5 + 3*6 = 4 + 10 + 18 = 32
        assert result == pytest.approx(32.0, abs=1e-6)

    def test_orthogonal_vectors(self):
        """Test that orthogonal vectors have dot product 0.0."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]

        result = dot_product(vec1, vec2)

        assert result == pytest.approx(0.0, abs=1e-6)

    def test_different_dimensions_raises_error(self):
        """Test that vectors with different dimensions raise ValueError."""
        vec1 = [1.0, 2.0, 3.0]
        vec2 = [1.0, 2.0]

        with pytest.raises(ValueError, match="same dimensions"):
            dot_product(vec1, vec2)


class TestVectorMagnitude:
    """Tests for vector_magnitude function."""

    def test_unit_vector(self):
        """Test magnitude of unit vector."""
        vec = [1.0, 0.0, 0.0]

        magnitude = vector_magnitude(vec)

        assert magnitude == pytest.approx(1.0, abs=1e-6)

    def test_pythagorean_triple(self):
        """Test magnitude with Pythagorean triple."""
        vec = [3.0, 4.0]

        magnitude = vector_magnitude(vec)

        assert magnitude == pytest.approx(5.0, abs=1e-6)

    def test_zero_vector(self):
        """Test magnitude of zero vector."""
        vec = [0.0, 0.0, 0.0]

        magnitude = vector_magnitude(vec)

        assert magnitude == pytest.approx(0.0, abs=1e-6)

    def test_negative_values(self):
        """Test magnitude with negative values."""
        vec = [-3.0, -4.0]

        magnitude = vector_magnitude(vec)

        # Magnitude is always positive
        assert magnitude == pytest.approx(5.0, abs=1e-6)


class TestNormalizeVector:
    """Tests for normalize_vector function."""

    def test_normalize_simple_vector(self):
        """Test normalizing a simple vector."""
        vec = [3.0, 4.0]

        normalized = normalize_vector(vec)

        # Normalized vector should have magnitude 1.0
        assert vector_magnitude(normalized) == pytest.approx(1.0, abs=1e-6)

        # Direction should be preserved
        assert normalized[0] == pytest.approx(0.6, abs=1e-6)
        assert normalized[1] == pytest.approx(0.8, abs=1e-6)

    def test_normalize_unit_vector(self):
        """Test that normalizing a unit vector returns itself."""
        vec = [1.0, 0.0, 0.0]

        normalized = normalize_vector(vec)

        assert normalized == pytest.approx(vec, abs=1e-6)

    def test_normalize_zero_vector_raises_error(self):
        """Test that normalizing zero vector raises ValueError."""
        vec = [0.0, 0.0, 0.0]

        with pytest.raises(ValueError, match="Cannot normalize zero vector"):
            normalize_vector(vec)

    def test_normalize_preserves_direction(self):
        """Test that normalization preserves direction."""
        vec = [2.0, 2.0, 2.0]

        normalized = normalize_vector(vec)

        # All components should be equal (same direction)
        assert normalized[0] == pytest.approx(normalized[1], abs=1e-6)
        assert normalized[1] == pytest.approx(normalized[2], abs=1e-6)

        # Magnitude should be 1.0
        assert vector_magnitude(normalized) == pytest.approx(1.0, abs=1e-6)
