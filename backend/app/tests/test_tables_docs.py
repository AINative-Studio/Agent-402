"""
Tables API Documentation Validation Tests

Validates Epic 7, Issue 5 - Tables API Documentation:
- Verifies all documentation files exist
- Validates TABLES_API.md contains all required endpoints
- Validates ROW_DATA_WARNING.md contains WRONG and RIGHT patterns
- Validates warning about prohibited field names (data, rows, items)
- Validates no prohibited terms (Claude, Anthropic, ChatGPT, Copilot)
"""

import os
import re
import pytest


# Base path for documentation
DOCS_BASE = "/Volumes/Cody/projects/Agent402/docs"


class TestTablesDocumentationFiles:
    """Test that all required documentation files exist."""

    def test_tables_api_exists(self):
        """Verify TABLES_API.md exists."""
        api_doc = os.path.join(DOCS_BASE, "api", "TABLES_API.md")
        assert os.path.exists(api_doc), f"TABLES_API.md not found at {api_doc}"
        assert os.path.isfile(api_doc), "TABLES_API.md is not a file"

    def test_row_data_warning_exists(self):
        """Verify ROW_DATA_WARNING.md exists."""
        warning_doc = os.path.join(DOCS_BASE, "api", "ROW_DATA_WARNING.md")
        assert os.path.exists(warning_doc), f"ROW_DATA_WARNING.md not found at {warning_doc}"
        assert os.path.isfile(warning_doc), "ROW_DATA_WARNING.md is not a file"

    def test_tables_quick_start_exists(self):
        """Verify TABLES_QUICK_START.md exists."""
        quick_start = os.path.join(DOCS_BASE, "quick-reference", "TABLES_QUICK_START.md")
        assert os.path.exists(quick_start), f"TABLES_QUICK_START.md not found at {quick_start}"
        assert os.path.isfile(quick_start), "TABLES_QUICK_START.md is not a file"


class TestTablesAPIEndpoints:
    """Test that TABLES_API.md contains all required endpoints."""

    @pytest.fixture
    def api_doc_content(self):
        """Load TABLES_API.md content."""
        api_doc = os.path.join(DOCS_BASE, "api", "TABLES_API.md")
        with open(api_doc, 'r', encoding='utf-8') as f:
            return f.read()

    def test_create_table_endpoint(self, api_doc_content):
        """Verify Create Table endpoint is documented."""
        assert "POST /v1/public/database/tables" in api_doc_content
        assert "Create Table" in api_doc_content or "create table" in api_doc_content.lower()

    def test_list_tables_endpoint(self, api_doc_content):
        """Verify List Tables endpoint is documented."""
        assert "GET /v1/public/database/tables" in api_doc_content
        assert "List Tables" in api_doc_content or "list tables" in api_doc_content.lower()

    def test_get_table_endpoint(self, api_doc_content):
        """Verify Get Table Details endpoint is documented."""
        assert "GET /v1/public/database/tables/{table_id}" in api_doc_content
        assert "Get Table" in api_doc_content or "table details" in api_doc_content.lower()

    def test_delete_table_endpoint(self, api_doc_content):
        """Verify Delete Table endpoint is documented."""
        assert "DELETE /v1/public/database/tables/{table_id}" in api_doc_content
        assert "Delete Table" in api_doc_content or "delete table" in api_doc_content.lower()

    def test_insert_rows_endpoint(self, api_doc_content):
        """Verify Insert Rows endpoint is documented."""
        assert "POST /v1/public/database/tables/{table_id}/rows" in api_doc_content
        assert "Insert Rows" in api_doc_content or "insert rows" in api_doc_content.lower()

    def test_query_rows_endpoint(self, api_doc_content):
        """Verify Query Rows endpoint is documented."""
        assert "POST /v1/public/database/tables/{table_id}/query" in api_doc_content
        assert "Query Rows" in api_doc_content or "query rows" in api_doc_content.lower()

    def test_update_rows_endpoint(self, api_doc_content):
        """Verify Update Rows endpoint is documented."""
        assert "PATCH /v1/public/database/tables/{table_id}/rows" in api_doc_content
        assert "Update Rows" in api_doc_content or "update rows" in api_doc_content.lower()

    def test_delete_rows_endpoint(self, api_doc_content):
        """Verify Delete Rows endpoint is documented."""
        assert "DELETE /v1/public/database/tables/{table_id}/rows" in api_doc_content
        assert "Delete Rows" in api_doc_content or "delete rows" in api_doc_content.lower()

    def test_all_eight_endpoints_present(self, api_doc_content):
        """Verify all 8 endpoints are documented."""
        endpoints = [
            "POST /v1/public/database/tables",  # Create table
            "GET /v1/public/database/tables",   # List tables
            "GET /v1/public/database/tables/{table_id}",  # Get table
            "DELETE /v1/public/database/tables/{table_id}",  # Delete table
            "POST /v1/public/database/tables/{table_id}/rows",  # Insert rows
            "POST /v1/public/database/tables/{table_id}/query",  # Query rows
            "PATCH /v1/public/database/tables/{table_id}/rows",  # Update rows
            "DELETE /v1/public/database/tables/{table_id}/rows",  # Delete rows
        ]

        for endpoint in endpoints:
            assert endpoint in api_doc_content, f"Missing endpoint: {endpoint}"


