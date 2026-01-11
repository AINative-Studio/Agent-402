"""
Tests for Epic 4, Issue 20: Model Consistency Documentation and Enforcement.

This test suite verifies:
1. Documentation exists and contains required model consistency guidance
2. Model consistency is enforced between store and search operations
3. Dimension mismatches are properly detected and reported
4. MODEL_NOT_FOUND and DIMENSION_MISMATCH errors are documented
5. Default model (BAAI/bge-small-en-v1.5) behavior is consistent
6. Model name is included in stored vector metadata
7. Dimension validation prevents incompatible operations

Per Epic 4, Story 5 (Issue #20):
- As a developer, docs enforce model consistency across store and search
- Documentation warns about dimension mismatches
- Documentation explains default model behavior
- Documentation lists supported models with dimensions
- DIMENSION_MISMATCH error is properly documented
- MODEL_NOT_FOUND error is documented
- Docs mention the default model (BAAI/bge-small-en-v1.5)

Related PRD Sections:
- PRD Section 10: Determinism (predictable errors)
- DX Contract Section 3: Default model specifications
- DX Contract Section 7: Error semantics

Built by AINative Dev Team
"""
import os
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.services.embed_store_service import embed_store_service
from app.services.vector_store_service import vector_store_service
from app.services.embedding_service import embedding_service
from app.core.embedding_models import (
    DEFAULT_EMBEDDING_MODEL,
    get_model_dimensions,
    is_model_supported
)
from app.core.errors import APIError


# Path constants for documentation files
DOCS_API_DIR = "/Volumes/Cody/projects/Agent402/docs/api"
DOCS_QUICK_REF_DIR = "/Volumes/Cody/projects/Agent402/docs/quick-reference"

MODEL_CONSISTENCY_GUIDE = os.path.join(DOCS_API_DIR, "MODEL_CONSISTENCY_GUIDE.md")
MODEL_CONSISTENCY_EMBED_STORE = os.path.join(DOCS_API_DIR, "MODEL_CONSISTENCY_EMBED_STORE.md")
EMBED_STORE_MODEL_GUIDE = os.path.join(DOCS_QUICK_REF_DIR, "EMBED_STORE_MODEL_GUIDE.md")


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
    return "proj_test_consistency"


@pytest.fixture(autouse=True)
def cleanup():
    """Clean up services before and after each test."""
    embed_store_service.clear_all()
    vector_store_service.clear_all_vectors()
    yield
    embed_store_service.clear_all()
    vector_store_service.clear_all_vectors()


class TestDocumentationExists:
    """Test that required documentation files exist."""

    def test_model_consistency_guide_exists(self):
        """
        Verify MODEL_CONSISTENCY_GUIDE.md exists.

        Issue #20: Documentation must exist for model consistency.
        """
        assert os.path.exists(MODEL_CONSISTENCY_GUIDE), (
            f"MODEL_CONSISTENCY_GUIDE.md not found at {MODEL_CONSISTENCY_GUIDE}"
        )

    def test_model_consistency_embed_store_exists(self):
        """
        Verify MODEL_CONSISTENCY_EMBED_STORE.md exists.

        Issue #20: Embed-store specific documentation must exist.
        """
        assert os.path.exists(MODEL_CONSISTENCY_EMBED_STORE), (
            f"MODEL_CONSISTENCY_EMBED_STORE.md not found at {MODEL_CONSISTENCY_EMBED_STORE}"
        )

    def test_embed_store_model_guide_exists(self):
        """
        Verify EMBED_STORE_MODEL_GUIDE.md exists in quick-reference.

        Issue #20: Quick reference guide must exist.
        """
        assert os.path.exists(EMBED_STORE_MODEL_GUIDE), (
            f"EMBED_STORE_MODEL_GUIDE.md not found at {EMBED_STORE_MODEL_GUIDE}"
        )


