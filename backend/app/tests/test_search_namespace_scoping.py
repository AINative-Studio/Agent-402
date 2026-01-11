"""
Test namespace scoping for search endpoint.

Tests Issue #23: As a developer, I can scope search by namespace.

Requirements tested:
- Search endpoint accepts namespace parameter
- Search only returns results from specified namespace
- Default namespace is used when parameter is omitted
- Complete isolation - vectors in namespace A never appear in namespace B searches
- Namespace validation works on search endpoint
- Search works with both default and custom namespaces

Per PRD §6: Agent isolation via namespace scoping.
Per Epic 5 Story 3: Namespace scopes search correctly.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.services.vector_store_service import vector_store_service


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def valid_api_key():
    """Get a valid API key from settings."""
    if settings.valid_api_keys:
        return list(settings.valid_api_keys.keys())[0]
    return "test_api_key_abc123"


@pytest.fixture
def auth_headers(valid_api_key):
    """Create authentication headers."""
    return {"X-API-Key": valid_api_key}


@pytest.fixture
def test_project_id():
    """Get a test project ID."""
    return "proj_test_namespace_search"


@pytest.fixture(autouse=True)
def clear_vectors():
    """Clear vector store before each test."""
    vector_store_service.clear_all_vectors()
    yield
    vector_store_service.clear_all_vectors()


class TestSearchNamespaceScoping:
    """Test namespace scoping in search endpoint."""

    def test_search_with_explicit_namespace(self, client, auth_headers, test_project_id):
        """
        Issue #23: Search with explicit namespace parameter.

        Verify that search accepts namespace parameter and searches only that namespace.
        """
        # Store vector in namespace "agent_1"
        store_response = client.post(
            f"/v1/public/{test_project_id}/embeddings/embed-and-store",
            json={
                "texts": ["Agent 1 memory about compliance"],
                "namespace": "agent_1",
                "metadata": {"agent": "agent_1"}
            },
            headers=auth_headers
        )
        assert store_response.status_code == 200

        # Store vector in namespace "agent_2"
        store_response_2 = client.post(
            f"/v1/public/{test_project_id}/embeddings/embed-and-store",
            json={
                "texts": ["Agent 2 memory about finance"],
                "namespace": "agent_2",
                "metadata": {"agent": "agent_2"}
            },
            headers=auth_headers
        )
        assert store_response_2.status_code == 200

        # Search in namespace "agent_1"
        search_response = client.post(
            f"/v1/public/{test_project_id}/embeddings/search",
            json={
                "query": "compliance",
                "namespace": "agent_1",
                "top_k": 10
            },
            headers=auth_headers
        )

        assert search_response.status_code == 200
        data = search_response.json()

        # Verify only agent_1's vector is returned
        assert data["namespace"] == "agent_1"
        assert len(data["results"]) == 1
        assert data["results"][0]["document"] == "Agent 1 memory about compliance"
        assert data["results"][0]["metadata"]["agent"] == "agent_1"

    def test_search_with_default_namespace(self, client, auth_headers, test_project_id):
        """
        Issue #23: Search without namespace parameter defaults to "default" namespace.

        Verify that omitting namespace parameter uses "default" namespace.
        """
        # Store vector in default namespace (no namespace parameter)
        store_response = client.post(
            f"/v1/public/{test_project_id}/embeddings/embed-and-store",
            json={
                "texts": ["Default namespace memory"],
                "metadata": {"type": "default"}
            },
            headers=auth_headers
        )
        assert store_response.status_code == 200
        # Store vector in custom namespace
        store_response_2 = client.post(
            f"/v1/public/{test_project_id}/embeddings/embed-and-store",
            json={
                "texts": ["Custom namespace memory"],
                "namespace": "custom",
                "metadata": {"type": "custom"}
            },
            headers=auth_headers
        )
        assert store_response_2.status_code == 200

        # Search without namespace parameter (should use "default")
        search_response = client.post(
            f"/v1/public/{test_project_id}/embeddings/search",
            json={
                "query": "memory",
                "top_k": 10
            },
            headers=auth_headers
        )

        assert search_response.status_code == 200
        data = search_response.json()

        # Verify only default namespace vector is returned
        assert data["namespace"] == "default"
        assert len(data["results"]) == 1
        assert data["results"][0]["document"] == "Default namespace memory"
        assert data["results"][0]["metadata"]["type"] == "default"

    def test_search_complete_isolation_namespace_a_vs_b(self, client, auth_headers, test_project_id):
        """
        Issue #23: Complete isolation - vectors in namespace A never appear in namespace B searches.

        Critical requirement: Verify strict namespace isolation.
        """
        # Store 5 vectors in namespace "team_alpha"
        alpha_texts = [
            "Alpha team strategy document",
            "Alpha team financial report",
            "Alpha team compliance audit",
            "Alpha team risk assessment",
            "Alpha team quarterly review"
        ]
        for text in alpha_texts:
            response = client.post(
                f"/v1/public/{test_project_id}/embeddings/embed-and-store",
                json={
                    "texts": [text],
                    "namespace": "team_alpha",
                    "metadata": {"team": "alpha"}
                },
                headers=auth_headers
            )
            assert response.status_code == 200

        # Store 3 vectors in namespace "team_beta"
        beta_texts = [
            "Beta team product roadmap",
            "Beta team engineering plan",
            "Beta team user research"
        ]
        for text in beta_texts:
            response = client.post(
                f"/v1/public/{test_project_id}/embeddings/embed-and-store",
                json={
                    "texts": [text],
                    "namespace": "team_beta",
                    "metadata": {"team": "beta"}
                },
                headers=auth_headers
            )
            assert response.status_code == 200

        # Search in team_alpha - should ONLY find alpha vectors
        search_alpha = client.post(
            f"/v1/public/{test_project_id}/embeddings/search",
            json={
                "query": "team report",
                "namespace": "team_alpha",
                "top_k": 100  # Request more than total to ensure no cross-contamination
            },
            headers=auth_headers
        )

        assert search_alpha.status_code == 200
        alpha_data = search_alpha.json()

        assert alpha_data["namespace"] == "team_alpha"
        assert len(alpha_data["results"]) == 5
        # Verify ALL results are from team_alpha
        for result in alpha_data["results"]:
            assert result["metadata"]["team"] == "alpha"
            assert "Alpha team" in result["document"]
            assert "Beta team" not in result["document"]

        # Search in team_beta - should ONLY find beta vectors
        search_beta = client.post(
            f"/v1/public/{test_project_id}/embeddings/search",
            json={
                "query": "team plan",
                "namespace": "team_beta",
                "top_k": 100
            },
            headers=auth_headers
        )

        assert search_beta.status_code == 200
        beta_data = search_beta.json()

        assert beta_data["namespace"] == "team_beta"
        assert len(beta_data["results"]) == 3
        # Verify ALL results are from team_beta
        for result in beta_data["results"]:
            assert result["metadata"]["team"] == "beta"
            assert "Beta team" in result["document"]
            assert "Alpha team" not in result["document"]

    def test_search_default_namespace_isolated_from_custom(self, client, auth_headers, test_project_id):
        """
        Issue #23: Default namespace is isolated from custom namespaces.

        Verify that "default" namespace is treated as a first-class isolated namespace.
        """
        # Store vectors in default namespace
        default_texts = [
            "General system configuration",
            "Global settings document"
        ]
        for text in default_texts:
            response = client.post(
                f"/v1/public/{test_project_id}/embeddings/embed-and-store",
                json={
                    "texts": [text],
                    "metadata": {"scope": "global"}
                },
                headers=auth_headers
            )
            assert response.status_code == 200

        # Store vectors in "production" namespace
        prod_texts = [
            "Production deployment guide",
            "Production monitoring setup"
        ]
        for text in prod_texts:
            response = client.post(
                f"/v1/public/{test_project_id}/embeddings/embed-and-store",
                json={
                    "texts": [text],
                    "namespace": "production",
                    "metadata": {"scope": "production"}
                },
                headers=auth_headers
            )
            assert response.status_code == 200

        # Search in default namespace
        search_default = client.post(
            f"/v1/public/{test_project_id}/embeddings/search",
            json={
                "query": "configuration",
                "top_k": 10
            },
            headers=auth_headers
        )

        assert search_default.status_code == 200
        default_data = search_default.json()

        assert default_data["namespace"] == "default"
        for result in default_data["results"]:
            assert result["metadata"]["scope"] == "global"
            assert "Production" not in result["document"]

        # Search in production namespace
        search_prod = client.post(
            f"/v1/public/{test_project_id}/embeddings/search",
            json={
                "query": "deployment",
                "namespace": "production",
                "top_k": 10
            },
            headers=auth_headers
        )

        assert search_prod.status_code == 200
        prod_data = search_prod.json()

        assert prod_data["namespace"] == "production"
        for result in prod_data["results"]:
            assert result["metadata"]["scope"] == "production"
            assert "Production" in result["document"]

    def test_search_empty_namespace_returns_empty_results(self, client, auth_headers, test_project_id):
        """
        Issue #23: Searching empty namespace returns empty results.

        Verify that searching a namespace with no vectors returns empty results list.
        """
        # Store vector in one namespace
        store_response = client.post(
            f"/v1/public/{test_project_id}/embeddings/embed-and-store",
            json={
                "texts": ["Some content"],
                "namespace": "populated_namespace"
            },
            headers=auth_headers
        )
        assert store_response.status_code == 200

        # Search in different, empty namespace
        search_response = client.post(
            f"/v1/public/{test_project_id}/embeddings/search",
            json={
                "query": "content",
                "namespace": "empty_namespace",
                "top_k": 10
            },
            headers=auth_headers
        )

        assert search_response.status_code == 200
        data = search_response.json()

        assert data["namespace"] == "empty_namespace"
        assert len(data["results"]) == 0

    def test_search_namespace_validation(self, client, auth_headers, test_project_id):
        """
        Issue #23: Namespace validation on search endpoint.

        Verify that search endpoint validates namespace format (same rules as storage).
        """
        # Test invalid namespace characters
        invalid_namespaces = [
            "has/slash",
            "has spaces",
            "has@symbol",
            "has#hash",
            "../traversal"
        ]

        for invalid_ns in invalid_namespaces:
            search_response = client.post(
                f"/v1/public/{test_project_id}/embeddings/search",
                json={
                    "query": "test query",
                    "namespace": invalid_ns,
                    "top_k": 10
                },
                headers=auth_headers
            )

            # Should return validation error
            assert search_response.status_code == 422
            error_data = search_response.json()
            assert "detail" in error_data

    def test_search_with_valid_namespace_formats(self, client, auth_headers, test_project_id):
        """
        Issue #23: Search accepts valid namespace formats.

        Verify that search accepts alphanumeric, hyphens, and underscores.
        Per namespace validation rules: only a-z, A-Z, 0-9, underscore, hyphen are valid.
        """
        valid_namespaces = [
            "simple",
            "with-hyphens",
            "with_underscores",
            "MixedCase123",
            "mixed-chars_123"
        ]

        for namespace in valid_namespaces:
            # Store a vector in this namespace
            store_response = client.post(
                f"/v1/public/{test_project_id}/embeddings/embed-and-store",
                json={
                    "texts": [f"Content for {namespace}"],
                    "namespace": namespace
                },
                headers=auth_headers
            )
            assert store_response.status_code == 200

            # Search in this namespace
            search_response = client.post(
                f"/v1/public/{test_project_id}/embeddings/search",
                json={
                    "query": "content",
                    "namespace": namespace,
                    "top_k": 10
                },
                headers=auth_headers
            )

            assert search_response.status_code == 200
            data = search_response.json()
            assert data["namespace"] == namespace

    def test_search_with_metadata_filter_and_namespace(self, client, auth_headers, test_project_id):
        """
        Issue #23: Metadata filtering is scoped within namespace.

        Verify that metadata filters only apply to vectors within the specified namespace.
        """
        # Store vectors in namespace "app_logs" with different severities
        for severity in ["info", "warning", "error"]:
            for i in range(2):
                response = client.post(
                    f"/v1/public/{test_project_id}/embeddings/embed-and-store",
                    json={
                        "texts": [f"Log message {severity} {i}"],
                        "namespace": "app_logs",
                        "metadata": {"severity": severity, "app": "main"}
                    },
                    headers=auth_headers
                )
                assert response.status_code == 200

        # Store vectors in namespace "audit_logs" with same severities
        for severity in ["info", "warning", "error"]:
            response = client.post(
                f"/v1/public/{test_project_id}/embeddings/embed-and-store",
                json={
                    "texts": [f"Audit log {severity}"],
                    "namespace": "audit_logs",
                    "metadata": {"severity": severity, "app": "audit"}
                },
                headers=auth_headers
            )
            assert response.status_code == 200

        # Search in app_logs namespace with severity filter
        search_response = client.post(
            f"/v1/public/{test_project_id}/embeddings/search",
            json={
                "query": "log",
                "namespace": "app_logs",
                "metadata_filter": {"severity": "error"},
                "top_k": 10
            },
            headers=auth_headers
        )

        assert search_response.status_code == 200
        data = search_response.json()

        # Should only find error logs from app_logs namespace
        assert data["namespace"] == "app_logs"
        for result in data["results"]:
            assert result["metadata"]["severity"] == "error"
            assert result["metadata"]["app"] == "main"
            assert "audit" not in result["document"].lower()

    def test_search_namespace_case_sensitivity(self, client, auth_headers, test_project_id):
        """
        Issue #23: Namespace search is case-sensitive.

        Verify that "Namespace" and "namespace" are treated as different namespaces.
        """
        # Store in lowercase namespace
        store_lower = client.post(
            f"/v1/public/{test_project_id}/embeddings/embed-and-store",
            json={
                "texts": ["Lowercase namespace content"],
                "namespace": "myspace"
            },
            headers=auth_headers
        )
        assert store_lower.status_code == 200

        # Store in uppercase namespace
        store_upper = client.post(
            f"/v1/public/{test_project_id}/embeddings/embed-and-store",
            json={
                "texts": ["Uppercase namespace content"],
                "namespace": "MYSPACE"
            },
            headers=auth_headers
        )
        assert store_upper.status_code == 200

        # Search lowercase namespace
        search_lower = client.post(
            f"/v1/public/{test_project_id}/embeddings/search",
            json={
                "query": "content",
                "namespace": "myspace",
                "top_k": 10
            },
            headers=auth_headers
        )

        assert search_lower.status_code == 200
        lower_data = search_lower.json()
        assert lower_data["namespace"] == "myspace"
        assert lower_data["results"][0]["document"] == "Lowercase namespace content"

        # Search uppercase namespace
        search_upper = client.post(
            f"/v1/public/{test_project_id}/embeddings/search",
            json={
                "query": "content",
                "namespace": "MYSPACE",
                "top_k": 10
            },
            headers=auth_headers
        )

        assert search_upper.status_code == 200
        upper_data = search_upper.json()
        assert upper_data["namespace"] == "MYSPACE"
        assert upper_data["results"][0]["document"] == "Uppercase namespace content"

    def test_search_response_includes_namespace_confirmation(self, client, auth_headers, test_project_id):
        """
        Issue #23: Search response confirms namespace that was searched.

        Verify that response includes namespace field to confirm scope.
        """
        # Store vector
        store_response = client.post(
            f"/v1/public/{test_project_id}/embeddings/embed-and-store",
            json={
                "texts": ["Test content"],
                "namespace": "confirmation_test"
            },
            headers=auth_headers
        )
        assert store_response.status_code == 200

        # Search with namespace
        search_response = client.post(
            f"/v1/public/{test_project_id}/embeddings/search",
            json={
                "query": "test",
                "namespace": "confirmation_test",
                "top_k": 10
            },
            headers=auth_headers
        )

        assert search_response.status_code == 200
        data = search_response.json()

        # Verify response confirms searched namespace
        assert "namespace" in data
        assert data["namespace"] == "confirmation_test"

    def test_search_top_k_scoped_to_namespace(self, client, auth_headers, test_project_id):
        """
        Issue #23: top_k parameter is scoped to namespace.

        Verify that top_k only limits results within the searched namespace.
        """
        # Store 10 vectors in namespace "limited"
        for i in range(10):
            response = client.post(
                f"/v1/public/{test_project_id}/embeddings/embed-and-store",
                json={
                    "texts": [f"Limited namespace vector {i}"],
                    "namespace": "limited"
                },
                headers=auth_headers
            )
            assert response.status_code == 200

        # Store 5 vectors in namespace "other"
        for i in range(5):
            response = client.post(
                f"/v1/public/{test_project_id}/embeddings/embed-and-store",
                json={
                    "texts": [f"Other namespace vector {i}"],
                    "namespace": "other"
                },
                headers=auth_headers
            )
            assert response.status_code == 200

        # Search in "limited" namespace with top_k=3
        search_response = client.post(
            f"/v1/public/{test_project_id}/embeddings/search",
            json={
                "query": "vector",
                "namespace": "limited",
                "top_k": 3
            },
            headers=auth_headers
        )

        assert search_response.status_code == 200
        data = search_response.json()

        # Should return exactly 3 results, all from "limited" namespace
        assert data["namespace"] == "limited"
        assert len(data["results"]) == 3
        for result in data["results"]:
            assert "Limited namespace" in result["document"]

    def test_search_similarity_threshold_scoped_to_namespace(self, client, auth_headers, test_project_id):
        """
        Issue #23: Similarity threshold is scoped to namespace.

        Verify that similarity filtering only applies within searched namespace.
        """
        # Store vectors in namespace "threshold_test"
        store_response = client.post(
            f"/v1/public/{test_project_id}/embeddings/embed-and-store",
            json={
                "texts": ["Exact match query text"],
                "namespace": "threshold_test"
            },
            headers=auth_headers
        )
        assert store_response.status_code == 200

        # Store vectors in another namespace (should not appear in results)
        store_response_2 = client.post(
            f"/v1/public/{test_project_id}/embeddings/embed-and-store",
            json={
                "texts": ["Exact match query text"],
                "namespace": "other_namespace"
            },
            headers=auth_headers
        )
        assert store_response_2.status_code == 200

        # Search with high similarity threshold
        search_response = client.post(
            f"/v1/public/{test_project_id}/embeddings/search",
            json={
                "query": "Exact match query text",
                "namespace": "threshold_test",
                "similarity_threshold": 0.9,
                "top_k": 10
            },
            headers=auth_headers
        )

        assert search_response.status_code == 200
        data = search_response.json()

        # Should only find vector from threshold_test namespace
        assert data["namespace"] == "threshold_test"
        for result in data["results"]:
            assert result["score"] >= 0.9