class TestRowDataWarningPatterns:
    """Test that ROW_DATA_WARNING.md contains WRONG and RIGHT patterns."""

    @pytest.fixture
    def warning_doc_content(self):
        """Load ROW_DATA_WARNING.md content."""
        warning_doc = os.path.join(DOCS_BASE, "api", "ROW_DATA_WARNING.md")
        with open(warning_doc, 'r', encoding='utf-8') as f:
            return f.read()

    def test_wrong_pattern_section_exists(self, warning_doc_content):
        """Verify WRONG patterns section exists."""
        # Check for section headers
        assert "WRONG" in warning_doc_content.upper()
        assert re.search(r'(WRONG|Wrong)\s+(Pattern|Patterns)', warning_doc_content)

    def test_right_pattern_section_exists(self, warning_doc_content):
        """Verify RIGHT patterns section exists."""
        # Check for section headers
        assert "RIGHT" in warning_doc_content.upper() or "CORRECT" in warning_doc_content.upper()
        assert re.search(r'(RIGHT|CORRECT|Correct)\s+(Pattern|Patterns)', warning_doc_content)

    def test_wrong_rows_pattern(self, warning_doc_content):
        """Verify WRONG pattern for 'rows' field is documented."""
        # Should show { "rows": [...] } as WRONG
        assert '"rows"' in warning_doc_content
        # Should be in a WRONG context
        pattern = r'(WRONG|Wrong|wrong).*"rows"'
        assert re.search(pattern, warning_doc_content, re.DOTALL)

    def test_wrong_data_pattern(self, warning_doc_content):
        """Verify WRONG pattern for 'data' field is documented."""
        # Should show { "data": [...] } as WRONG
        assert '"data"' in warning_doc_content
        # Should be in a WRONG context
        pattern = r'(WRONG|Wrong|wrong).*"data"'
        assert re.search(pattern, warning_doc_content, re.DOTALL)

    def test_wrong_items_pattern(self, warning_doc_content):
        """Verify WRONG pattern for 'items' field is documented."""
        # Should show { "items": [...] } as WRONG
        assert '"items"' in warning_doc_content
        # Should be in a WRONG context
        pattern = r'(WRONG|Wrong|wrong).*"items"'
        assert re.search(pattern, warning_doc_content, re.DOTALL)

    def test_wrong_records_pattern(self, warning_doc_content):
        """Verify WRONG pattern for 'records' field is documented."""
        # Should show { "records": [...] } as WRONG (optional but recommended)
        if '"records"' in warning_doc_content:
            pattern = r'(WRONG|Wrong|wrong).*"records"'
            assert re.search(pattern, warning_doc_content, re.DOTALL)

    def test_correct_row_data_pattern(self, warning_doc_content):
        """Verify CORRECT pattern for 'row_data' field is documented."""
        # Should show { "row_data": [...] } as CORRECT/RIGHT
        assert '"row_data"' in warning_doc_content or 'row_data' in warning_doc_content
        # Should be in a CORRECT/RIGHT context
        pattern = r'(RIGHT|CORRECT|Correct|correct).*row_data'
        assert re.search(pattern, warning_doc_content, re.DOTALL | re.IGNORECASE)

    def test_wrong_patterns_with_code_blocks(self, warning_doc_content):
        """Verify WRONG patterns are shown in code blocks."""
        # Check for JSON code blocks with WRONG patterns
        code_block_pattern = r'```json\s*//\s*WRONG.*?"(rows|data|items)"'
        matches = re.findall(code_block_pattern, warning_doc_content, re.DOTALL)
        assert len(matches) > 0, "No WRONG patterns found in JSON code blocks"

    def test_correct_patterns_with_code_blocks(self, warning_doc_content):
        """Verify CORRECT patterns are shown in code blocks."""
        # Check for JSON code blocks with CORRECT patterns
        code_block_pattern = r'```json\s*//\s*(CORRECT|RIGHT).*?row_data'
        matches = re.findall(code_block_pattern, warning_doc_content, re.DOTALL | re.IGNORECASE)
        assert len(matches) > 0, "No CORRECT patterns found in JSON code blocks"