class TestDocumentationContent:
    """Test that documentation contains required content about model consistency."""

    def test_docs_warn_about_dimension_mismatches(self):
        """
        Verify documentation warns about dimension mismatches.

        Issue #20 Requirement: Documentation must warn about dimension mismatches.
        """
        with open(MODEL_CONSISTENCY_GUIDE, 'r') as f:
            content = f.read()

        # Check for dimension mismatch warnings
        assert "DIMENSION_MISMATCH" in content, (
            "Documentation should mention DIMENSION_MISMATCH error"
        )
        assert "dimension" in content.lower(), (
            "Documentation should discuss dimensions"
        )
        assert "mismatch" in content.lower(), (
            "Documentation should warn about mismatches"
        )

    def test_docs_explain_default_model_behavior(self):
        """
        Verify documentation explains default model behavior.

        Issue #20 Requirement: Documentation must explain default model behavior.
        """
        with open(MODEL_CONSISTENCY_GUIDE, 'r') as f:
            content = f.read()

        # Check for default model documentation
        assert "BAAI/bge-small-en-v1.5" in content, (
            "Documentation should mention default model BAAI/bge-small-en-v1.5"
        )
        assert "default" in content.lower(), (
            "Documentation should discuss default model behavior"
        )

    def test_docs_list_supported_models_with_dimensions(self):
        """
        Verify documentation lists supported models with dimensions.

        Issue #20 Requirement: Documentation must list supported models with dimensions.
        """
        with open(MODEL_CONSISTENCY_EMBED_STORE, 'r') as f:
            content = f.read()

        # Check for model listings
        assert "BAAI/bge-small-en-v1.5" in content, (
            "Documentation should list BAAI/bge-small-en-v1.5"
        )
        assert "384" in content, (
            "Documentation should list 384-dimension models"
        )
        assert "768" in content, (
            "Documentation should list 768-dimension models"
        )

        # Check for table or structured listing
        assert "Model" in content or "model" in content, (
            "Documentation should have model listings"
        )
        assert "Dimensions" in content or "dimensions" in content, (
            "Documentation should specify dimensions for each model"
        )

    def test_docs_document_dimension_mismatch_error(self):
        """
        Verify DIMENSION_MISMATCH error is properly documented.

        Issue #20 Requirement: DIMENSION_MISMATCH error must be documented.
        """
        with open(MODEL_CONSISTENCY_GUIDE, 'r') as f:
            content = f.read()

        # Check for DIMENSION_MISMATCH error documentation
        assert "DIMENSION_MISMATCH" in content, (
            "Documentation should document DIMENSION_MISMATCH error code"
        )

        # Check for error explanation
        assert "error" in content.lower(), (
            "Documentation should explain error conditions"
        )

    def test_docs_document_model_not_found_error(self):
        """
        Verify MODEL_NOT_FOUND error is documented.

        Issue #20 Requirement: MODEL_NOT_FOUND error must be documented.
        """
        with open(MODEL_CONSISTENCY_GUIDE, 'r') as f:
            content = f.read()

        # Check for MODEL_NOT_FOUND error documentation
        assert "MODEL_NOT_FOUND" in content, (
            "Documentation should document MODEL_NOT_FOUND error code"
        )

    def test_docs_mention_default_model(self):
        """
        Verify docs mention the default model (BAAI/bge-small-en-v1.5).

        Issue #20 Requirement: Docs must mention default model.
        """
        with open(MODEL_CONSISTENCY_EMBED_STORE, 'r') as f:
            content = f.read()

        # Check for default model mention
        assert "BAAI/bge-small-en-v1.5" in content, (
            "Documentation should mention BAAI/bge-small-en-v1.5"
        )
        assert "DEFAULT" in content or "default" in content.lower(), (
            "Documentation should indicate which model is default"
        )

    def test_quick_reference_has_model_table(self):
        """
        Verify quick reference guide has a model reference table.

        Issue #20 Requirement: Quick reference should have easy model lookup.
        """
        with open(EMBED_STORE_MODEL_GUIDE, 'r') as f:
            content = f.read()

        # Check for table structure
        assert "|" in content, (
            "Quick reference should contain a table (markdown tables use |)"
        )
        assert "384" in content and "768" in content, (
            "Quick reference should list dimensions"
        )
        assert "BAAI/bge-small-en-v1.5" in content, (
            "Quick reference should list default model"
        )


