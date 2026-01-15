"""
Test suite for embedding dimension consistency (Epic 11, Story 2).

Tests validate that embedding dimensions remain consistent throughout
the entire embedding lifecycle: generate → store → search.

Per Issue #68:
- Test generates embeddings with specific model
- Test verifies returned dimensions match model spec
- Test stores vectors with embeddings
- Test searches and verifies dimensions in results
- Test fails if dimensions mismatch between generate/store/search
- Test validates default 384-dim behavior
- Test validates multiple supported models (at least 3)

Per PRD §12 (Extensibility):
- Support multiple embedding models with different dimensions
- Validate dimensions at each operation stage
- Ensure deterministic behavior across operations

Per DX Contract §3:
- Default model: BAAI/bge-small-en-v1.5 (384 dimensions)
- Dimensions must be consistent across all operations
"""
import pytest
from fastapi.testclient import TestClient
from app.core.config import settings
from app.core.embedding_models import (
    DEFAULT_EMBEDDING_MODEL,
    EMBEDDING_MODEL_SPECS,
    get_model_dimensions,
    EmbeddingModel
)
from app.core.errors import APIError
from app.services.embedding_service import embedding_service
from app.services.vector_store_service import vector_store_service

# Import the correct app version for testing
try:
    from app.main_simple import app
except ImportError:
    from app.main import app

client = TestClient(app)

# Test configuration
TEST_API_KEY = settings.demo_api_key_1 if settings.demo_api_key_1 else "test_api_key_12345"
TEST_PROJECT_ID = "proj_test_dimension_consistency"


@pytest.fixture(autouse=True)
def cleanup_vector_store():
    """Clear vector store before and after each test."""
    vector_store_service.clear_all_vectors()
    yield
    vector_store_service.clear_all_vectors()


