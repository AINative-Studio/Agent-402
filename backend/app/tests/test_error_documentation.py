"""
Error Documentation Validation Tests (Epic 9, Issue 45)

This test suite validates that all required error documentation is present,
properly formatted, and contains comprehensive troubleshooting guidance.

Tests verify:
1. Documentation files exist and are readable
2. All 10 required error codes are documented
3. Each error has example JSON response
4. Each error has "How to fix" section
5. HTTP status codes are documented for each error
6. Documentation follows DX contract compliance
7. Quick reference guide provides actionable fixes
"""

import os
import re
import json
from pathlib import Path
import pytest


# Project root is 2 levels up from backend/app/tests/
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.absolute()

# Required error codes as per Issue 45
REQUIRED_ERROR_CODES = [
    "INVALID_API_KEY",
    "VALIDATION_ERROR",
    "MODEL_NOT_FOUND",
    "PROJECT_NOT_FOUND",
    "DIMENSION_MISMATCH",
    "INVALID_NAMESPACE",
    "INVALID_METADATA_FILTER",
    "PATH_NOT_FOUND",
    "PROJECT_LIMIT_EXCEEDED",
    "INVALID_TIER"
]

# Expected HTTP status codes for each error
EXPECTED_HTTP_CODES = {
    "INVALID_API_KEY": 401,
    "VALIDATION_ERROR": 422,
    "MODEL_NOT_FOUND": 404,
    "PROJECT_NOT_FOUND": 404,
    "DIMENSION_MISMATCH": 422,
    "INVALID_NAMESPACE": 422,
    "INVALID_METADATA_FILTER": 422,
    "PATH_NOT_FOUND": 404,
    "PROJECT_LIMIT_EXCEEDED": 429,
    "INVALID_TIER": 422
}


