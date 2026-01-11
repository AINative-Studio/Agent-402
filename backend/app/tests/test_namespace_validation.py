"""
Test namespace validation and error handling.

Tests Issue #17: Namespace validation requirements.

Requirements tested:
- Namespace validation rules are enforced
- Invalid namespace characters are rejected
- Empty/whitespace namespaces are rejected
- Namespace length limits are enforced
- Proper error messages for validation failures
"""
import pytest
from app.services.vector_store_service import vector_store_service, DEFAULT_NAMESPACE


class TestNamespaceValidation:
    """Test namespace validation rules."""

    def setup_method(self):
        """Clear vector store before each test."""
        vector_store_service._vectors = {}

    def test_valid_namespace_characters(self):
        """
        Issue #17: Valid namespace characters should be accepted.

        Test that namespaces with alphanumeric, hyphens, underscores, and dots are valid.
        """
        project_id = "test_project_1"
        user_id = "user_1"

        valid_namespaces = [
            "simple",
            "with-hyphens",
            "with_underscores",
            "with.dots",
            "mixed-chars_123.test",
            "UPPERCASE",
            "MixedCase123"
        ]

        for namespace in valid_namespaces:
            result = vector_store_service.store_vector(
                project_id=project_id,
                user_id=user_id,
                text=f"Text for {namespace}",
                embedding=[1.0, 2.0, 3.0],
                model="test-model",
                dimensions=3,
                namespace=namespace
            )

            assert result["namespace"] == namespace
            assert result["stored"] is True

    def test_invalid_namespace_characters_rejected(self):
        """
        Issue #17: Invalid namespace characters should be rejected.

        Test that namespaces with special characters (except -, _, .) are rejected.
        """
        project_id = "test_project_2"
        user_id = "user_1"

        invalid_namespaces = [
            "has spaces",
            "has/slash",
            "has\\backslash",
            "has@symbol",
            "has#hash",
            "has$dollar",
            "has%percent",
            "has*asterisk",
            "has!exclamation",
            "has?question",
            "has[brackets]",
            "has{braces}",
            "has(parens)",
            "has<angle>",
            "has|pipe",
            "has;semicolon",
            "has:colon",
            "has'quote",
            "has\"doublequote"
        ]

        for namespace in invalid_namespaces:
            with pytest.raises(ValueError) as exc_info:
                vector_store_service.store_vector(
                    project_id=project_id,
                    user_id=user_id,
                    text="Test text",
                    embedding=[1.0, 2.0, 3.0],
                    model="test-model",
                    dimensions=3,
                    namespace=namespace
                )

            assert "can only contain alphanumeric characters" in str(exc_info.value)

    def test_empty_namespace_rejected(self):
        """
        Issue #17: Empty namespace should be rejected.

        Test that empty string namespace is rejected.
        """
        project_id = "test_project_3"
        user_id = "user_1"

        with pytest.raises(ValueError) as exc_info:
            vector_store_service.store_vector(
                project_id=project_id,
                user_id=user_id,
                text="Test text",
                embedding=[1.0, 2.0, 3.0],
                model="test-model",
                dimensions=3,
                namespace=""
            )

        assert "cannot be empty or whitespace" in str(exc_info.value)

    def test_whitespace_namespace_rejected(self):
        """
        Issue #17: Whitespace-only namespace should be rejected.

        Test that namespaces with only whitespace are rejected.
        """
        project_id = "test_project_4"
        user_id = "user_1"

        whitespace_namespaces = [" ", "  ", "\t", "\n", "   \t\n   "]

        for namespace in whitespace_namespaces:
            with pytest.raises(ValueError) as exc_info:
                vector_store_service.store_vector(
                    project_id=project_id,
                    user_id=user_id,
                    text="Test text",
                    embedding=[1.0, 2.0, 3.0],
                    model="test-model",
                    dimensions=3,
                    namespace=namespace
                )

            assert "cannot be empty or whitespace" in str(exc_info.value)

    def test_namespace_length_limit_enforced(self):
        """
        Issue #17: Namespace length limit should be enforced.

        Test that namespaces longer than 128 characters are rejected.
        """
        project_id = "test_project_5"
        user_id = "user_1"

        # Valid namespace at exactly 128 characters
        valid_namespace = "a" * 128
        result = vector_store_service.store_vector(
            project_id=project_id,
            user_id=user_id,
            text="Test text",
            embedding=[1.0, 2.0, 3.0],
            model="test-model",
            dimensions=3,
            namespace=valid_namespace
        )
        assert result["stored"] is True

        # Invalid namespace at 129 characters
        invalid_namespace = "a" * 129
        with pytest.raises(ValueError) as exc_info:
            vector_store_service.store_vector(
                project_id=project_id,
                user_id=user_id,
                text="Test text",
                embedding=[1.0, 2.0, 3.0],
                model="test-model",
                dimensions=3,
                namespace=invalid_namespace
            )

        assert "cannot exceed 128 characters" in str(exc_info.value)

    def test_non_string_namespace_rejected(self):
        """
        Issue #17: Non-string namespace should be rejected.

        Test that namespace must be a string or None.
        """
        project_id = "test_project_6"
        user_id = "user_1"

        invalid_types = [123, 45.6, True, ["list"], {"dict": "value"}]

        for invalid_namespace in invalid_types:
            with pytest.raises(ValueError) as exc_info:
                vector_store_service.store_vector(
                    project_id=project_id,
                    user_id=user_id,
                    text="Test text",
                    embedding=[1.0, 2.0, 3.0],
                    model="test-model",
                    dimensions=3,
                    namespace=invalid_namespace
                )

            assert "must be a string" in str(exc_info.value)

    def test_none_namespace_uses_default(self):
        """
        Issue #17: None namespace should use DEFAULT_NAMESPACE.

        Test that None is valid and maps to default namespace.
        """
        project_id = "test_project_7"
        user_id = "user_1"

        result = vector_store_service.store_vector(
            project_id=project_id,
            user_id=user_id,
            text="Test text",
            embedding=[1.0, 2.0, 3.0],
            model="test-model",
            dimensions=3,
            namespace=None
        )

        assert result["namespace"] == DEFAULT_NAMESPACE
        assert result["namespace"] == "default"
        assert result["stored"] is True

    def test_namespace_validation_in_search(self):
        """
        Issue #17: Namespace validation should also apply to search.

        Test that search rejects invalid namespaces.
        """
        project_id = "test_project_8"

        # Test invalid characters
        with pytest.raises(ValueError):
            vector_store_service.search_vectors(
                project_id=project_id,
                query_embedding=[1.0, 2.0, 3.0],
                namespace="invalid/namespace",
                top_k=10
            )

        # Test empty namespace
        with pytest.raises(ValueError):
            vector_store_service.search_vectors(
                project_id=project_id,
                query_embedding=[1.0, 2.0, 3.0],
                namespace="",
                top_k=10
            )

        # Test too long namespace
        with pytest.raises(ValueError):
            vector_store_service.search_vectors(
                project_id=project_id,
                query_embedding=[1.0, 2.0, 3.0],
                namespace="a" * 129,
                top_k=10
            )

    def test_path_traversal_prevention(self):
        """
        Issue #17: Namespace validation should prevent path traversal.

        Test that path traversal attempts are blocked.
        """
        project_id = "test_project_9"
        user_id = "user_1"

        path_traversal_attempts = [
            "../parent",
            "../../root",
            "child/../sibling",
            "./current",
            "/absolute/path"
        ]

        for namespace in path_traversal_attempts:
            with pytest.raises(ValueError):
                vector_store_service.store_vector(
                    project_id=project_id,
                    user_id=user_id,
                    text="Test text",
                    embedding=[1.0, 2.0, 3.0],
                    model="test-model",
                    dimensions=3,
                    namespace=namespace
                )

    def test_namespace_case_sensitivity(self):
        """
        Issue #17: Namespaces should be case-sensitive.

        Test that "Namespace" and "namespace" are different namespaces.
        """
        project_id = "test_project_10"
        user_id = "user_1"

        # Store in lowercase namespace
        vector_store_service.store_vector(
            project_id=project_id,
            user_id=user_id,
            text="Lowercase namespace",
            embedding=[1.0, 0.0, 0.0],
            model="test-model",
            dimensions=3,
            namespace="myspace"
        )

        # Store in uppercase namespace
        vector_store_service.store_vector(
            project_id=project_id,
            user_id=user_id,
            text="Uppercase namespace",
            embedding=[0.0, 1.0, 0.0],
            model="test-model",
            dimensions=3,
            namespace="MYSPACE"
        )

        # Search lowercase - should only find lowercase
        results_lower = vector_store_service.search_vectors(
            project_id=project_id,
            query_embedding=[1.0, 0.0, 0.0],
            namespace="myspace",
            top_k=10
        )
        assert len(results_lower) == 1
        assert results_lower[0]["text"] == "Lowercase namespace"

        # Search uppercase - should only find uppercase
        results_upper = vector_store_service.search_vectors(
            project_id=project_id,
            query_embedding=[0.0, 1.0, 0.0],
            namespace="MYSPACE",
            top_k=10
        )
        assert len(results_upper) == 1
        assert results_upper[0]["text"] == "Uppercase namespace"

    def test_namespace_stats_validation(self):
        """
        Issue #17: get_namespace_stats should validate namespace.

        Test that stats endpoint also validates namespace.
        """
        project_id = "test_project_11"

        # Test invalid namespace
        with pytest.raises(ValueError):
            vector_store_service.get_namespace_stats(
                project_id=project_id,
                namespace="invalid/namespace"
            )

        # Test valid namespace
        stats = vector_store_service.get_namespace_stats(
            project_id=project_id,
            namespace="valid-namespace"
        )
        assert stats["namespace"] == "valid-namespace"
        assert stats["vector_count"] == 0
        assert stats["exists"] is False
