"""
Simple integration test for Issue #24 - Metadata Filtering.

This script tests the metadata filtering functionality end-to-end
without requiring the full test infrastructure.
"""
from app.services.metadata_filter import MetadataFilter, MetadataFilterOperator


def test_filter_validation():
    """Test that filter validation works correctly."""
    print("Testing filter validation...")

    # Valid filters should not raise
    MetadataFilter.validate_filter(None)
    MetadataFilter.validate_filter({})
    MetadataFilter.validate_filter({"agent_id": "agent_1"})
    MetadataFilter.validate_filter({"score": {"$gte": 0.8}})
    print("✓ Valid filters accepted")

    # Invalid filters should raise
    try:
        MetadataFilter.validate_filter("not a dict")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "must be a dictionary" in str(e)
        print("✓ Invalid filter type rejected")

    try:
        MetadataFilter.validate_filter({"field": {"$invalid": "value"}})
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Unsupported operator" in str(e)
        print("✓ Invalid operator rejected")


def test_equals_filtering():
    """Test simple equality filtering."""
    print("\nTesting equality filtering...")

    metadata_filter = {"agent_id": "agent_1", "source": "memory"}

    # Should match
    vector_meta = {"agent_id": "agent_1", "source": "memory", "score": 0.9}
    assert MetadataFilter.matches_filter(vector_meta, metadata_filter)
    print("✓ Exact match works")

    # Should not match (wrong agent_id)
    vector_meta = {"agent_id": "agent_2", "source": "memory", "score": 0.9}
    assert not MetadataFilter.matches_filter(vector_meta, metadata_filter)
    print("✓ Non-match correctly rejected")


def test_in_operator():
    """Test $in operator filtering."""
    print("\nTesting $in operator...")

    metadata_filter = {"agent_id": {"$in": ["agent_1", "agent_3"]}}

    # Should match
    vector_meta = {"agent_id": "agent_1", "source": "memory"}
    assert MetadataFilter.matches_filter(vector_meta, metadata_filter)
    print("✓ Value in list matches")

    # Should not match
    vector_meta = {"agent_id": "agent_2", "source": "memory"}
    assert not MetadataFilter.matches_filter(vector_meta, metadata_filter)
    print("✓ Value not in list rejected")


def test_numeric_operators():
    """Test numeric comparison operators."""
    print("\nTesting numeric operators...")

    # Greater than or equal
    vector_meta = {"score": 0.9}
    assert MetadataFilter.matches_filter(vector_meta, {"score": {"$gte": 0.8}})
    print("✓ $gte works")

    # Greater than
    assert MetadataFilter.matches_filter(vector_meta, {"score": {"$gt": 0.8}})
    assert not MetadataFilter.matches_filter({"score": 0.8}, {"score": {"$gt": 0.8}})
    print("✓ $gt works")

    # Less than or equal
    assert MetadataFilter.matches_filter({"score": 0.5}, {"score": {"$lte": 0.7}})
    print("✓ $lte works")

    # Less than
    assert MetadataFilter.matches_filter({"score": 0.5}, {"score": {"$lt": 0.7}})
    assert not MetadataFilter.matches_filter({"score": 0.7}, {"score": {"$lt": 0.7}})
    print("✓ $lt works")


def test_contains_operator():
    """Test $contains operator for string matching."""
    print("\nTesting $contains operator...")

    vector_meta = {"status": "active"}
    assert MetadataFilter.matches_filter(vector_meta, {"status": {"$contains": "act"}})
    print("✓ String contains works")

    assert not MetadataFilter.matches_filter(vector_meta, {"status": {"$contains": "pending"}})
    print("✓ String not containing rejected")


def test_exists_operator():
    """Test $exists operator."""
    print("\nTesting $exists operator...")

    vector_meta = {"agent_id": "agent_1", "score": 0.9}

    # Field exists
    assert MetadataFilter.matches_filter(vector_meta, {"score": {"$exists": True}})
    print("✓ Existing field detected")

    # Field doesn't exist
    assert MetadataFilter.matches_filter(vector_meta, {"missing_field": {"$exists": False}})
    print("✓ Missing field detected")

    assert not MetadataFilter.matches_filter(vector_meta, {"score": {"$exists": False}})
    print("✓ Existing field correctly identified")


def test_combined_filters():
    """Test combining multiple filter conditions."""
    print("\nTesting combined filters...")

    metadata_filter = {
        "agent_id": "agent_1",
        "source": "memory",
        "score": {"$gte": 0.8}
    }

    # Should match all conditions
    vector_meta = {"agent_id": "agent_1", "source": "memory", "score": 0.9}
    assert MetadataFilter.matches_filter(vector_meta, metadata_filter)
    print("✓ All conditions matched")

    # Should fail on score
    vector_meta = {"agent_id": "agent_1", "source": "memory", "score": 0.5}
    assert not MetadataFilter.matches_filter(vector_meta, metadata_filter)
    print("✓ Failed condition rejected")


def test_filter_results():
    """Test filtering a list of search results."""
    print("\nTesting filter_results...")

    results = [
        {"vector_id": "1", "metadata": {"agent_id": "agent_1", "score": 0.9}},
        {"vector_id": "2", "metadata": {"agent_id": "agent_2", "score": 0.8}},
        {"vector_id": "3", "metadata": {"agent_id": "agent_1", "score": 0.7}},
    ]

    metadata_filter = {"agent_id": "agent_1", "score": {"$gte": 0.8}}

    filtered = MetadataFilter.filter_results(results, metadata_filter)

    assert len(filtered) == 1
    assert filtered[0]["vector_id"] == "1"
    print("✓ Results filtered correctly")

    # No filter should return all
    all_results = MetadataFilter.filter_results(results, None)
    assert len(all_results) == 3
    print("✓ No filter returns all results")


def test_edge_cases():
    """Test edge cases."""
    print("\nTesting edge cases...")

    # Missing field in metadata
    vector_meta = {"agent_id": "agent_1"}
    assert not MetadataFilter.matches_filter(vector_meta, {"missing_field": "value"})
    print("✓ Missing field handled")

    # Null value
    vector_meta = {"agent_id": None}
    assert MetadataFilter.matches_filter(vector_meta, {"agent_id": None})
    print("✓ Null value equality works")

    # Empty $in list
    assert not MetadataFilter.matches_filter(
        {"agent_id": "agent_1"},
        {"agent_id": {"$in": []}}
    )
    print("✓ Empty $in list returns no matches")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Issue #24: Metadata Filtering Integration Test")
    print("=" * 60)

    try:
        test_filter_validation()
        test_equals_filtering()
        test_in_operator()
        test_numeric_operators()
        test_contains_operator()
        test_exists_operator()
        test_combined_filters()
        test_filter_results()
        test_edge_cases()

        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED")
        print("=" * 60)
        print("\nIssue #24 implementation is working correctly!")
        print("\nSupported filter operations:")
        print("  - equals: {'field': 'value'}")
        print("  - $in: {'field': {'$in': ['val1', 'val2']}}")
        print("  - $contains: {'field': {'$contains': 'substring'}}")
        print("  - $gt, $gte, $lt, $lte: {'field': {'$gte': 0.8}}")
        print("  - $exists: {'field': {'$exists': True}}")
        print("  - $not_equals: {'field': {'$not_equals': 'value'}}")

        return 0
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