class TestErrorCodeReferenceDoc:
    """Test suite for ERROR_CODES_REFERENCE.md validation."""

    @pytest.fixture
    def doc_path(self):
        """Get path to ERROR_CODES_REFERENCE.md."""
        return PROJECT_ROOT / "docs" / "api" / "ERROR_CODES_REFERENCE.md"

    @pytest.fixture
    def doc_content(self, doc_path):
        """Read ERROR_CODES_REFERENCE.md content."""
        assert doc_path.exists(), f"ERROR_CODES_REFERENCE.md not found at {doc_path}"
        with open(doc_path, 'r', encoding='utf-8') as f:
            return f.read()

    def test_doc_exists(self, doc_path):
        """Verify ERROR_CODES_REFERENCE.md exists."""
        assert doc_path.exists(), f"ERROR_CODES_REFERENCE.md not found at {doc_path}"
        assert doc_path.is_file(), f"ERROR_CODES_REFERENCE.md is not a file: {doc_path}"

    def test_doc_readable(self, doc_path):
        """Verify ERROR_CODES_REFERENCE.md is readable."""
        try:
            with open(doc_path, 'r', encoding='utf-8') as f:
                content = f.read()
            assert len(content) > 0, "ERROR_CODES_REFERENCE.md is empty"
        except Exception as e:
            pytest.fail(f"Failed to read ERROR_CODES_REFERENCE.md: {e}")

    def test_doc_has_metadata(self, doc_content):
        """Verify document has version and metadata."""
        assert "Version:" in doc_content, "Missing version information"
        assert "Last Updated:" in doc_content, "Missing last updated date"
        assert "Epic:" in doc_content or "Issue:" in doc_content, "Missing epic/issue reference"

    def test_dx_contract_compliance(self, doc_content):
        """Verify document mentions DX contract compliance."""
        assert "DX Contract" in doc_content or "error_code" in doc_content, \
            "Missing DX Contract compliance section"
        assert '"error_code"' in doc_content, "Missing error_code field in examples"
        assert '"detail"' in doc_content, "Missing detail field in examples"

    def test_all_error_codes_documented(self, doc_content):
        """Verify all 10 required error codes are documented."""
        for error_code in REQUIRED_ERROR_CODES:
            assert error_code in doc_content, \
                f"Error code '{error_code}' not found in ERROR_CODES_REFERENCE.md"

    def test_error_codes_have_headings(self, doc_content):
        """Verify each error code has a proper heading."""
        for error_code in REQUIRED_ERROR_CODES:
            # Look for heading like "## 1. INVALID_API_KEY (401)"
            pattern = rf"##\s+\d+\.\s+{error_code}\s+\(\d+\)"
            assert re.search(pattern, doc_content), \
                f"Error code '{error_code}' missing proper heading with HTTP code"

    def test_http_status_codes_documented(self, doc_content):
        """Verify HTTP status codes are documented for each error."""
        for error_code, expected_status in EXPECTED_HTTP_CODES.items():
            # Look for the error code with its HTTP status in heading
            pattern = rf"{error_code}\s+\({expected_status}\)"
            assert re.search(pattern, doc_content), \
                f"Error code '{error_code}' missing HTTP status code {expected_status}"

    def test_example_json_responses(self, doc_content):
        """Verify each error has example JSON response."""
        for error_code in REQUIRED_ERROR_CODES:
            # Check for JSON code block after the error heading
            section_pattern = rf"##.*{error_code}.*?(?=##|\Z)"
            section_match = re.search(section_pattern, doc_content, re.DOTALL)

            assert section_match, f"Could not find section for {error_code}"
            section_content = section_match.group(0)

            # Verify JSON code block exists
            assert "```json" in section_content, \
                f"Error code '{error_code}' missing JSON example"

            # Verify example contains error_code field
            assert f'"error_code": "{error_code}"' in section_content, \
                f"JSON example for '{error_code}' missing error_code field"

    def test_how_to_fix_sections(self, doc_content):
        """Verify each error has 'How to fix' section."""
        for error_code in REQUIRED_ERROR_CODES:
            # Get the section for this error
            section_pattern = rf"##.*{error_code}.*?(?=##|\Z)"
            section_match = re.search(section_pattern, doc_content, re.DOTALL)

            assert section_match, f"Could not find section for {error_code}"
            section_content = section_match.group(0)

            # Verify "How to fix" heading exists
            assert re.search(r"###\s+How to fix", section_content), \
                f"Error code '{error_code}' missing 'How to fix' section"

    def test_when_it_occurs_sections(self, doc_content):
        """Verify each error has 'When it occurs' section."""
        for error_code in REQUIRED_ERROR_CODES:
            section_pattern = rf"##.*{error_code}.*?(?=##|\Z)"
            section_match = re.search(section_pattern, doc_content, re.DOTALL)

            assert section_match, f"Could not find section for {error_code}"
            section_content = section_match.group(0)

            assert re.search(r"###\s+When it occurs", section_content), \
                f"Error code '{error_code}' missing 'When it occurs' section"

    def test_example_response_sections(self, doc_content):
        """Verify each error has 'Example Response' section."""
        for error_code in REQUIRED_ERROR_CODES:
            section_pattern = rf"##.*{error_code}.*?(?=##|\Z)"
            section_match = re.search(section_pattern, doc_content, re.DOTALL)

            assert section_match, f"Could not find section for {error_code}"
            section_content = section_match.group(0)

            assert re.search(r"###\s+Example Response", section_content), \
                f"Error code '{error_code}' missing 'Example Response' section"

    def test_json_response_format(self, doc_content):
        """Verify JSON responses follow DX contract format."""
        # Extract all JSON code blocks
        json_blocks = re.findall(r"```json\n(.*?)```", doc_content, re.DOTALL)

        assert len(json_blocks) >= 10, "Expected at least 10 JSON examples (one per error)"

        # Verify at least 10 JSON blocks have both detail and error_code fields
        valid_responses = 0
        for json_block in json_blocks:
            if '"detail"' in json_block and '"error_code"' in json_block:
                valid_responses += 1

        assert valid_responses >= 10, \
            f"Expected at least 10 JSON responses with detail and error_code fields, found {valid_responses}"

    def test_quick_reference_table(self, doc_content):
        """Verify document includes quick reference table."""
        assert "Quick Reference Table" in doc_content or "## Quick Reference" in doc_content, \
            "Missing quick reference table"

        # Verify table includes all error codes
        table_section = doc_content[doc_content.find("Quick Reference"):]
        for error_code in REQUIRED_ERROR_CODES:
            assert error_code in table_section, \
                f"Error code '{error_code}' missing from quick reference table"

    def test_table_of_contents(self, doc_content):
        """Verify document has table of contents."""
        assert "Table of Contents" in doc_content or "## Table of Contents" in doc_content, \
            "Missing table of contents"