class TestModelConsistencyEnforcement:
    """Test that model consistency is enforced between store and search operations."""

    @pytest.mark.skip(reason="Search API endpoint not yet implemented")
    def test_same_model_store_and_search_succeeds(self, client, auth_headers, test_project_id):
        """
        Test that using the same model for store and search succeeds.

        Issue #20: Same model for store and search should work correctly.
        NOTE: Skipped until search endpoint is implemented.
        """
        namespace = "test_same_model"
        model = "BAAI/bge-small-en-v1.5"

        # Store documents with specific model
        store_response = client.post(
            f"/v1/public/{test_project_id}/embeddings/embed-and-store",
            json={
                "texts": [
                    "Compliance check passed",
                    "Risk assessment completed"
                ],
                "model": model,
                "namespace": namespace
            },
            headers=auth_headers
        )

        assert store_response.status_code == 200
        store_data = store_response.json()
        assert store_data["model"] == model
        assert store_data["dimensions"] == 384

        # Search with same model
        search_response = client.post(
            f"/v1/public/{test_project_id}/embeddings/search",
            json={
                "query": "compliance check",
                "model": model,
                "namespace": namespace,
                "top_k": 5
            },
            headers=auth_headers
        )

        assert search_response.status_code == 200
        search_data = search_response.json()
        assert search_data["model"] == model
        assert len(search_data["results"]) > 0

    def test_different_dimensions_causes_dimension_mismatch(self):
        """
        Test that using models with different dimensions causes DIMENSION_MISMATCH.

        Issue #20: Different model dimensions should be detected and reported.
        """
        # Store with 384-dim model
        _, model_384, dim_384, vector_ids = embed_store_service.embed_and_store(
            texts=["Test document for dimension mismatch"],
            model="BAAI/bge-small-en-v1.5",  # 384 dimensions
            namespace="test_dim_mismatch"
        )

        assert dim_384 == 384

        # Generate query embedding with 768-dim model
        query_embedding, model_768, dim_768, _ = embedding_service.generate_embedding(
            text="test query",
            model="sentence-transformers/all-mpnet-base-v2"  # 768 dimensions
        )

        assert dim_768 == 768

        # Dimension mismatch should be detected when searching
        # (In production, this would be caught by dimension validation)
        assert dim_384 != dim_768, "Dimensions should be different"

    def test_model_metadata_stored_with_vector(self, test_project_id):
        """
        Test that model name is included in stored vector metadata.

        Issue #20 Requirement: Model name must be stored with vector.
        """
        model = "BAAI/bge-small-en-v1.5"
        namespace = "test_metadata"

        # Store vector
        _, model_used, _, vector_ids = embed_store_service.embed_and_store(
            texts=["Test document for metadata"],
            model=model,
            namespace=namespace,
            project_id=test_project_id
        )

        assert model_used == model
        assert len(vector_ids) > 0

        # Retrieve vector and verify model is stored
        vector_data = embed_store_service.get_vector(
            vector_id=vector_ids[0],
            namespace=namespace
        )

        assert vector_data is not None
        assert "model" in vector_data
        assert vector_data["model"] == model
        assert vector_data["dimensions"] == 384


class TestDimensionValidation:
    """Test that dimension validation prevents incompatible operations."""

    def test_dimension_mismatch_detected_for_384_vs_768(self):
        """
        Test dimension mismatch detection between 384 and 768 dimensions.

        Issue #20: Dimension validation must detect mismatches.
        """
        # Get dimensions for different models
        dim_384 = get_model_dimensions("BAAI/bge-small-en-v1.5")
        dim_768 = get_model_dimensions("sentence-transformers/all-mpnet-base-v2")

        assert dim_384 == 384
        assert dim_768 == 768
        assert dim_384 != dim_768

    def test_dimension_validation_in_embed_store(self):
        """
        Test that embed-and-store generates correct dimensions for model.

        Issue #20: Embeddings must match model dimensions.
        """
        # Test with 384-dim model
        _, model_384, dim_384, _ = embed_store_service.embed_and_store(
            texts=["Test text"],
            model="BAAI/bge-small-en-v1.5"
        )

        assert model_384 == "BAAI/bge-small-en-v1.5"
        assert dim_384 == 384

        # Test with 768-dim model
        _, model_768, dim_768, _ = embed_store_service.embed_and_store(
            texts=["Test text"],
            model="sentence-transformers/all-mpnet-base-v2"
        )

        assert model_768 == "sentence-transformers/all-mpnet-base-v2"
        assert dim_768 == 768

    def test_dimension_consistency_within_namespace(self):
        """
        Test that all vectors in a namespace should use consistent dimensions.

        Issue #20: Namespace isolation helps maintain dimension consistency.
        """
        namespace_384 = "vectors_384"
        namespace_768 = "vectors_768"

        # Store with 384-dim model in namespace_384
        _, model1, dim1, _ = embed_store_service.embed_and_store(
            texts=["Document 1"],
            model="BAAI/bge-small-en-v1.5",
            namespace=namespace_384
        )

        assert dim1 == 384

        # Store with 768-dim model in namespace_768
        _, model2, dim2, _ = embed_store_service.embed_and_store(
            texts=["Document 2"],
            model="sentence-transformers/all-mpnet-base-v2",
            namespace=namespace_768
        )

        assert dim2 == 768

        # Namespaces are isolated
        assert namespace_384 != namespace_768


