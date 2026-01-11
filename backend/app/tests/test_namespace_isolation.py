"""
Test namespace isolation for vector storage and retrieval.

Tests Issue #17: As a developer, namespace scopes retrieval correctly.

Requirements tested:
- Vectors stored in one namespace should NOT appear in another namespace
- Default namespace should be isolated from named namespaces
- Namespace parameter properly scopes vector storage and retrieval
- Cross-namespace isolation is enforced
"""
import pytest
from app.services.vector_store_service import vector_store_service, DEFAULT_NAMESPACE


class TestNamespaceIsolation:
    """Test namespace isolation guarantees."""

    def setup_method(self):
        """Clear vector store before each test."""
        vector_store_service._vectors = {}

    def test_vectors_in_different_namespaces_are_isolated(self):
        """
        Issue #17: Vectors stored in one namespace should NOT appear in another.

        Test that vectors stored in namespace A cannot be retrieved from namespace B.
        """
        project_id = "test_project_1"
        user_id = "user_1"

        # Store vector in namespace "agent_1"
        result_1 = vector_store_service.store_vector(
            project_id=project_id,
            user_id=user_id,
            text="Agent 1 memory",
            embedding=[0.1, 0.2, 0.3],
            model="test-model",
            dimensions=3,
            namespace="agent_1",
            metadata={"source": "agent_1"}
        )

        # Store vector in namespace "agent_2"
        result_2 = vector_store_service.store_vector(
            project_id=project_id,
            user_id=user_id,
            text="Agent 2 memory",
            embedding=[0.4, 0.5, 0.6],
            model="test-model",
            dimensions=3,
            namespace="agent_2",
            metadata={"source": "agent_2"}
        )

        # Search in namespace "agent_1" - should only find agent_1's vector
        results_1 = vector_store_service.search_vectors(
            project_id=project_id,
            query_embedding=[0.1, 0.2, 0.3],
            namespace="agent_1",
            top_k=10
        )

        assert len(results_1) == 1
        assert results_1[0]["text"] == "Agent 1 memory"
        assert results_1[0]["namespace"] == "agent_1"
        assert results_1[0]["metadata"]["source"] == "agent_1"

        # Search in namespace "agent_2" - should only find agent_2's vector
        results_2 = vector_store_service.search_vectors(
            project_id=project_id,
            query_embedding=[0.4, 0.5, 0.6],
            namespace="agent_2",
            top_k=10
        )

        assert len(results_2) == 1
        assert results_2[0]["text"] == "Agent 2 memory"
        assert results_2[0]["namespace"] == "agent_2"
        assert results_2[0]["metadata"]["source"] == "agent_2"

    def test_default_namespace_is_isolated_from_named_namespaces(self):
        """
        Issue #17: Default namespace should be isolated from named namespaces.

        Test that vectors in default namespace don't appear in named namespaces.
        """
        project_id = "test_project_2"
        user_id = "user_1"

        # Store vector in default namespace (namespace=None)
        result_default = vector_store_service.store_vector(
            project_id=project_id,
            user_id=user_id,
            text="Default namespace memory",
            embedding=[0.7, 0.8, 0.9],
            model="test-model",
            dimensions=3,
            namespace=None,  # Should use DEFAULT_NAMESPACE
            metadata={"source": "default"}
        )

        assert result_default["namespace"] == DEFAULT_NAMESPACE

        # Store vector in named namespace
        result_named = vector_store_service.store_vector(
            project_id=project_id,
            user_id=user_id,
            text="Named namespace memory",
            embedding=[0.1, 0.1, 0.1],
            model="test-model",
            dimensions=3,
            namespace="custom_ns",
            metadata={"source": "custom"}
        )

        # Search in default namespace - should only find default vector
        results_default = vector_store_service.search_vectors(
            project_id=project_id,
            query_embedding=[0.7, 0.8, 0.9],
            namespace=None,  # Should search DEFAULT_NAMESPACE
            top_k=10
        )

        assert len(results_default) == 1
        assert results_default[0]["text"] == "Default namespace memory"
        assert results_default[0]["namespace"] == DEFAULT_NAMESPACE

        # Search in named namespace - should only find named vector
        results_named = vector_store_service.search_vectors(
            project_id=project_id,
            query_embedding=[0.1, 0.1, 0.1],
            namespace="custom_ns",
            top_k=10
        )

        assert len(results_named) == 1
        assert results_named[0]["text"] == "Named namespace memory"
        assert results_named[0]["namespace"] == "custom_ns"

    def test_namespace_parameter_defaults_to_default_namespace(self):
        """
        Issue #17: When namespace is None, should use DEFAULT_NAMESPACE.

        Test that omitting namespace parameter uses "default" namespace.
        """
        project_id = "test_project_3"
        user_id = "user_1"

        # Store without specifying namespace
        result = vector_store_service.store_vector(
            project_id=project_id,
            user_id=user_id,
            text="Implicit default namespace",
            embedding=[0.5, 0.5, 0.5],
            model="test-model",
            dimensions=3,
            namespace=None
        )

        # Should be stored in DEFAULT_NAMESPACE
        assert result["namespace"] == DEFAULT_NAMESPACE
        assert result["namespace"] == "default"

        # Search without specifying namespace
        results = vector_store_service.search_vectors(
            project_id=project_id,
            query_embedding=[0.5, 0.5, 0.5],
            namespace=None,
            top_k=10
        )

        assert len(results) == 1
        assert results[0]["namespace"] == DEFAULT_NAMESPACE

    def test_cross_namespace_isolation_with_multiple_vectors(self):
        """
        Issue #17: Test cross-namespace isolation with multiple vectors.

        Store multiple vectors in different namespaces and verify complete isolation.
        """
        project_id = "test_project_4"
        user_id = "user_1"

        # Store 3 vectors in namespace "ns_a"
        for i in range(3):
            vector_store_service.store_vector(
                project_id=project_id,
                user_id=user_id,
                text=f"Namespace A vector {i}",
                embedding=[float(i), float(i), float(i)],
                model="test-model",
                dimensions=3,
                namespace="ns_a"
            )

        # Store 2 vectors in namespace "ns_b"
        for i in range(2):
            vector_store_service.store_vector(
                project_id=project_id,
                user_id=user_id,
                text=f"Namespace B vector {i}",
                embedding=[float(i + 10), float(i + 10), float(i + 10)],
                model="test-model",
                dimensions=3,
                namespace="ns_b"
            )

        # Search in namespace "ns_a" - should only find 3 vectors
        results_a = vector_store_service.search_vectors(
            project_id=project_id,
            query_embedding=[1.0, 1.0, 1.0],
            namespace="ns_a",
            top_k=100  # Request more than total to ensure no cross-contamination
        )

        assert len(results_a) == 3
        assert all("Namespace A" in r["text"] for r in results_a)
        assert all(r["namespace"] == "ns_a" for r in results_a)

        # Search in namespace "ns_b" - should only find 2 vectors
        results_b = vector_store_service.search_vectors(
            project_id=project_id,
            query_embedding=[10.0, 10.0, 10.0],
            namespace="ns_b",
            top_k=100
        )

        assert len(results_b) == 2
        assert all("Namespace B" in r["text"] for r in results_b)
        assert all(r["namespace"] == "ns_b" for r in results_b)

    def test_namespace_stats_are_isolated(self):
        """
        Issue #17: Namespace statistics should be isolated.

        Test that namespace stats only count vectors in that namespace.
        """
        project_id = "test_project_5"
        user_id = "user_1"

        # Store 5 vectors in namespace "ns_1"
        for i in range(5):
            vector_store_service.store_vector(
                project_id=project_id,
                user_id=user_id,
                text=f"Vector {i}",
                embedding=[float(i), 0.0, 0.0],
                model="test-model",
                dimensions=3,
                namespace="ns_1"
            )

        # Store 3 vectors in namespace "ns_2"
        for i in range(3):
            vector_store_service.store_vector(
                project_id=project_id,
                user_id=user_id,
                text=f"Vector {i}",
                embedding=[0.0, float(i), 0.0],
                model="test-model",
                dimensions=3,
                namespace="ns_2"
            )

        # Get stats for each namespace
        stats_1 = vector_store_service.get_namespace_stats(project_id, "ns_1")
        stats_2 = vector_store_service.get_namespace_stats(project_id, "ns_2")

        assert stats_1["namespace"] == "ns_1"
        assert stats_1["vector_count"] == 5
        assert stats_1["exists"] is True

        assert stats_2["namespace"] == "ns_2"
        assert stats_2["vector_count"] == 3
        assert stats_2["exists"] is True

    def test_empty_namespace_returns_no_results(self):
        """
        Issue #17: Searching an empty namespace should return empty results.

        Test that searching a namespace with no vectors returns empty list.
        """
        project_id = "test_project_6"

        # Search in non-existent namespace
        results = vector_store_service.search_vectors(
            project_id=project_id,
            query_embedding=[1.0, 1.0, 1.0],
            namespace="empty_namespace",
            top_k=10
        )

        assert results == []

        # Get stats for non-existent namespace
        stats = vector_store_service.get_namespace_stats(project_id, "empty_namespace")
        assert stats["namespace"] == "empty_namespace"
        assert stats["vector_count"] == 0
        assert stats["exists"] is False

    def test_list_namespaces_returns_all_namespaces(self):
        """
        Issue #17: List namespaces should return all namespaces in project.

        Test that list_namespaces returns all unique namespaces.
        """
        project_id = "test_project_7"
        user_id = "user_1"

        # Store vectors in multiple namespaces
        namespaces = ["ns_a", "ns_b", "ns_c", DEFAULT_NAMESPACE]
        for ns in namespaces:
            vector_store_service.store_vector(
                project_id=project_id,
                user_id=user_id,
                text=f"Vector in {ns}",
                embedding=[1.0, 2.0, 3.0],
                model="test-model",
                dimensions=3,
                namespace=ns if ns != DEFAULT_NAMESPACE else None
            )

        # List all namespaces
        all_namespaces = vector_store_service.list_namespaces(project_id)

        assert len(all_namespaces) == 4
        assert set(all_namespaces) == set(namespaces)

    def test_same_vector_id_in_different_namespaces(self):
        """
        Issue #17: Same vector_id can exist in different namespaces.

        Test that vector_id uniqueness is scoped to namespace.
        """
        project_id = "test_project_8"
        user_id = "user_1"
        vector_id = "shared_id_123"

        # Store vector with same ID in namespace "ns_1"
        result_1 = vector_store_service.store_vector(
            project_id=project_id,
            user_id=user_id,
            text="Vector in namespace 1",
            embedding=[1.0, 0.0, 0.0],
            model="test-model",
            dimensions=3,
            namespace="ns_1",
            vector_id=vector_id
        )

        # Store vector with same ID in namespace "ns_2" - should succeed
        result_2 = vector_store_service.store_vector(
            project_id=project_id,
            user_id=user_id,
            text="Vector in namespace 2",
            embedding=[0.0, 1.0, 0.0],
            model="test-model",
            dimensions=3,
            namespace="ns_2",
            vector_id=vector_id
        )

        assert result_1["vector_id"] == vector_id
        assert result_2["vector_id"] == vector_id
        assert result_1["namespace"] == "ns_1"
        assert result_2["namespace"] == "ns_2"

        # Verify both vectors exist in their respective namespaces
        results_1 = vector_store_service.search_vectors(
            project_id=project_id,
            query_embedding=[1.0, 0.0, 0.0],
            namespace="ns_1",
            top_k=10
        )
        assert len(results_1) == 1
        assert results_1[0]["vector_id"] == vector_id
        assert results_1[0]["text"] == "Vector in namespace 1"

        results_2 = vector_store_service.search_vectors(
            project_id=project_id,
            query_embedding=[0.0, 1.0, 0.0],
            namespace="ns_2",
            top_k=10
        )
        assert len(results_2) == 1
        assert results_2[0]["vector_id"] == vector_id
        assert results_2[0]["text"] == "Vector in namespace 2"