class TestCommonErrorsFixesDoc:
    """Test suite for COMMON_ERRORS_FIXES.md validation."""

    @pytest.fixture
    def doc_path(self):
        """Get path to COMMON_ERRORS_FIXES.md."""
        return PROJECT_ROOT / "docs" / "quick-reference" / "COMMON_ERRORS_FIXES.md"

    @pytest.fixture
    def doc_content(self, doc_path):
        """Read COMMON_ERRORS_FIXES.md content."""
        assert doc_path.exists(), f"COMMON_ERRORS_FIXES.md not found at {doc_path}"
        with open(doc_path, 'r', encoding='utf-8') as f:
            return f.read()

    def test_doc_exists(self, doc_path):
        """Verify COMMON_ERRORS_FIXES.md exists."""
        assert doc_path.exists(), f"COMMON_ERRORS_FIXES.md not found at {doc_path}"
        assert doc_path.is_file(), f"COMMON_ERRORS_FIXES.md is not a file: {doc_path}"

    def test_doc_readable(self, doc_path):
        """Verify COMMON_ERRORS_FIXES.md is readable."""
        try:
            with open(doc_path, 'r', encoding='utf-8') as f:
                content = f.read()
            assert len(content) > 0, "COMMON_ERRORS_FIXES.md is empty"
        except Exception as e:
            pytest.fail(f"Failed to read COMMON_ERRORS_FIXES.md: {e}")

    def test_doc_has_metadata(self, doc_content):
        """Verify document has version and metadata."""
        assert "Version:" in doc_content or "v1.0" in doc_content, "Missing version information"
        assert "Issue:" in doc_content or "#45" in doc_content, "Missing issue reference"

    def test_all_error_codes_documented(self, doc_content):
        """Verify all 10 required error codes are in quick reference."""
        for error_code in REQUIRED_ERROR_CODES:
            assert error_code in doc_content, \
                f"Error code '{error_code}' not found in COMMON_ERRORS_FIXES.md"

    def test_error_codes_have_sections(self, doc_content):
        """Verify each error code has its own section."""
        for error_code in REQUIRED_ERROR_CODES:
            # Look for heading with error code
            pattern = rf"##\s+\d+\.\s+{error_code}"
            assert re.search(pattern, doc_content), \
                f"Error code '{error_code}' missing section heading in quick reference"

    def test_http_codes_in_sections(self, doc_content):
        """Verify HTTP status codes are mentioned in quick reference."""
        for error_code, expected_status in EXPECTED_HTTP_CODES.items():
            # Find the section for this error
            section_pattern = rf"##.*{error_code}.*?(?=##|\Z)"
            section_match = re.search(section_pattern, doc_content, re.DOTALL)

            assert section_match, f"Could not find section for {error_code}"
            section_content = section_match.group(0)

            # Verify HTTP status code is mentioned
            assert str(expected_status) in section_content, \
                f"HTTP status {expected_status} not found in section for {error_code}"

    def test_quick_fix_sections(self, doc_content):
        """Verify each error has quick fix guidance."""
        quick_fix_keywords = ["Quick Fix", "Fix:", "How to", "Solution"]

        for error_code in REQUIRED_ERROR_CODES:
            section_pattern = rf"##.*{error_code}.*?(?=##|\Z)"
            section_match = re.search(section_pattern, doc_content, re.DOTALL)

            assert section_match, f"Could not find section for {error_code}"
            section_content = section_match.group(0)

            # Verify at least one quick fix keyword is present
            has_fix_guidance = any(keyword in section_content for keyword in quick_fix_keywords)
            assert has_fix_guidance, \
                f"Error code '{error_code}' missing quick fix guidance in quick reference"

    def test_code_examples(self, doc_content):
        """Verify quick reference includes code examples."""
        # Count code blocks
        code_blocks = re.findall(r"```\w*\n", doc_content)
        assert len(code_blocks) >= 10, \
            f"Expected at least 10 code examples in quick reference, found {len(code_blocks)}"

    def test_quick_reference_table(self, doc_content):
        """Verify document includes error quick reference table."""
        # Look for table with error codes and HTTP codes
        for error_code in REQUIRED_ERROR_CODES:
            # Check if error code appears in a table format (with pipes)
            table_pattern = rf"\|.*{error_code}.*\|"
            assert re.search(table_pattern, doc_content), \
                f"Error code '{error_code}' not found in quick reference table"

    def test_30_second_fixes(self, doc_content):
        """Verify quick reference provides fast solutions."""
        # The quick reference should be concise - check for brevity indicators
        assert "30-Second" in doc_content or "Quick Fix" in doc_content or "Quick Reference" in doc_content, \
            "Missing quick/30-second fix indicators"

    def test_copy_paste_examples(self, doc_content):
        """Verify document includes copy-paste ready examples."""
        # Look for bash/curl examples that can be copy-pasted
        assert "curl" in doc_content or "bash" in doc_content, \
            "Missing copy-paste ready curl/bash examples"

        # Check for environment variable usage (makes examples more copy-paste friendly)
        assert "${" in doc_content or "$BASE_URL" in doc_content or "$API_KEY" in doc_content, \
            "Missing environment variable usage in examples"

    def test_debugging_checklist(self, doc_content):
        """Verify document includes debugging checklist."""
        # Look for checklist items
        checklist_pattern = r"- \[ \]"
        checklist_matches = re.findall(checklist_pattern, doc_content)

        assert len(checklist_matches) >= 5, \
            f"Expected at least 5 checklist items, found {len(checklist_matches)}"

    def test_templates_section(self, doc_content):
        """Verify document includes copy-paste templates."""
        # Look for templates or examples section
        assert "Template" in doc_content or "Example" in doc_content, \
            "Missing templates or examples section"