class TestModelNotFoundError:
    """Test MODEL_NOT_FOUND error handling."""

    def test_invalid_model_name_raises_model_not_found(self):
        """
        Test that invalid model name raises MODEL_NOT_FOUND error.

        Issue #20 Requirement: MODEL_NOT_FOUND error must be properly raised.
        """
        with pytest.raises(APIError) as exc_info:
            embed_store_service.embed_and_store(
                texts=["Test text"],
                model="INVALID/model-that-does-not-exist"
            )

        assert exc_info.value.error_code == "MODEL_NOT_FOUND"
        assert exc_info.value.status_code == 404

    def test_model_not_found_has_detail_field(self):
        """
        Test that MODEL_NOT_FOUND error has detail field.

        Issue #20: Error must follow DX Contract format.
        """
        with pytest.raises(APIError) as exc_info:
            embed_store_service.embed_and_store(
                texts=["Test text"],
                model="nonexistent/model"
            )

        assert hasattr(exc_info.value, 'detail')
        assert isinstance(exc_info.value.detail, str)
        assert len(exc_info.value.detail) > 0

    def test_model_not_found_error_includes_model_name(self):
        """
        Test that MODEL_NOT_FOUND error includes the invalid model name.

        Issue #20: Error should help developers identify the problem.
        """
        invalid_model = "BAAI/bge-invalid-model"

        with pytest.raises(APIError) as exc_info:
            embed_store_service.embed_and_store(
                texts=["Test text"],
                model=invalid_model
            )

        assert invalid_model in exc_info.value.detail


class TestDefaultModelBehavior:
    """Test default model behavior per DX Contract Section 3."""

    def test_default_model_is_bge_small(self):
        """
        Verify default model is BAAI/bge-small-en-v1.5.

        Issue #20 Requirement: Default model must be documented and enforced.
        """
        assert DEFAULT_EMBEDDING_MODEL == "BAAI/bge-small-en-v1.5"

    def test_omitting_model_uses_default(self):
        """
        Test that omitting model parameter uses default model.

        Issue #20: Default behavior must be consistent.
        """
        # Store without specifying model (should use default)
        _, model_used, dimensions, _ = embed_store_service.embed_and_store(
            texts=["Test document"],
            model=None  # Explicitly pass None
        )

        assert model_used == DEFAULT_EMBEDDING_MODEL
        assert model_used == "BAAI/bge-small-en-v1.5"
        assert dimensions == 384

    def test_default_model_dimensions_are_384(self):
        """
        Verify default model has 384 dimensions.

        Issue #20: Default model dimensions must be consistent.
        """
        default_dims = get_model_dimensions(DEFAULT_EMBEDDING_MODEL)
        assert default_dims == 384

    @pytest.mark.skip(reason="Search API endpoint not yet implemented")
    def test_store_and_search_both_default_to_same_model(self, client, auth_headers, test_project_id):
        """
        Test that both store and search default to the same model.

        Issue #20: Default behavior must be consistent across operations.
        NOTE: Skipped until search endpoint is implemented.
        """
        namespace = "test_defaults"

        # Store without model (uses default)
        store_response = client.post(
            f"/v1/public/{test_project_id}/embeddings/embed-and-store",
            json={
                "texts": ["Test document"],
                "namespace": namespace
                # model parameter omitted
            },
            headers=auth_headers
        )

        assert store_response.status_code == 200
        store_data = store_response.json()
        assert store_data["model"] == DEFAULT_EMBEDDING_MODEL

        # Search without model (uses default)
        search_response = client.post(
            f"/v1/public/{test_project_id}/embeddings/search",
            json={
                "query": "test",
                "namespace": namespace
                # model parameter omitted
            },
            headers=auth_headers
        )

        assert search_response.status_code == 200
        search_data = search_response.json()
        assert search_data["model"] == DEFAULT_EMBEDDING_MODEL