class TestProhibitedFieldWarnings:
    """Test that warnings about prohibited field names are present."""

    @pytest.fixture
    def all_docs_content(self):
        """Load all documentation files."""
        docs = {}

        api_doc = os.path.join(DOCS_BASE, "api", "TABLES_API.md")
        with open(api_doc, 'r', encoding='utf-8') as f:
            docs['api'] = f.read()

        warning_doc = os.path.join(DOCS_BASE, "api", "ROW_DATA_WARNING.md")
        with open(warning_doc, 'r', encoding='utf-8') as f:
            docs['warning'] = f.read()

        quick_start = os.path.join(DOCS_BASE, "quick-reference", "TABLES_QUICK_START.md")
        with open(quick_start, 'r', encoding='utf-8') as f:
            docs['quick_start'] = f.read()

        return docs

    def test_api_doc_warns_about_data_field(self, all_docs_content):
        """Verify TABLES_API.md warns against 'data' field."""
        content = all_docs_content['api']
        assert '"data"' in content
        # Should be mentioned in a negative context (WRONG, NOT, etc.)
        assert re.search(r'(WRONG|NOT|wrong|not).*"data"', content, re.DOTALL)

    def test_api_doc_warns_about_rows_field(self, all_docs_content):
        """Verify TABLES_API.md warns against 'rows' field."""
        content = all_docs_content['api']
        assert '"rows"' in content
        # Should be mentioned in a negative context
        assert re.search(r'(WRONG|NOT|wrong|not).*"rows"', content, re.DOTALL)

    def test_api_doc_warns_about_items_field(self, all_docs_content):
        """Verify TABLES_API.md warns against 'items' field."""
        content = all_docs_content['api']
        assert '"items"' in content
        # Should be mentioned in a negative context
        assert re.search(r'(WRONG|NOT|wrong|not).*"items"', content, re.DOTALL)

    def test_warning_doc_emphasizes_prohibition(self, all_docs_content):
        """Verify ROW_DATA_WARNING.md strongly emphasizes field name prohibition."""
        content = all_docs_content['warning']

        # Should have strong emphasis
        emphasis_patterns = [
            r'MUST',
            r'CRITICAL',
            r'MANDATORY',
            r'REQUIRED',
            r'NOT.*data.*rows.*items',
        ]

        matches = sum(1 for pattern in emphasis_patterns if re.search(pattern, content, re.IGNORECASE))
        assert matches >= 2, "Warning document lacks sufficient emphasis on field name requirement"

    def test_quick_start_mentions_row_data_requirement(self, all_docs_content):
        """Verify TABLES_QUICK_START.md mentions row_data requirement."""
        content = all_docs_content['quick_start']
        assert 'row_data' in content
        # Should mention using it correctly
        assert re.search(r'(use|Use|USE).*row_data', content)

    def test_quick_start_warns_common_mistakes(self, all_docs_content):
        """Verify TABLES_QUICK_START.md warns about common mistakes."""
        content = all_docs_content['quick_start']
        # Should have a section about mistakes or common errors
        assert re.search(r'(mistake|error|wrong|common|avoid)', content, re.IGNORECASE)