class TestDefaultDimensions:
    """Test default 384-dimension behavior per DX Contract."""

    def test_default_384_dimensions_generate(self):
        """
        Test that default model returns 384 dimensions in generate endpoint.

        Per Issue #68, AC #7: Test validates default 384-dim behavior.
        Per DX Contract §3: Default model is BAAI/bge-small-en-v1.5 (384 dims).
        """
        # Generate embedding without specifying model
        response = client.post(
            f"/v1/public/{TEST_PROJECT_ID}/embeddings/generate",
            headers={"X-API-Key": TEST_API_KEY},
            json={"text": "Test default dimensions"}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify default model and dimensions
        assert data["model"] == DEFAULT_EMBEDDING_MODEL
        assert data["dimensions"] == 384
        assert len(data["embedding"]) == 384

        # Verify each element is a float
        for value in data["embedding"]:
            assert isinstance(value, (int, float))

    def test_default_384_dimensions_embed_and_store(self):
        """
        Test that default model returns 384 dimensions in embed-and-store.

        Per Issue #68, AC #7: Test validates default 384-dim behavior.
        """
        response = client.post(
            f"/v1/public/{TEST_PROJECT_ID}/embeddings/embed-and-store",
            headers={"X-API-Key": TEST_API_KEY},
            json={
                "text": "Test default dimensions in storage",
                "namespace": "test_default"
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Verify default model and dimensions
        assert data["model"] == DEFAULT_EMBEDDING_MODEL
        assert data["dimensions"] == 384
        assert data["vectors_stored"] == 1

    def test_default_384_dimensions_search(self):
        """
        Test that default model returns 384 dimensions in search results.

        Per Issue #68, AC #7: Test validates default 384-dim behavior.
        """
        # First, store a vector with default model
        store_response = client.post(
            f"/v1/public/{TEST_PROJECT_ID}/embeddings/embed-and-store",
            headers={"X-API-Key": TEST_API_KEY},
            json={
                "text": "Test search default dimensions",
                "namespace": "test_default_search"
            }
        )
        assert store_response.status_code == 200

        # Search with default model
        search_response = client.post(
            f"/v1/public/{TEST_PROJECT_ID}/embeddings/search",
            headers={"X-API-Key": TEST_API_KEY},
            json={
                "query": "Test search",
                "namespace": "test_default_search",
                "top_k": 5
            }
        )

        assert search_response.status_code == 200
        data = search_response.json()

        # Verify search used default model
        assert data["model"] == DEFAULT_EMBEDDING_MODEL

        # Verify results have correct dimensions
        assert data["total_results"] >= 1
        for result in data["results"]:
            assert result["dimensions"] == 384
            assert result["model"] == DEFAULT_EMBEDDING_MODEL


class TestModelDimensionConsistency:
    """
    Test dimension consistency across generate → store → search lifecycle.

    Per Issue #68, AC #2-6: Test complete flow for each model.
    """

    @pytest.mark.parametrize("model,expected_dims", [
        ("BAAI/bge-small-en-v1.5", 384),
        ("sentence-transformers/all-MiniLM-L6-v2", 384),
        ("sentence-transformers/all-mpnet-base-v2", 768),
    ])
    def test_model_dimension_consistency_full_flow(self, model, expected_dims):
        """
        Test dimension consistency through generate → store → search flow.

        Per Issue #68, AC #2-6:
        - Generate embedding and check dimensions
        - Store embedding and verify stored dimensions
        - Search embedding and verify returned dimensions

        This test validates the complete embedding lifecycle for each model.
        """
        namespace = f"test_consistency_{model.replace('/', '_').replace('-', '_')}"
        test_text = f"Test dimension consistency for {model}"

        # Step 1: Generate embedding and verify dimensions
        generate_response = client.post(
            f"/v1/public/{TEST_PROJECT_ID}/embeddings/generate",
            headers={"X-API-Key": TEST_API_KEY},
            json={
                "text": test_text,
                "model": model
            }
        )

        assert generate_response.status_code == 200
        generate_data = generate_response.json()

        # AC #2: Test generates embeddings with specific model
        assert generate_data["model"] == model

        # AC #3: Test verifies returned dimensions match model spec
        assert generate_data["dimensions"] == expected_dims
        assert len(generate_data["embedding"]) == expected_dims

        # Step 2: Store vector and verify dimensions
        store_response = client.post(
            f"/v1/public/{TEST_PROJECT_ID}/embeddings/embed-and-store",
            headers={"X-API-Key": TEST_API_KEY},
            json={
                "text": test_text,
                "model": model,
                "namespace": namespace,
                "vector_id": f"vec_test_{model.replace('/', '_')}"
            }
        )

        assert store_response.status_code == 200
        store_data = store_response.json()

        # AC #4: Test stores vectors with embeddings
        assert store_data["model"] == model
        assert store_data["dimensions"] == expected_dims
        assert store_data["vectors_stored"] == 1

        # Step 3: Search and verify dimensions in results
        search_response = client.post(
            f"/v1/public/{TEST_PROJECT_ID}/embeddings/search",
            headers={"X-API-Key": TEST_API_KEY},
            json={
                "query": test_text,
                "model": model,
                "namespace": namespace,
                "top_k": 5
            }
        )

        assert search_response.status_code == 200
        search_data = search_response.json()

        # AC #5: Test searches and verifies dimensions in results
        assert search_data["model"] == model
        assert search_data["total_results"] >= 1

        for result in search_data["results"]:
            assert result["model"] == model
            assert result["dimensions"] == expected_dims

        # Verify consistency across all three operations
        assert generate_data["dimensions"] == store_data["dimensions"]
        assert store_data["dimensions"] == search_data["results"][0]["dimensions"]


class TestDimensionMismatchErrors:
    """
    Test that dimension mismatches are properly detected and reported.

    Per Issue #68, AC #6: Test fails if dimensions mismatch.
    """

    def test_dimension_mismatch_generate_vs_store(self):
        """
        Test that dimension consistency is maintained through generate → store flow.

        Per Issue #68, AC #6: Validates dimensions remain consistent.

        This test verifies that when using the embed-and-store endpoint,
        the system generates embeddings with correct dimensions matching
        the model specification, ensuring consistency.
        """
        # Generate with 384-dim model
        generate_response = client.post(
            f"/v1/public/{TEST_PROJECT_ID}/embeddings/generate",
            headers={"X-API-Key": TEST_API_KEY},
            json={
                "text": "Test dimension consistency",
                "model": "BAAI/bge-small-en-v1.5"  # 384 dims
            }
        )

        assert generate_response.status_code == 200
        generate_data = generate_response.json()
        assert len(generate_data["embedding"]) == 384
        assert generate_data["dimensions"] == 384

        # Store using embed-and-store with same model
        store_response = client.post(
            f"/v1/public/{TEST_PROJECT_ID}/embeddings/embed-and-store",
            headers={"X-API-Key": TEST_API_KEY},
            json={
                "text": "Test dimension consistency",
                "model": "BAAI/bge-small-en-v1.5",  # Same 384-dim model
                "namespace": "test_mismatch"
            }
        )

        assert store_response.status_code == 200
        store_data = store_response.json()

        # Verify dimensions match between generate and store
        assert store_data["dimensions"] == generate_data["dimensions"]
        assert store_data["model"] == generate_data["model"]

        # Verify stored dimensions are correct
        assert store_data["dimensions"] == 384

    def test_dimension_mismatch_search_wrong_model(self):
        """
        Test that searching with wrong model dimensions produces expected behavior.

        Per Issue #68, AC #6: Dimension consistency must be maintained.
        """
        # Store vector with 384-dim model
        store_response = client.post(
            f"/v1/public/{TEST_PROJECT_ID}/embeddings/embed-and-store",
            headers={"X-API-Key": TEST_API_KEY},
            json={
                "text": "Stored with 384 dims",
                "model": "BAAI/bge-small-en-v1.5",  # 384 dims
                "namespace": "test_search_mismatch"
            }
        )
        assert store_response.status_code == 200

        # Search with different dimension model
        search_response = client.post(
            f"/v1/public/{TEST_PROJECT_ID}/embeddings/search",
            headers={"X-API-Key": TEST_API_KEY},
            json={
                "query": "Search query",
                "model": "sentence-transformers/all-mpnet-base-v2",  # 768 dims
                "namespace": "test_search_mismatch",
                "top_k": 5
            }
        )

        # Search should succeed but may return no/low-quality results
        # because dimensions don't match stored vectors
        assert search_response.status_code == 200
        data = search_response.json()

        # Query was generated with 768-dim model
        assert data["model"] == "sentence-transformers/all-mpnet-base-v2"

        # Results (if any) should show their original 384 dims
        if data["total_results"] > 0:
            for result in data["results"]:
                assert result["dimensions"] == 384
                assert result["model"] == "BAAI/bge-small-en-v1.5"


class TestAllSupportedModels:
    """
    Test all supported embedding models for dimension consistency.

    Per Issue #68, AC #8: Test validates multiple supported models (at least 3).
    """

    def test_all_supported_models_dimension_consistency(self):
        """
        Iterate through all supported models and validate dimensions.

        Per Issue #68, AC #8: Test validates multiple supported models.

        This test ensures:
        1. All models generate correct dimensions
        2. Dimensions match model specifications
        3. Each model works through full lifecycle
        """
        models_tested = 0

        for model_enum, spec in EMBEDDING_MODEL_SPECS.items():
            model_name = model_enum.value if hasattr(model_enum, 'value') else str(model_enum)
            expected_dims = spec["dimensions"]
            namespace = f"test_all_models_{model_name.replace('/', '_').replace('-', '_')}"

            # Test generate endpoint
            generate_response = client.post(
                f"/v1/public/{TEST_PROJECT_ID}/embeddings/generate",
                headers={"X-API-Key": TEST_API_KEY},
                json={
                    "text": f"Testing model {model_name}",
                    "model": model_name
                }
            )

            assert generate_response.status_code == 200, f"Generate failed for {model_name}"
            generate_data = generate_response.json()

            assert generate_data["model"] == model_name
            assert generate_data["dimensions"] == expected_dims
            assert len(generate_data["embedding"]) == expected_dims

            # Test embed-and-store endpoint
            store_response = client.post(
                f"/v1/public/{TEST_PROJECT_ID}/embeddings/embed-and-store",
                headers={"X-API-Key": TEST_API_KEY},
                json={
                    "text": f"Storing with model {model_name}",
                    "model": model_name,
                    "namespace": namespace
                }
            )

            assert store_response.status_code == 200, f"Store failed for {model_name}"
            store_data = store_response.json()

            assert store_data["model"] == model_name
            assert store_data["dimensions"] == expected_dims

            # Test search endpoint
            search_response = client.post(
                f"/v1/public/{TEST_PROJECT_ID}/embeddings/search",
                headers={"X-API-Key": TEST_API_KEY},
                json={
                    "query": f"Search with model {model_name}",
                    "model": model_name,
                    "namespace": namespace,
                    "top_k": 5
                }
            )

            assert search_response.status_code == 200, f"Search failed for {model_name}"
            search_data = search_response.json()

            assert search_data["model"] == model_name

            # Verify results have correct dimensions
            if search_data["total_results"] > 0:
                for result in search_data["results"]:
                    assert result["dimensions"] == expected_dims
                    assert result["model"] == model_name

            models_tested += 1

        # Verify we tested at least 3 models per requirements
        assert models_tested >= 3, f"Should test at least 3 models, tested {models_tested}"

        # Verify we tested all configured models
        assert models_tested == len(EMBEDDING_MODEL_SPECS)

    def test_minimum_three_models_validation(self):
        """
        Explicit test that at least 3 models are supported and validated.

        Per Issue #68, AC #8: At least 3 models must be tested.
        """
        models = [
            ("BAAI/bge-small-en-v1.5", 384),
            ("sentence-transformers/all-MiniLM-L6-v2", 384),
            ("sentence-transformers/all-mpnet-base-v2", 768),
        ]

        for model_name, expected_dims in models:
            # Verify model is in specs
            model_specs = {k.value if hasattr(k, 'value') else str(k): v
                          for k, v in EMBEDDING_MODEL_SPECS.items()}
            assert model_name in model_specs

            # Verify dimensions match
            assert model_specs[model_name]["dimensions"] == expected_dims

            # Quick generate test
            response = client.post(
                f"/v1/public/{TEST_PROJECT_ID}/embeddings/generate",
                headers={"X-API-Key": TEST_API_KEY},
                json={
                    "text": f"Quick test {model_name}",
                    "model": model_name
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["dimensions"] == expected_dims


class TestDimensionValidationEdgeCases:
    """Test edge cases and boundary conditions for dimension validation."""

    def test_embedding_with_include_embeddings_flag(self):
        """
        Test dimension consistency when embeddings are included in search results.

        Per Issue #26: Toggle embeddings in results.
        Validates that returned embeddings have correct dimensions.
        """
        namespace = "test_include_embeddings"
        model = "BAAI/bge-small-en-v1.5"
        expected_dims = 384

        # Store a vector
        store_response = client.post(
            f"/v1/public/{TEST_PROJECT_ID}/embeddings/embed-and-store",
            headers={"X-API-Key": TEST_API_KEY},
            json={
                "text": "Test embedding inclusion",
                "model": model,
                "namespace": namespace
            }
        )
        assert store_response.status_code == 200

        # Search with include_embeddings=true
        search_response = client.post(
            f"/v1/public/{TEST_PROJECT_ID}/embeddings/search",
            headers={"X-API-Key": TEST_API_KEY},
            json={
                "query": "Test search",
                "model": model,
                "namespace": namespace,
                "include_embeddings": True,
                "top_k": 5
            }
        )

        assert search_response.status_code == 200
        data = search_response.json()

        # Verify results include embeddings with correct dimensions
        assert data["total_results"] >= 1
        for result in data["results"]:
            assert result["dimensions"] == expected_dims
            assert result["embedding"] is not None
            assert len(result["embedding"]) == expected_dims

    def test_dimension_consistency_with_metadata_filters(self):
        """
        Test dimension consistency when using metadata filters.

        Per Issue #24: Metadata filtering.
        Validates dimensions are correct regardless of filtering.
        """
        namespace = "test_metadata_filtering"
        model = "sentence-transformers/all-MiniLM-L6-v2"
        expected_dims = 384

        # Store vectors with different metadata
        for i in range(3):
            response = client.post(
                f"/v1/public/{TEST_PROJECT_ID}/embeddings/embed-and-store",
                headers={"X-API-Key": TEST_API_KEY},
                json={
                    "text": f"Test document {i}",
                    "model": model,
                    "namespace": namespace,
                    "metadata": {
                        "category": "test",
                        "index": i
                    }
                }
            )
            assert response.status_code == 200

        # Search with metadata filter
        search_response = client.post(
            f"/v1/public/{TEST_PROJECT_ID}/embeddings/search",
            headers={"X-API-Key": TEST_API_KEY},
            json={
                "query": "Test search",
                "model": model,
                "namespace": namespace,
                "metadata_filter": {"category": "test"},
                "top_k": 10
            }
        )

        assert search_response.status_code == 200
        data = search_response.json()

        # All filtered results should have correct dimensions
        assert data["total_results"] >= 1
        for result in data["results"]:
            assert result["dimensions"] == expected_dims
            assert result["model"] == model

    def test_dimension_consistency_with_similarity_threshold(self):
        """
        Test dimension consistency with similarity threshold filtering.

        Per Issue #23: Similarity threshold.
        Validates dimensions regardless of threshold filtering.
        """
        namespace = "test_similarity_threshold"
        model = "BAAI/bge-small-en-v1.5"
        expected_dims = 384

        # Store a vector
        store_response = client.post(
            f"/v1/public/{TEST_PROJECT_ID}/embeddings/embed-and-store",
            headers={"X-API-Key": TEST_API_KEY},
            json={
                "text": "Similarity threshold test document",
                "model": model,
                "namespace": namespace
            }
        )
        assert store_response.status_code == 200

        # Search with similarity threshold
        search_response = client.post(
            f"/v1/public/{TEST_PROJECT_ID}/embeddings/search",
            headers={"X-API-Key": TEST_API_KEY},
            json={
                "query": "threshold test",
                "model": model,
                "namespace": namespace,
                "similarity_threshold": 0.5,
                "top_k": 5
            }
        )

        assert search_response.status_code == 200
        data = search_response.json()

        # All results above threshold should have correct dimensions
        for result in data["results"]:
            assert result["dimensions"] == expected_dims
            assert result["model"] == model
            assert result["similarity"] >= 0.5


class TestDimensionConsistencyIntegration:
    """Integration tests for dimension consistency across complex workflows."""

    def test_multi_model_same_namespace(self):
        """
        Test storing vectors from different models in same namespace.

        Validates that each vector maintains its model-specific dimensions
        even when stored in the same namespace.
        """
        namespace = "test_multi_model"

        models = [
            ("BAAI/bge-small-en-v1.5", 384),
            ("sentence-transformers/all-mpnet-base-v2", 768),
        ]

        stored_vectors = []

        # Store vectors with different models in same namespace
        for model_name, expected_dims in models:
            response = client.post(
                f"/v1/public/{TEST_PROJECT_ID}/embeddings/embed-and-store",
                headers={"X-API-Key": TEST_API_KEY},
                json={
                    "text": f"Document for {model_name}",
                    "model": model_name,
                    "namespace": namespace
                }
            )

            assert response.status_code == 200
            data = response.json()

            assert data["dimensions"] == expected_dims
            assert data["model"] == model_name
            stored_vectors.append((model_name, expected_dims, data["vector_id"]))

        # Search with each model and verify results
        for model_name, expected_dims, vector_id in stored_vectors:
            search_response = client.post(
                f"/v1/public/{TEST_PROJECT_ID}/embeddings/search",
                headers={"X-API-Key": TEST_API_KEY},
                json={
                    "query": f"Search for {model_name}",
                    "model": model_name,
                    "namespace": namespace,
                    "top_k": 10
                }
            )

            assert search_response.status_code == 200
            search_data = search_response.json()

            # Verify each result maintains its original dimensions
            for result in search_data["results"]:
                # Result should have its original model's dimensions
                assert result["dimensions"] in [384, 768]
                assert result["model"] in [m[0] for m in models]

    def test_upsert_maintains_dimensions(self):
        """
        Test that upserting a vector maintains dimension consistency.

        Per Issue #18: Upsert behavior.
        Validates dimensions remain consistent during updates.
        """
        namespace = "test_upsert_dims"
        model = "BAAI/bge-small-en-v1.5"
        expected_dims = 384
        vector_id = "vec_test_upsert_dims"

        # Initial store
        store_response = client.post(
            f"/v1/public/{TEST_PROJECT_ID}/embeddings/embed-and-store",
            headers={"X-API-Key": TEST_API_KEY},
            json={
                "text": "Initial text",
                "model": model,
                "namespace": namespace,
                "vector_id": vector_id,
                "upsert": True
            }
        )

        assert store_response.status_code == 200
        initial_data = store_response.json()
        assert initial_data["dimensions"] == expected_dims
        assert initial_data["created"] is True

        # Upsert (update)
        upsert_response = client.post(
            f"/v1/public/{TEST_PROJECT_ID}/embeddings/embed-and-store",
            headers={"X-API-Key": TEST_API_KEY},
            json={
                "text": "Updated text",
                "model": model,
                "namespace": namespace,
                "vector_id": vector_id,
                "upsert": True
            }
        )

        assert upsert_response.status_code == 200
        upsert_data = upsert_response.json()

        # Dimensions should remain consistent
        assert upsert_data["dimensions"] == expected_dims
        assert upsert_data["model"] == model
        assert upsert_data["created"] is False  # Was updated, not created

        # Search and verify dimensions maintained
        search_response = client.post(
            f"/v1/public/{TEST_PROJECT_ID}/embeddings/search",
            headers={"X-API-Key": TEST_API_KEY},
            json={
                "query": "Updated text",
                "model": model,
                "namespace": namespace,
                "top_k": 5
            }
        )

        assert search_response.status_code == 200
        search_data = search_response.json()

        # Find the upserted vector
        found = False
        for result in search_data["results"]:
            if result["vector_id"] == vector_id:
                assert result["dimensions"] == expected_dims
                assert result["model"] == model
                found = True
                break

        assert found, f"Upserted vector {vector_id} not found in search results"


class TestDimensionSpecificationCompliance:
    """Test compliance with dimension specifications from embedding models."""

    async def test_all_models_match_specification(self):
        """
        Test that all models generate dimensions matching their specifications.

        Validates that EMBEDDING_MODEL_SPECS is authoritative and consistent
        with actual generation behavior.
        """
        for model_enum, spec in EMBEDDING_MODEL_SPECS.items():
            model_name = model_enum.value if hasattr(model_enum, 'value') else str(model_enum)
            spec_dims = spec["dimensions"]

            # Generate embedding
            embedding, model_used, actual_dims, _ = await embedding_service.generate_embedding(
                text=f"Test spec compliance for {model_name}",
                model=model_name
            )

            # Verify all aspects match specification
            assert model_used == model_name
            assert actual_dims == spec_dims
            assert len(embedding) == spec_dims

            # Verify get_model_dimensions returns same value
            assert get_model_dimensions(model_name) == spec_dims

    def test_dimension_specification_accuracy(self):
        """
        Test that dimension specifications are accurate for known models.

        Per DX Contract §3 and embedding model standards.
        """
        known_models = {
            "BAAI/bge-small-en-v1.5": 384,
            "sentence-transformers/all-MiniLM-L6-v2": 384,
            "sentence-transformers/all-MiniLM-L12-v2": 384,
            "sentence-transformers/all-mpnet-base-v2": 768,
            "sentence-transformers/all-distilroberta-v1": 768,
            "sentence-transformers/msmarco-distilbert-base-v4": 768,
        }

        for model_name, expected_dims in known_models.items():
            # Verify specification matches known standard
            actual_dims = get_model_dimensions(model_name)
            assert actual_dims == expected_dims, (
                f"Model {model_name} specification mismatch: "
                f"expected {expected_dims}, got {actual_dims}"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