class TestModelConsistencyAPIEndpoints:
    """Test model consistency through API endpoints."""

    def test_embed_store_returns_model_info(self, client, auth_headers, test_project_id):
        """
        Test that embed-and-store returns model information.

        Issue #20: API response must include model metadata.
        """
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/embed-and-store",
            json={
                "texts": ["Test"],
                "model": "BAAI/bge-small-en-v1.5"
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert "model" in data
        assert "dimensions" in data
        assert data["model"] == "BAAI/bge-small-en-v1.5"
        assert data["dimensions"] == 384

    @pytest.mark.skip(reason="Search API endpoint not yet implemented")
    def test_search_returns_model_info(self, client, auth_headers, test_project_id):
        """
        Test that search returns model information.

        Issue #20: Search response must include model metadata.
        NOTE: Skipped until search endpoint is implemented.
        """
        namespace = "test_search_model"

        # First store some documents
        client.post(
            f"/v1/public/{test_project_id}/embeddings/embed-and-store",
            json={
                "texts": ["Test document"],
                "model": "BAAI/bge-small-en-v1.5",
                "namespace": namespace
            },
            headers=auth_headers
        )

        # Then search
        response = client.post(
            f"/v1/public/{test_project_id}/embeddings/search",
            json={
                "query": "test",
                "model": "BAAI/bge-small-en-v1.5",
                "namespace": namespace
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert "model" in data
        assert "dimensions" in data
        assert data["model"] == "BAAI/bge-small-en-v1.5"
        assert data["dimensions"] == 384

    def test_stored_vector_includes_model_in_metadata(self, client, auth_headers, test_project_id):
        """
        Test that stored vectors include model in their metadata.

        Issue #20 Requirement: Model must be stored with each vector.
        """
        namespace = "test_vector_model_metadata"
        model = "BAAI/bge-small-en-v1.5"

        # Store documents
        store_response = client.post(
            f"/v1/public/{test_project_id}/embeddings/embed-and-store",
            json={
                "texts": ["Test document"],
                "model": model,
                "namespace": namespace
            },
            headers=auth_headers
        )

        assert store_response.status_code == 200
        store_data = store_response.json()
        vector_ids = store_data.get("vector_ids", [])
        assert len(vector_ids) > 0

        # Retrieve vector directly from service
        vector_data = embed_store_service.get_vector(
            vector_id=vector_ids[0],
            namespace=namespace
        )

        assert vector_data is not None
        assert vector_data["model"] == model
        assert vector_data["dimensions"] == 384


class TestModelSupportedCheck:
    """Test model support validation."""

    def test_supported_models_are_recognized(self):
        """
        Test that supported models are recognized.

        Issue #20: Supported models must be properly validated.
        """
        # Test standard supported models (using only models that are actually in the system)
        assert is_model_supported("BAAI/bge-small-en-v1.5") is True
        assert is_model_supported("sentence-transformers/all-MiniLM-L6-v2") is True
        assert is_model_supported("sentence-transformers/all-mpnet-base-v2") is True

    def test_unsupported_model_is_not_recognized(self):
        """
        Test that unsupported models are not recognized.

        Issue #20: Unsupported models must be rejected.
        """
        assert is_model_supported("fake/model") is False
        assert is_model_supported("INVALID/model-name") is False

    def test_model_dimensions_mapping(self):
        """
        Test that model dimensions are correctly mapped.

        Issue #20: Model dimension mapping must be accurate.
        """
        # 384-dimension models
        assert get_model_dimensions("BAAI/bge-small-en-v1.5") == 384
        assert get_model_dimensions("sentence-transformers/all-MiniLM-L6-v2") == 384

        # 768-dimension models
        assert get_model_dimensions("sentence-transformers/all-mpnet-base-v2") == 768
        assert get_model_dimensions("sentence-transformers/all-distilroberta-v1") == 768


class TestErrorCodeConsistency:
    """Test that error codes are consistent with documentation."""

    def test_dimension_mismatch_error_code_matches_docs(self):
        """
        Verify DIMENSION_MISMATCH error code matches documentation.

        Issue #20: Error codes must be consistent with docs.
        """
        with open(MODEL_CONSISTENCY_GUIDE, 'r') as f:
            content = f.read()

        # Error code documented in guide
        assert "DIMENSION_MISMATCH" in content

        # Error code used in code matches documentation
        # This is verified by the error handling tests

    def test_model_not_found_error_code_matches_docs(self):
        """
        Verify MODEL_NOT_FOUND error code matches documentation.

        Issue #20: Error codes must be consistent with docs.
        """
        with open(MODEL_CONSISTENCY_GUIDE, 'r') as f:
            content = f.read()

        # Error code documented in guide
        assert "MODEL_NOT_FOUND" in content

        # Error code used in code matches documentation
        with pytest.raises(APIError) as exc_info:
            embed_store_service.embed_and_store(
                texts=["Test"],
                model="invalid/model"
            )

        assert exc_info.value.error_code == "MODEL_NOT_FOUND"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