class TestErrorDocumentationCrossReference:
    """Test cross-references between error documentation files."""

    @pytest.fixture
    def reference_doc_path(self):
        """Get path to ERROR_CODES_REFERENCE.md."""
        return PROJECT_ROOT / "docs" / "api" / "ERROR_CODES_REFERENCE.md"

    @pytest.fixture
    def quick_doc_path(self):
        """Get path to COMMON_ERRORS_FIXES.md."""
        return PROJECT_ROOT / "docs" / "quick-reference" / "COMMON_ERRORS_FIXES.md"

    @pytest.fixture
    def reference_content(self, reference_doc_path):
        """Read ERROR_CODES_REFERENCE.md content."""
        with open(reference_doc_path, 'r', encoding='utf-8') as f:
            return f.read()

    @pytest.fixture
    def quick_content(self, quick_doc_path):
        """Read COMMON_ERRORS_FIXES.md content."""
        with open(quick_doc_path, 'r', encoding='utf-8') as f:
            return f.read()

    def test_reference_doc_links_to_quick_guide(self, reference_content):
        """Verify ERROR_CODES_REFERENCE.md links to quick guide."""
        assert "COMMON_ERRORS_FIXES.md" in reference_content or \
               "Quick Troubleshooting" in reference_content or \
               "quick-reference" in reference_content, \
            "ERROR_CODES_REFERENCE.md should link to COMMON_ERRORS_FIXES.md"

    def test_quick_guide_links_to_reference(self, quick_content):
        """Verify COMMON_ERRORS_FIXES.md links to full reference."""
        assert "ERROR_CODES_REFERENCE.md" in quick_content or \
               "Full Error Reference" in quick_content or \
               "api/ERROR" in quick_content, \
            "COMMON_ERRORS_FIXES.md should link to ERROR_CODES_REFERENCE.md"

    def test_http_codes_match(self, reference_content, quick_content):
        """Verify HTTP codes are consistent across both documents."""
        for error_code, expected_status in EXPECTED_HTTP_CODES.items():
            # Both documents should mention the error with its HTTP status
            ref_has_status = re.search(rf"{error_code}.*\({expected_status}\)", reference_content)
            quick_has_status = str(expected_status) in quick_content

            assert ref_has_status, \
                f"ERROR_CODES_REFERENCE.md missing HTTP {expected_status} for {error_code}"
            assert quick_has_status, \
                f"COMMON_ERRORS_FIXES.md missing HTTP {expected_status} for {error_code}"


