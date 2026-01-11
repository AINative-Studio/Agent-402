#!/usr/bin/env python3
"""
Fix test field names: "texts" → "documents"

The embed-and-store endpoint uses EmbedAndStoreRequest schema which expects "documents" field,
not "texts" field.
"""
import re
from pathlib import Path


def fix_file(file_path: Path) -> int:
    """Replace "texts": with "documents": in JSON contexts."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Replace "texts": with "documents": in JSON payload contexts
    new_content = content.replace('"texts":', '"documents":')

    if new_content != content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        # Count replacements
        return new_content.count('"documents":') - content.count('"documents":')

    return 0


def main():
    test_file = Path("app/tests/test_embed_and_store.py")

    if not test_file.exists():
        print(f"Error: {test_file} not found!")
        return

    print("🔧 Fixing field names in test_embed_and_store.py...")
    replacements = fix_file(test_file)

    if replacements > 0:
        print(f"✅ Fixed {replacements} occurrences: 'texts' → 'documents'")
    else:
        print("ℹ️  No changes needed")


if __name__ == "__main__":
    main()