class TestProhibitedTerms:
    """Test that no prohibited terms appear in documentation."""

    @pytest.fixture
    def all_docs_content(self):
        """Load all documentation files."""
        docs = {}

        api_doc = os.path.join(DOCS_BASE, "api", "TABLES_API.md")
        with open(api_doc, 'r', encoding='utf-8') as f:
            docs['TABLES_API.md'] = f.read()

        warning_doc = os.path.join(DOCS_BASE, "api", "ROW_DATA_WARNING.md")
        with open(warning_doc, 'r', encoding='utf-8') as f:
            docs['ROW_DATA_WARNING.md'] = f.read()

        quick_start = os.path.join(DOCS_BASE, "quick-reference", "TABLES_QUICK_START.md")
        with open(quick_start, 'r', encoding='utf-8') as f:
            docs['TABLES_QUICK_START.md'] = f.read()

        return docs

    def test_no_claude_references(self, all_docs_content):
        """Verify no 'Claude' references in documentation."""
        prohibited_patterns = [
            r'\bClaude\b',
            r'\bclaude\b',
        ]

        for doc_name, content in all_docs_content.items():
            for pattern in prohibited_patterns:
                matches = re.findall(pattern, content)
                assert len(matches) == 0, f"Found 'Claude' reference in {doc_name}: {matches}"

    def test_no_anthropic_references(self, all_docs_content):
        """Verify no 'Anthropic' references in documentation."""
        prohibited_patterns = [
            r'\bAnthropic\b',
            r'\banthropic\b',
        ]

        for doc_name, content in all_docs_content.items():
            for pattern in prohibited_patterns:
                matches = re.findall(pattern, content)
                assert len(matches) == 0, f"Found 'Anthropic' reference in {doc_name}: {matches}"

    def test_no_chatgpt_references(self, all_docs_content):
        """Verify no 'ChatGPT' references in documentation."""
        prohibited_patterns = [
            r'\bChatGPT\b',
            r'\bchatGPT\b',
            r'\bchatgpt\b',
            r'\bChat-GPT\b',
        ]

        for doc_name, content in all_docs_content.items():
            for pattern in prohibited_patterns:
                matches = re.findall(pattern, content)
                assert len(matches) == 0, f"Found 'ChatGPT' reference in {doc_name}: {matches}"

    def test_no_copilot_references(self, all_docs_content):
        """Verify no 'Copilot' references in documentation."""
        prohibited_patterns = [
            r'\bCopilot\b',
            r'\bcopilot\b',
            r'\bCo-pilot\b',
        ]

        for doc_name, content in all_docs_content.items():
            for pattern in prohibited_patterns:
                matches = re.findall(pattern, content)
                assert len(matches) == 0, f"Found 'Copilot' reference in {doc_name}: {matches}"

    def test_combined_prohibited_terms_scan(self, all_docs_content):
        """Comprehensive scan for all prohibited terms."""
        prohibited_terms = [
            'Claude', 'claude',
            'Anthropic', 'anthropic',
            'ChatGPT', 'chatGPT', 'chatgpt',
            'Copilot', 'copilot', 'Co-pilot',
        ]

        for doc_name, content in all_docs_content.items():
            for term in prohibited_terms:
                # Use word boundary to avoid false positives
                if re.search(rf'\b{term}\b', content):
                    pytest.fail(f"Prohibited term '{term}' found in {doc_name}")