class TestErrorDocumentationCompleteness:
    """Test overall completeness and quality of error documentation."""

    @pytest.fixture
    def reference_doc_path(self):
        """Get path to ERROR_CODES_REFERENCE.md."""
        return PROJECT_ROOT / "docs" / "api" / "ERROR_CODES_REFERENCE.md"

    @pytest.fixture
    def reference_content(self, reference_doc_path):
        """Read ERROR_CODES_REFERENCE.md content."""
        with open(reference_doc_path, 'r', encoding='utf-8') as f:
            return f.read()

    def test_comprehensive_coverage(self, reference_content):
        """Verify comprehensive coverage of all required elements."""
        # Each error should have all three key sections
        for error_code in REQUIRED_ERROR_CODES:
            section_pattern = rf"##.*{error_code}.*?(?=##|\Z)"
            section_match = re.search(section_pattern, reference_content, re.DOTALL)

            assert section_match, f"Missing section for {error_code}"
            section_content = section_match.group(0)

            # Must have all three sections
            assert "When it occurs" in section_content, \
                f"{error_code} missing 'When it occurs' section"
            assert "Example Response" in section_content, \
                f"{error_code} missing 'Example Response' section"
            assert "How to fix" in section_content, \
                f"{error_code} missing 'How to fix' section"

    def test_sufficient_detail(self, reference_content):
        """Verify each error section has sufficient detail."""
        for error_code in REQUIRED_ERROR_CODES:
            section_pattern = rf"##.*{error_code}.*?(?=##|\Z)"
            section_match = re.search(section_pattern, reference_content, re.DOTALL)

            assert section_match, f"Missing section for {error_code}"
            section_content = section_match.group(0)

            # Each section should be substantial (at least 500 chars)
            assert len(section_content) >= 500, \
                f"{error_code} section too short - needs more detail (has {len(section_content)} chars)"

    def test_actionable_fixes(self, reference_content):
        """Verify fixes include actionable code examples."""
        for error_code in REQUIRED_ERROR_CODES:
            section_pattern = rf"##.*{error_code}.*?(?=##|\Z)"
            section_match = re.search(section_pattern, reference_content, re.DOTALL)

            assert section_match, f"Missing section for {error_code}"
            section_content = section_match.group(0)

            # How to fix section should have code examples
            fix_section = re.search(r"###\s+How to fix.*?(?=###|\Z)", section_content, re.DOTALL)
            if fix_section:
                fix_content = fix_section.group(0)
                assert "```" in fix_content, \
                    f"{error_code} 'How to fix' section missing code examples"

    def test_no_broken_markdown_links(self, reference_content):
        """Verify markdown links are properly formatted."""
        # Find all markdown links
        link_pattern = r'\[([^\]]+)\]\(([^\)]+)\)'
        links = re.findall(link_pattern, reference_content)

        for link_text, link_url in links:
            # Verify links are not empty
            assert link_url.strip(), f"Empty link URL for '{link_text}'"
            # Verify internal links use proper paths
            if link_url.startswith('/docs/'):
                assert not link_url.endswith('/'), \
                    f"Internal link should not end with slash: {link_url}"

    def test_consistent_formatting(self, reference_content):
        """Verify consistent markdown formatting."""
        # All error headings should follow same pattern
        error_headings = re.findall(r"##\s+\d+\.\s+\w+\s+\(\d+\)", reference_content)

        assert len(error_headings) == 10, \
            f"Expected 10 error headings, found {len(error_headings)}"

        # All should be numbered 1-10
        for i in range(1, 11):
            pattern = rf"##\s+{i}\."
            assert re.search(pattern, reference_content), \
                f"Missing heading number {i}"


