#!/usr/bin/env python3
"""
Fix test URLs to include {project_id} path parameter.

This script updates test files that use embeddings/vectors endpoints
to include the required project_id path parameter.

Tests currently use: /v1/public/embeddings/generate
Should use: /v1/public/proj_demo_u1_001/embeddings/generate
"""
import re
import os
from pathlib import Path

# Default project ID used in tests
DEFAULT_PROJECT_ID = "proj_demo_u1_001"

# URL patterns that need project_id inserted
URL_PATTERNS = [
    # Embeddings endpoints (Epic 3, 4, 5)
    (r'"/v1/public/embeddings/generate"', f'"/v1/public/{DEFAULT_PROJECT_ID}/embeddings/generate"'),
    (r'"/v1/public/embeddings/embed-and-store"', f'"/v1/public/{DEFAULT_PROJECT_ID}/embeddings/embed-and-store"'),
    (r'"/v1/public/embeddings/search"', f'"/v1/public/{DEFAULT_PROJECT_ID}/embeddings/search"'),
    (r'"/v1/public/embeddings/models"', f'"/v1/public/embeddings/models"'),  # No project_id needed

    # Vector endpoints (Epic 6)
    (r'"/v1/public/database/vectors/upsert"', f'"/v1/public/{DEFAULT_PROJECT_ID}/database/vectors/upsert"'),
    (r'"/v1/public/database/vectors/search"', f'"/v1/public/{DEFAULT_PROJECT_ID}/database/vectors/search"'),
    (r'"/v1/public/database/vectors/list"', f'"/v1/public/{DEFAULT_PROJECT_ID}/database/vectors/list"'),

    # Wrong paths that should have /database/
    (r'"/v1/public/vectors/upsert"', f'"/v1/public/{DEFAULT_PROJECT_ID}/database/vectors/upsert"'),
    (r'"/v1/public/vectors/search"', f'"/v1/public/{DEFAULT_PROJECT_ID}/database/vectors/search"'),
]

def fix_test_file(file_path: Path) -> tuple[bool, int]:
    """
    Fix URL patterns in a single test file.

    Returns:
        (modified, replacements_count)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content
        replacements = 0

        for pattern, replacement in URL_PATTERNS:
            # Count matches before replacing
            matches = len(re.findall(pattern, content))
            if matches > 0:
                content = re.sub(pattern, replacement, content)
                replacements += matches

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
    """Fix all test files in app/tests directory."""
    tests_dir = Path("app/tests")

    if not tests_dir.exists():
        print(f"Error: {tests_dir} directory not found!")
        return

    print("🔧 Fixing test URLs to include project_id parameter...\n")

    total_files = 0
    modified_files = 0
    total_replacements = 0

    # Process all Python test files
    for test_file in sorted(tests_dir.glob("test_*.py")):
        total_files += 1
        modified, replacements = fix_test_file(test_file)

        if modified:
            modified_files += 1
            total_replacements += replacements
            print(f"✅ {test_file.name}: {replacements} URLs fixed")

    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"  Total test files scanned: {total_files}")
    print(f"  Files modified: {modified_files}")
    print(f"  Total URL replacements: {total_replacements}")
    print(f"{'='*60}\n")

    if modified_files > 0:
        print("✅ Test URLs have been fixed!")
        print(f"   Run: pytest app/tests/ -v")
    else:
        print("ℹ️  No URLs needed fixing")

if __name__ == "__main__":
    main()
