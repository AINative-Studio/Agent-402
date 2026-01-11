#!/usr/bin/env python3
"""
Epic 10 Story 1 (Issue #46): Standardize Environment Variables in Documentation

This script updates all markdown documentation files to use environment variables
($API_KEY, $PROJECT_ID, $BASE_URL) instead of hardcoded values.

Usage:
    python3 scripts/standardize_documentation.py [--dry-run]
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple, Dict

# Files that should NOT be modified (already standardized or special purpose)
SKIP_FILES = {
    'docs/api/API_EXAMPLES.md',  # Already standardized
    'docs/DX_CONTRACT.md',       # Already standardized
    'docs/CRITICAL_REQUIREMENTS.md',  # Already standardized
}

# Patterns to replace
REPLACEMENTS = [
    # API Key patterns
    (r'"your-api-key"', r'$API_KEY'),
    (r'"your_api_key"', r'$API_KEY'),
    (r'"your-api-key-here"', r'$API_KEY'),
    (r'"your_api_key_here"', r'$API_KEY'),
    (r'"API-KEY-HERE"', r'$API_KEY'),
    (r'your_api_key_here', r'$API_KEY'),
    (r'your-api-key-here', r'$API_KEY'),
    (r'your-api-key', r'$API_KEY'),
    (r'your_api_key', r'$API_KEY'),

    # Project ID patterns
    (r'"proj_abc123"', r'$PROJECT_ID'),
    (r'"proj_demo_001"', r'$PROJECT_ID'),
    (r'"project-id"', r'$PROJECT_ID'),
    (r'"PROJECT-ID"', r'$PROJECT_ID'),
    (r'proj_abc123', r'$PROJECT_ID'),
    (r'proj_demo_001', r'$PROJECT_ID'),

    # Base URL patterns (in curl commands)
    (r'http://localhost:8000/', r'$BASE_URL/'),
    (r'https://api\.ainative\.studio/', r'$BASE_URL/'),

    # Base URL patterns (in quoted strings)
    (r'"http://localhost:8000"', r'"$BASE_URL"'),
    (r'"https://api\.ainative\.studio"', r'"$BASE_URL"'),
]

# Standard environment setup block to add
ENV_SETUP_BLOCK = """## Environment Setup

```bash
# Set standard environment variables
export API_KEY="your_api_key_here"
export PROJECT_ID="proj_abc123"
export BASE_URL="https://api.ainative.studio"
```

"""


def should_skip(file_path: Path) -> bool:
    """Check if file should be skipped"""
    # Skip if in venv or pytest cache
    if 'venv' in str(file_path) or '.pytest_cache' in str(file_path):
        return True

    # Skip if in exclude list
    try:
        rel_path = str(file_path.relative_to(Path.cwd()))
    except ValueError:
        rel_path = str(file_path)

    if rel_path in SKIP_FILES:
        return True

    return False


def needs_env_setup(content: str) -> bool:
    """Check if file needs environment setup block"""
    # Already has environment setup
    if '## Environment Setup' in content or '### Environment Setup' in content:
        return False

    # Has API examples but no setup
    if ('X-API-Key' in content or 'curl' in content) and 'export API_KEY' not in content:
        return True

    return False


def add_env_setup(content: str) -> str:
    """Add environment setup block at appropriate location"""
    lines = content.split('\n')
    result = []
    added = False

    for i, line in enumerate(lines):
        result.append(line)

        # Add after first heading section (usually Overview or similar)
        if not added and line.startswith('##') and i > 10:
            # Check if next few lines might be good place
            next_section = '\n'.join(lines[i+1:i+5])
            if 'curl' in next_section or 'Example' in next_section:
                result.append('')
                result.append(ENV_SETUP_BLOCK.rstrip())
                result.append('')
                added = True

    return '\n'.join(result) if added else content


def standardize_file(file_path: Path, dry_run: bool = False) -> Tuple[bool, int]:
    """
    Standardize environment variables in a file

    Returns:
        (changed, num_replacements)
    """
    if should_skip(file_path):
        return False, 0

    try:
        content = file_path.read_text(encoding='utf-8')
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return False, 0

    original_content = content
    num_replacements = 0

    # Apply replacements
    for pattern, replacement in REPLACEMENTS:
        new_content, n = re.subn(pattern, replacement, content)
        if n > 0:
            num_replacements += n
            content = new_content

    # Add environment setup if needed
    if needs_env_setup(content) and num_replacements > 0:
        content = add_env_setup(content)

    # Check if anything changed
    if content == original_content:
        return False, 0

    # Write changes if not dry run
    if not dry_run:
        try:
            # Create backup
            backup_path = file_path.with_suffix('.md.backup')
            backup_path.write_text(original_content, encoding='utf-8')

            # Write updated content
            file_path.write_text(content, encoding='utf-8')

            # Remove backup if successful
            backup_path.unlink()
        except Exception as e:
            print(f"Error writing {file_path}: {e}")
            return False, 0

    return True, num_replacements


def main():
    """Main function"""
    dry_run = '--dry-run' in sys.argv

    print("=" * 70)
    print("Epic 10 Story 1 (Issue #46): Standardize Environment Variables")
    print("=" * 70)
    print()

    if dry_run:
        print("🔍 DRY RUN MODE - No files will be modified")
        print()

    # Find all markdown files
    docs_files = list(Path('docs').rglob('*.md'))
    backend_files = list(Path('backend').rglob('*.md'))
    all_files = docs_files + backend_files

    print(f"Found {len(all_files)} markdown files")
    print()

    stats = {
        'total': 0,
        'skipped': 0,
        'unchanged': 0,
        'updated': 0,
        'total_replacements': 0,
    }

    updated_files: List[Tuple[Path, int]] = []

    for file_path in sorted(all_files):
        stats['total'] += 1

        if should_skip(file_path):
            stats['skipped'] += 1
            continue

        changed, num_replacements = standardize_file(file_path, dry_run)

        if not changed:
            stats['unchanged'] += 1
        else:
            stats['updated'] += 1
            stats['total_replacements'] += num_replacements
            updated_files.append((file_path, num_replacements))
            print(f"{'[DRY RUN] ' if dry_run else ''}✓ Updated: {file_path} ({num_replacements} replacements)")

    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total files:         {stats['total']}")
    print(f"Skipped:             {stats['skipped']}")
    print(f"Unchanged:           {stats['unchanged']}")
    print(f"Updated:             {stats['updated']}")
    print(f"Total replacements:  {stats['total_replacements']}")
    print()

    if updated_files:
        print("Updated files:")
        for file_path, count in updated_files:
            print(f"  - {file_path} ({count} changes)")
        print()

    if dry_run:
        print("This was a dry run. Run without --dry-run to apply changes.")
    else:
        print("✅ All files updated successfully!")
        print()
        print("Next steps:")
        print("1. Review changes: git diff")
        print("2. Test examples still work")
        print("3. Commit changes")

    print()


if __name__ == '__main__':
    main()
