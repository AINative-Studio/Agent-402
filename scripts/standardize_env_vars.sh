#!/bin/bash
#
# Epic 10 Story 1 (Issue #46): Standardize all documentation examples to use environment variables
#
# This script updates all markdown documentation files to use $API_KEY, $PROJECT_ID, and $BASE_URL
# instead of hardcoded values.
#

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=== Epic 10 Story 1: Standardizing Environment Variables in Documentation ==="
echo ""

# Counter for tracking
TOTAL_FILES=0
UPDATED_FILES=0

# Function to update a file
update_file() {
    local file="$1"
    local temp_file="${file}.tmp"
    local changed=false

    # Skip if file doesn't exist or is in venv
    if [[ ! -f "$file" ]] || [[ "$file" == *"venv"* ]] || [[ "$file" == *".pytest_cache"* ]]; then
        return
    fi

    ((TOTAL_FILES++))

    # Check if file needs updates
    if grep -q 'X-API-Key.*your\|"http://localhost:8000"\|"https://api\.ainative\.studio"' "$file" 2>/dev/null; then
        echo -e "${YELLOW}Updating:${NC} $file"

        # Create backup
        cp "$file" "${file}.backup"

        # Perform replacements
        sed -E \
            -e 's/"your-api-key"/"$API_KEY"/g' \
            -e 's/"your_api_key"/"$API_KEY"/g' \
            -e 's/"your-api-key-here"/"$API_KEY"/g' \
            -e 's/"your_api_key_here"/"$API_KEY"/g' \
            -e 's/"API-KEY-HERE"/"$API_KEY"/g' \
            -e 's/"proj_abc123"/"$PROJECT_ID"/g' \
            -e 's/"proj_demo_001"/"$PROJECT_ID"/g' \
            -e 's/"project-id"/"$PROJECT_ID"/g' \
            -e 's/"PROJECT-ID"/"$PROJECT_ID"/g' \
            -e 's#"http://localhost:8000"#"$BASE_URL"#g' \
            -e 's#"https://api\.ainative\.studio"#"$BASE_URL"#g' \
            -e 's#http://localhost:8000/#$BASE_URL/#g' \
            -e 's#https://api\.ainative\.studio/#$BASE_URL/#g' \
            "$file" > "$temp_file"

        # Check if file actually changed
        if ! cmp -s "$file" "$temp_file"; then
            mv "$temp_file" "$file"
            rm "${file}.backup"
            ((UPDATED_FILES++))
            changed=true
            echo -e "  ${GREEN}✓${NC} Updated successfully"
        else
            rm "$temp_file" "${file}.backup"
            echo -e "  - No changes needed"
        fi
    fi
}

# Find and update all markdown files
echo "Scanning documentation files..."
echo ""

# Update files in docs/
while IFS= read -r file; do
    update_file "$file"
done < <(find docs -name "*.md" -type f 2>/dev/null || true)

# Update files in backend/
while IFS= read -r file; do
    update_file "$file"
done < <(find backend -name "*.md" -type f ! -path "*/venv/*" ! -path "*/.pytest_cache/*" 2>/dev/null || true)

echo ""
echo "=== Summary ==="
echo -e "Total files scanned: ${TOTAL_FILES}"
echo -e "${GREEN}Files updated: ${UPDATED_FILES}${NC}"
echo ""
echo "=== Done! ==="
echo ""
echo "Next steps:"
echo "1. Review changes: git diff"
echo "2. Test examples still work"
echo "3. Commit changes"