class TestIssue45Acceptance:
    """Acceptance tests for Issue 45 completion criteria."""

    def test_issue_45_all_files_exist(self):
        """Verify all required documentation files exist."""
        reference_doc = PROJECT_ROOT / "docs" / "api" / "ERROR_CODES_REFERENCE.md"
        quick_doc = PROJECT_ROOT / "docs" / "quick-reference" / "COMMON_ERRORS_FIXES.md"

        assert reference_doc.exists(), "ERROR_CODES_REFERENCE.md missing"
        assert quick_doc.exists(), "COMMON_ERRORS_FIXES.md missing"

    def test_issue_45_all_errors_covered(self):
        """Verify all 10 required errors are documented in both files."""
        reference_doc = PROJECT_ROOT / "docs" / "api" / "ERROR_CODES_REFERENCE.md"
        quick_doc = PROJECT_ROOT / "docs" / "quick-reference" / "COMMON_ERRORS_FIXES.md"

        with open(reference_doc, 'r', encoding='utf-8') as f:
            reference_content = f.read()
        with open(quick_doc, 'r', encoding='utf-8') as f:
            quick_content = f.read()

        for error_code in REQUIRED_ERROR_CODES:
            assert error_code in reference_content, \
                f"ERROR_CODES_REFERENCE.md missing {error_code}"
            assert error_code in quick_content, \
                f"COMMON_ERRORS_FIXES.md missing {error_code}"

    def test_issue_45_all_have_json_examples(self):
        """Verify all errors have JSON response examples."""
        reference_doc = PROJECT_ROOT / "docs" / "api" / "ERROR_CODES_REFERENCE.md"

        with open(reference_doc, 'r', encoding='utf-8') as f:
            content = f.read()

        for error_code in REQUIRED_ERROR_CODES:
            # Get error section
            section_pattern = rf"##.*{error_code}.*?(?=##|\Z)"
            section_match = re.search(section_pattern, content, re.DOTALL)

            assert section_match, f"Missing section for {error_code}"
            section_content = section_match.group(0)

            # Must have JSON example with error_code field
            assert "```json" in section_content, \
                f"{error_code} missing JSON example"
            assert f'"error_code": "{error_code}"' in section_content, \
                f"{error_code} JSON example missing error_code field"

    def test_issue_45_all_have_fixes(self):
        """Verify all errors have 'How to fix' sections."""
        reference_doc = PROJECT_ROOT / "docs" / "api" / "ERROR_CODES_REFERENCE.md"

        with open(reference_doc, 'r', encoding='utf-8') as f:
            content = f.read()

        for error_code in REQUIRED_ERROR_CODES:
            section_pattern = rf"##.*{error_code}.*?(?=##|\Z)"
            section_match = re.search(section_pattern, content, re.DOTALL)

            assert section_match, f"Missing section for {error_code}"
            section_content = section_match.group(0)

            assert re.search(r"###\s+How to fix", section_content), \
                f"{error_code} missing 'How to fix' section"

    def test_issue_45_all_have_http_codes(self):
        """Verify all errors have HTTP status codes documented."""
        reference_doc = PROJECT_ROOT / "docs" / "api" / "ERROR_CODES_REFERENCE.md"

        with open(reference_doc, 'r', encoding='utf-8') as f:
            content = f.read()

        for error_code, expected_status in EXPECTED_HTTP_CODES.items():
            pattern = rf"{error_code}\s+\({expected_status}\)"
            assert re.search(pattern, content), \
                f"{error_code} missing HTTP status code {expected_status} in heading"

    def test_issue_45_completion_summary(self):
        """Final acceptance test - verify Issue 45 is complete."""
        reference_doc = PROJECT_ROOT / "docs" / "api" / "ERROR_CODES_REFERENCE.md"
        quick_doc = PROJECT_ROOT / "docs" / "quick-reference" / "COMMON_ERRORS_FIXES.md"

        # All files exist
        assert reference_doc.exists() and quick_doc.exists(), \
            "Not all documentation files exist"

        with open(reference_doc, 'r', encoding='utf-8') as f:
            ref_content = f.read()
        with open(quick_doc, 'r', encoding='utf-8') as f:
            quick_content = f.read()

        # All 10 errors present in both
        for error_code in REQUIRED_ERROR_CODES:
            assert error_code in ref_content and error_code in quick_content, \
                f"Error code {error_code} not in both documents"

        # All have HTTP codes
        for error_code, status in EXPECTED_HTTP_CODES.items():
            assert str(status) in ref_content, \
                f"HTTP {status} for {error_code} not documented"

        # All have JSON examples
        json_examples = ref_content.count("```json")
        assert json_examples >= 10, \
            f"Expected at least 10 JSON examples, found {json_examples}"

        # All have How to fix sections
        fix_sections = len(re.findall(r"###\s+How to fix", ref_content))
        assert fix_sections >= 10, \
            f"Expected at least 10 'How to fix' sections, found {fix_sections}"

        print("\n" + "="*70)
        print("Issue 45 Acceptance Test: PASSED")
        print("="*70)
        print(f"✓ Both documentation files exist")
        print(f"✓ All 10 error codes documented")
        print(f"✓ All errors have JSON examples")
        print(f"✓ All errors have 'How to fix' sections")
        print(f"✓ All errors have HTTP status codes")
        print("="*70)