class TestDocumentationCompleteness:
    """Test overall documentation completeness and quality."""

    @pytest.fixture
    def api_doc_content(self):
        """Load TABLES_API.md content."""
        api_doc = os.path.join(DOCS_BASE, "api", "TABLES_API.md")
        with open(api_doc, 'r', encoding='utf-8') as f:
            return f.read()

    def test_api_doc_has_overview(self, api_doc_content):
        """Verify TABLES_API.md has an overview section."""
        assert re.search(r'##\s*Overview', api_doc_content, re.IGNORECASE)

    def test_api_doc_has_authentication(self, api_doc_content):
        """Verify TABLES_API.md documents authentication."""
        assert re.search(r'##\s*Authentication', api_doc_content, re.IGNORECASE)
        assert 'X-API-Key' in api_doc_content

    def test_api_doc_has_error_codes(self, api_doc_content):
        """Verify TABLES_API.md documents error codes."""
        assert re.search(r'##\s*Error', api_doc_content, re.IGNORECASE)
        # Should have at least a few error codes
        assert 'error_code' in api_doc_content or 'ERROR_CODE' in api_doc_content

    def test_api_doc_has_examples(self, api_doc_content):
        """Verify TABLES_API.md has code examples."""
        # Should have curl examples
        assert 'curl' in api_doc_content.lower()
        # Should have JSON examples
        assert '```json' in api_doc_content

    def test_api_doc_has_field_types(self, api_doc_content):
        """Verify TABLES_API.md documents field types."""
        # Should document data types
        types = ['string', 'number', 'boolean', 'timestamp']
        found = sum(1 for t in types if t in api_doc_content)
        assert found >= 3, "Not enough field types documented"

    def test_api_doc_references_warning_doc(self, api_doc_content):
        """Verify TABLES_API.md references ROW_DATA_WARNING.md."""
        assert 'ROW_DATA_WARNING' in api_doc_content

    def test_warning_doc_has_language_examples(self):
        """Verify ROW_DATA_WARNING.md has language-specific examples."""
        warning_doc = os.path.join(DOCS_BASE, "api", "ROW_DATA_WARNING.md")
        with open(warning_doc, 'r', encoding='utf-8') as f:
            content = f.read()

        # Should have examples in multiple languages
        languages = ['python', 'javascript', 'curl', 'go']
        found = sum(1 for lang in languages if lang.lower() in content.lower())
        assert found >= 2, "Not enough language examples in ROW_DATA_WARNING.md"

    def test_quick_start_is_concise(self):
        """Verify TABLES_QUICK_START.md is concise (not overly long)."""
        quick_start = os.path.join(DOCS_BASE, "quick-reference", "TABLES_QUICK_START.md")
        with open(quick_start, 'r', encoding='utf-8') as f:
            content = f.read()

        # Quick start should be reasonably short (< 500 lines)
        line_count = len(content.split('\n'))
        assert line_count < 500, f"Quick start guide is too long ({line_count} lines)"

    def test_all_docs_have_timestamps(self):
        """Verify all documentation has last updated timestamps."""
        docs = {
            'TABLES_API.md': os.path.join(DOCS_BASE, "api", "TABLES_API.md"),
            'ROW_DATA_WARNING.md': os.path.join(DOCS_BASE, "api", "ROW_DATA_WARNING.md"),
        }

        for doc_name, doc_path in docs.items():
            with open(doc_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Should have a last updated field
            has_timestamp = (
                re.search(r'Last Updated.*202\d', content, re.IGNORECASE) or
                re.search(r'Date.*202\d', content, re.IGNORECASE) or
                re.search(r'Version.*202\d', content, re.IGNORECASE)
            )
            assert has_timestamp, f"{doc_name} missing last updated timestamp"


class TestCrossReferenceLinks:
    """Test that cross-reference links between documents are correct."""

    @pytest.fixture
    def all_docs_content(self):
        """Load all documentation files."""
        docs = {}

        api_doc = os.path.join(DOCS_BASE, "api", "TABLES_API.md")
        with open(api_doc, 'r', encoding='utf-8') as f:
            docs['api'] = f.read()

        warning_doc = os.path.join(DOCS_BASE, "api", "ROW_DATA_WARNING.md")
        with open(warning_doc, 'r', encoding='utf-8') as f:
            docs['warning'] = f.read()

        quick_start = os.path.join(DOCS_BASE, "quick-reference", "TABLES_QUICK_START.md")
        with open(quick_start, 'r', encoding='utf-8') as f:
            docs['quick_start'] = f.read()

        return docs

    def test_api_doc_links_to_warning(self, all_docs_content):
        """Verify TABLES_API.md links to ROW_DATA_WARNING.md."""
        content = all_docs_content['api']
        assert 'ROW_DATA_WARNING.md' in content

    def test_api_doc_links_to_quick_start(self, all_docs_content):
        """Verify TABLES_API.md links to TABLES_QUICK_START.md."""
        content = all_docs_content['api']
        assert 'TABLES_QUICK_START.md' in content

    def test_warning_doc_links_to_api(self, all_docs_content):
        """Verify ROW_DATA_WARNING.md links to TABLES_API.md."""
        content = all_docs_content['warning']
        assert 'TABLES_API.md' in content

    def test_quick_start_links_to_api(self, all_docs_content):
        """Verify TABLES_QUICK_START.md links to TABLES_API.md."""
        content = all_docs_content['quick_start']
        assert 'TABLES_API.md' in content
