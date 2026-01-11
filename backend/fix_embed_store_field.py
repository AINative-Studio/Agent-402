#!/usr/bin/env python3
"""
Fix embed-and-store test field names.

Tests are sending "documents" but the endpoint expects "texts" per Epic 4 Issue #16 spec.

Schema definition (app/schemas/embed_store.py:45):
  texts: List[str] = Field(...)

Test files incorrectly use:
  json={"documents": [...]}

Should be:
  json={"texts": [...]}
"""
import re
from pathlib import Path


def fix_embed_store_test_file(file_path: Path) -> tuple[bool, int]:
    """
    Fix field name in embed-and-store test file.

    Changes "documents": to "texts": in JSON payloads.

    Returns:
        (modified, replacements_count)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # Replace "documents": with "texts": in JSON contexts
        # Use word boundary to avoid changing comment text
        content = re.sub(
            r'"documents"\s*:',
            '"texts":',
            content
        )

        # Count replacements
        replacements = content.count('"texts":') - original_content.count('"texts":')

        # Only write if content changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, replacements

        return False, 0

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False, 0


def main():
    """Fix embed-and-store test field names."""
    tests_dir = Path("app/tests")

    if not tests_dir.exists():
        print(f"Error: {tests_dir} directory not found!")
        return

    print("🔧 Fixing embed-and-store test field names (documents → texts)...\n")

    # Target only embed-and-store related test files
    test_files = [
        "test_embed_and_store.py",
        "test_embeddings_search.py",
        "test_embedding_dimension_consistency.py"
    ]

    total_files = 0
    modified_files = 0
    total_replacements = 0

    for test_file_name in test_files:
        test_file = tests_dir / test_file_name
        if not test_file.exists():
            print(f"⚠️  {test_file_name}: File not found, skipping")
            continue

        total_files += 1
        modified, replacements = fix_embed_store_test_file(test_file)

        if modified:
            modified_files += 1
            total_replacements += replacements
            print(f"✅ {test_file_name}: {replacements} field names fixed")
        else:
            print(f"ℹ️  {test_file_name}: No changes needed")

    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"  Total test files processed: {total_files}")
    print(f"  Files modified: {modified_files}")
    print(f"  Total field name replacements: {total_replacements}")
    print(f"{'='*60}\n")

    if modified_files > 0:
        print("✅ Embed-and-store test field names have been fixed!")
        print(f"   Changed: 'documents' → 'texts' (per Epic 4 Issue #16 spec)")
        print(f"   Run: pytest app/tests/test_embed_and_store.py -v")
    else:
        print("ℹ️  No field names needed fixing")


if __name__ == "__main__":
    main()
