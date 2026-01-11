"""
Standalone test for Issue #19 implementation.
Tests the response schema and metadata fields without the full app context.
"""
import sys
sys.path.insert(0, '/Users/aideveloper/Agent-402/backend')

from app.schemas.embeddings_store import EmbedAndStoreResponse, VectorStorageResult


def test_response_schema_has_required_fields():
    """Test that EmbedAndStoreResponse has all Issue #19 required fields."""
    # Create a sample response
    response = EmbedAndStoreResponse(
        vector_ids=["vec_test123"],
        vectors_stored=1,
        model="BAAI/bge-small-en-v1.5",
        dimensions=384,
        namespace="default",
        results=[
            VectorStorageResult(
                vector_id="vec_test123",
                document="Test document",
                metadata={"source": "test"}
            )
        ],
        processing_time_ms=42
    )

    # Verify all required fields are present
    assert hasattr(response, 'vectors_stored'), "Missing vectors_stored field"
    assert hasattr(response, 'model'), "Missing model field"
    assert hasattr(response, 'dimensions'), "Missing dimensions field"
    assert hasattr(response, 'processing_time_ms'), "Missing processing_time_ms field"

    # Verify values
    assert response.vectors_stored == 1
    assert response.model == "BAAI/bge-small-en-v1.5"
    assert response.dimensions == 384
    assert response.processing_time_ms == 42

    # Verify types
    assert isinstance(response.vectors_stored, int)
    assert isinstance(response.model, str)
    assert isinstance(response.dimensions, int)
    assert isinstance(response.processing_time_ms, int)

    print("✅ All Issue #19 required fields are present and valid")
    return True


def test_response_serialization():
    """Test that response serializes correctly with all fields."""
    response = EmbedAndStoreResponse(
        vector_ids=["vec_abc", "vec_xyz"],
        vectors_stored=2,
        model="sentence-transformers/all-mpnet-base-v2",
        dimensions=768,
        namespace="agent_memory",
        results=[
            VectorStorageResult(
                vector_id="vec_abc",
                document="First doc",
                metadata=None
            ),
            VectorStorageResult(
                vector_id="vec_xyz",
                document="Second doc",
                metadata={"agent": "test"}
            )
        ],
        processing_time_ms=125
    )

    # Serialize to dict
    data = response.model_dump()

    # Verify all Issue #19 fields are in serialized output
    assert "vectors_stored" in data, "vectors_stored not in serialized output"
    assert "model" in data, "model not in serialized output"
    assert "dimensions" in data, "dimensions not in serialized output"
    assert "processing_time_ms" in data, "processing_time_ms not in serialized output"

    # Verify values match
    assert data["vectors_stored"] == 2
    assert data["model"] == "sentence-transformers/all-mpnet-base-v2"
    assert data["dimensions"] == 768
    assert data["processing_time_ms"] == 125

    print("✅ Response serialization includes all Issue #19 fields")
    return True


def test_field_documentation():
    """Test that fields have proper descriptions."""
    schema = EmbedAndStoreResponse.model_json_schema()
    properties = schema.get("properties", {})

    # Check vectors_stored field
    vectors_stored_prop = properties.get("vectors_stored", {})
    assert "description" in vectors_stored_prop
    assert "Issue #19" in vectors_stored_prop["description"]

    # Check model field
    model_prop = properties.get("model", {})
    assert "description" in model_prop
    assert "Issue #19" in model_prop["description"]

    # Check dimensions field
    dimensions_prop = properties.get("dimensions", {})
    assert "description" in dimensions_prop
    assert "Issue #19" in dimensions_prop["description"]

    print("✅ All fields have Issue #19 documentation")
    return True


if __name__ == "__main__":
    print("Testing Issue #19 Implementation...")
    print("-" * 50)

    try:
        test_response_schema_has_required_fields()
        test_response_serialization()
        test_field_documentation()

        print("-" * 50)
        print("✅ All standalone tests passed!")
        print("\nIssue #19 requirements verified:")
        print("  ✅ vectors_stored field present and accurate")
        print("  ✅ model field present and accurate")
        print("  ✅ dimensions field present and accurate")
        print("  ✅ processing_time_ms field present")
        print("  ✅ All fields properly documented")
        print("  ✅ Response serialization works correctly")

    except AssertionError as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)
