#!/usr/bin/env python3
"""
Fix test field names: stored_count → vectors_stored

The EmbedAndStoreResponse schema uses "vectors_stored" field, not "stored_count".
"""
from pathlib import Path


def fix_file(file_path: Path) -> int:
    """Replace stored_count with vectors_stored in test assertions."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Replace stored_count with vectors_stored
    new_content = content.replace('"stored_count"', '"vectors_stored"')
    new_content = new_content.replace('["stored_count"]', '["vectors_stored"]')
    new_content = new_content.replace("['stored_count']", "['vectors_stored']")
    new_content = new_content.replace('.stored_count', '.vectors_stored')

    if new_content != content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return 1

    return 0


def main():
    test_file = Path("app/tests/test_embed_and_store.py")

    if not test_file.exists():
        print(f"Error: {test_file} not found!")
        return

    print("🔧 Fixing field names in test_embed_and_store.py...")
    changed = fix_file(test_file)

    if changed:
        print(f"✅ Fixed: 'stored_count' → 'vectors_stored'")
    else:
        print("ℹ️  No changes needed")


if __name__ == "__main__":
    main()
