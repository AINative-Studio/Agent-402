"""
Security Documentation Validation Tests (Epic 2, Issue 5)

This test suite validates that all required security documentation is present,
properly formatted, and contains the necessary security guidance for API key handling.

Tests verify:
1. Documentation files exist
2. Key security sections are present
3. Warning messages are prominent
4. Code examples show both WRONG and RIGHT patterns
5. No prohibited vendor-specific terms are used
"""

import os
import re
from pathlib import Path
import pytest


# Project root is 2 levels up from backend/app/tests/
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.absolute()


class TestSecurityDocumentation:
    """Test suite for API key security documentation validation."""

    def test_project_root_exists(self):
        """Verify project root directory exists."""
        assert PROJECT_ROOT.exists(), f"Project root not found: {PROJECT_ROOT}"
        assert PROJECT_ROOT.is_dir(), f"Project root is not a directory: {PROJECT_ROOT}"

    def test_api_key_security_doc_exists(self):
        """Verify comprehensive API key security guide exists."""
        doc_path = PROJECT_ROOT / "docs" / "api" / "API_KEY_SECURITY.md"
        assert doc_path.exists(), f"API_KEY_SECURITY.md not found at {doc_path}"
        assert doc_path.is_file(), f"API_KEY_SECURITY.md is not a file: {doc_path}"

    def test_api_key_safety_checklist_exists(self):
        """Verify quick reference checklist exists."""
        checklist_path = PROJECT_ROOT / "docs" / "quick-reference" / "API_KEY_SAFETY_CHECKLIST.md"
        assert checklist_path.exists(), f"API_KEY_SAFETY_CHECKLIST.md not found at {checklist_path}"
        assert checklist_path.is_file(), f"API_KEY_SAFETY_CHECKLIST.md is not a file: {checklist_path}"

    def test_backend_readme_security_warning(self):
        """Verify backend README contains security warning."""
        readme_path = PROJECT_ROOT / "backend" / "README.md"
        assert readme_path.exists(), f"Backend README.md not found at {readme_path}"

        with open(readme_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check for security warning section
        assert "SECURITY WARNING" in content or "CRITICAL" in content, \
            "Backend README must contain security warning"

        # Check for reference to security documentation
        assert "API_KEY_SECURITY.md" in content, \
            "Backend README must reference API_KEY_SECURITY.md"

    def test_api_key_security_has_warning_section(self):
        """Verify API_KEY_SECURITY.md has prominent warning section."""
        doc_path = PROJECT_ROOT / "docs" / "api" / "API_KEY_SECURITY.md"

        with open(doc_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check for warning section
        assert "## Critical Warning" in content or "## CRITICAL WARNING" in content, \
            "API_KEY_SECURITY.md must have Critical Warning section"

        # Check for warning about client-side exposure
        assert "WARNING" in content.upper(), \
            "API_KEY_SECURITY.md must contain WARNING text"

        assert "NEVER" in content.upper(), \
            "API_KEY_SECURITY.md must emphasize what should NEVER be done"

        # Check for specific client-side contexts mentioned
        client_contexts = ["browser", "mobile", "client-side", "frontend"]
        found_contexts = [ctx for ctx in client_contexts if ctx.lower() in content.lower()]
        assert len(found_contexts) >= 2, \
            f"API_KEY_SECURITY.md must mention multiple client contexts, found: {found_contexts}"

    def test_api_key_security_has_wrong_patterns(self):
        """Verify API_KEY_SECURITY.md documents WRONG patterns."""
        doc_path = PROJECT_ROOT / "docs" / "api" / "API_KEY_SECURITY.md"

        with open(doc_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check for section header
        assert "## Vulnerable Patterns" in content or "Vulnerable Patterns (WRONG)" in content, \
            "API_KEY_SECURITY.md must have Vulnerable Patterns section"

        # Check for "WRONG" markers
        wrong_count = content.count("WRONG")
        assert wrong_count >= 5, \
            f"API_KEY_SECURITY.md should show multiple WRONG patterns, found {wrong_count}"

        # Check for code examples
        code_block_count = content.count("```")
        assert code_block_count >= 10, \
            f"API_KEY_SECURITY.md should have multiple code examples, found {code_block_count // 2} blocks"

        # Check for specific vulnerable patterns
        vulnerable_patterns = [
            "hardcoded",
            "environment variable",
            "obfuscation",
            "base64",
            "frontend"
        ]
        found_patterns = [p for p in vulnerable_patterns if p.lower() in content.lower()]
        assert len(found_patterns) >= 4, \
            f"API_KEY_SECURITY.md must cover common vulnerable patterns, found: {found_patterns}"

    def test_api_key_security_has_right_patterns(self):
        """Verify API_KEY_SECURITY.md documents RIGHT patterns."""
        doc_path = PROJECT_ROOT / "docs" / "api" / "API_KEY_SECURITY.md"

        with open(doc_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check for section header
        assert "## Secure Backend Proxy Pattern" in content or "Backend Proxy Pattern (RIGHT)" in content, \
            "API_KEY_SECURITY.md must have Secure Backend Proxy Pattern section"

        # Check for "RIGHT" markers
        right_count = content.count("RIGHT")
        assert right_count >= 3, \
            f"API_KEY_SECURITY.md should show RIGHT patterns, found {right_count}"

        # Check for backend proxy architecture
        backend_terms = ["backend", "proxy", "server", "JWT"]
        found_terms = [t for t in backend_terms if t.lower() in content.lower()]
        assert len(found_terms) >= 3, \
            f"API_KEY_SECURITY.md must explain backend proxy architecture, found: {found_terms}"

        # Check for implementation examples
        assert "FastAPI" in content or "Express" in content or "backend" in content.lower(), \
            "API_KEY_SECURITY.md should include backend implementation examples"

    def test_api_key_security_has_incident_response(self):
        """Verify API_KEY_SECURITY.md includes incident response section."""
        doc_path = PROJECT_ROOT / "docs" / "api" / "API_KEY_SECURITY.md"

        with open(doc_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check for incident response section
        assert "## Incident Response" in content or "Incident Response" in content, \
            "API_KEY_SECURITY.md must have Incident Response section"

        # Check for key incident response steps
        response_terms = ["revoke", "compromise", "immediate", "generate"]
        found_terms = [t for t in response_terms if t.lower() in content.lower()]
        assert len(found_terms) >= 3, \
            f"API_KEY_SECURITY.md must include incident response procedures, found: {found_terms}"

    def test_api_key_security_has_security_checklist(self):
        """Verify API_KEY_SECURITY.md includes security checklist."""
        doc_path = PROJECT_ROOT / "docs" / "api" / "API_KEY_SECURITY.md"

        with open(doc_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check for checklist section
        assert "## Security Checklist" in content or "Security Checklist" in content, \
            "API_KEY_SECURITY.md must have Security Checklist section"

        # Check for checkbox items
        checkbox_count = content.count("- [ ]")
        assert checkbox_count >= 10, \
            f"Security Checklist should have multiple items, found {checkbox_count}"

    def test_checklist_has_wrong_patterns(self):
        """Verify API_KEY_SAFETY_CHECKLIST.md documents WRONG patterns."""
        checklist_path = PROJECT_ROOT / "docs" / "quick-reference" / "API_KEY_SAFETY_CHECKLIST.md"

        with open(checklist_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check for WRONG patterns section
        assert "WRONG" in content, \
            "API_KEY_SAFETY_CHECKLIST.md must include WRONG patterns"

        # Check for "Reject Immediately" or similar urgent language
        assert any(term in content for term in ["Reject", "CRITICAL", "NEVER"]), \
            "API_KEY_SAFETY_CHECKLIST.md must use urgent language for anti-patterns"

    def test_checklist_has_right_patterns(self):
        """Verify API_KEY_SAFETY_CHECKLIST.md documents RIGHT patterns."""
        checklist_path = PROJECT_ROOT / "docs" / "quick-reference" / "API_KEY_SAFETY_CHECKLIST.md"

        with open(checklist_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check for RIGHT patterns section
        assert "RIGHT" in content or "SECURE" in content, \
            "API_KEY_SAFETY_CHECKLIST.md must include RIGHT/SECURE patterns"

        # Check for approval/secure markers
        assert any(term in content for term in ["Approve", "SECURE", "Correct"]), \
            "API_KEY_SAFETY_CHECKLIST.md must mark secure patterns"

    def test_checklist_has_emergency_procedures(self):
        """Verify API_KEY_SAFETY_CHECKLIST.md includes emergency procedures."""
        checklist_path = PROJECT_ROOT / "docs" / "quick-reference" / "API_KEY_SAFETY_CHECKLIST.md"

        with open(checklist_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check for emergency section
        assert "Emergency" in content or "Compromised" in content, \
            "API_KEY_SAFETY_CHECKLIST.md must include emergency procedures"

        # Check for key emergency steps
        emergency_terms = ["revoke", "immediately", "generate"]
        found_terms = [t for t in emergency_terms if t.lower() in content.lower()]
        assert len(found_terms) >= 2, \
            f"API_KEY_SAFETY_CHECKLIST.md must include emergency steps, found: {found_terms}"

    def test_no_prohibited_terms_in_security_doc(self):
        """Verify API_KEY_SECURITY.md does not contain prohibited vendor-specific terms."""
        doc_path = PROJECT_ROOT / "docs" / "api" / "API_KEY_SECURITY.md"

        with open(doc_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Prohibited terms that should not appear in security documentation
        prohibited_terms = [
            "Claude",
            "Anthropic",
            "ChatGPT",
            "Copilot",
            "OpenAI API Key"  # Generic "API key" is fine, but not "OpenAI API Key"
        ]

        found_prohibited = []
        for term in prohibited_terms:
            # Case-insensitive search
            if re.search(r'\b' + re.escape(term) + r'\b', content, re.IGNORECASE):
                found_prohibited.append(term)

        assert len(found_prohibited) == 0, \
            f"API_KEY_SECURITY.md contains prohibited vendor-specific terms: {found_prohibited}"

    def test_no_prohibited_terms_in_checklist(self):
        """Verify API_KEY_SAFETY_CHECKLIST.md does not contain prohibited vendor-specific terms."""
        checklist_path = PROJECT_ROOT / "docs" / "quick-reference" / "API_KEY_SAFETY_CHECKLIST.md"

        with open(checklist_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Prohibited terms
        prohibited_terms = [
            "Claude",
            "Anthropic",
            "ChatGPT",
            "Copilot"
        ]

        found_prohibited = []
        for term in prohibited_terms:
            if re.search(r'\b' + re.escape(term) + r'\b', content, re.IGNORECASE):
                found_prohibited.append(term)

        assert len(found_prohibited) == 0, \
            f"API_KEY_SAFETY_CHECKLIST.md contains prohibited vendor-specific terms: {found_prohibited}"

    def test_documentation_links_are_valid(self):
        """Verify internal documentation links reference correct paths."""
        doc_path = PROJECT_ROOT / "docs" / "api" / "API_KEY_SECURITY.md"

        with open(doc_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract markdown links [text](/path)
        link_pattern = r'\[([^\]]+)\]\((/[^\)]+)\)'
        links = re.findall(link_pattern, content)

        # Check that referenced files exist
        for link_text, link_path in links:
            # Convert relative doc links to absolute paths
            if link_path.startswith('/docs/'):
                full_path = PROJECT_ROOT / link_path.lstrip('/')
            elif link_path.startswith('/'):
                full_path = PROJECT_ROOT / link_path.lstrip('/')
            else:
                continue  # Skip external links

            # Only check .md files
            if link_path.endswith('.md'):
                assert full_path.exists(), \
                    f"Broken link in API_KEY_SECURITY.md: '{link_text}' -> {link_path} (expected at {full_path})"

    def test_security_doc_has_table_of_contents(self):
        """Verify API_KEY_SECURITY.md has a table of contents."""
        doc_path = PROJECT_ROOT / "docs" / "api" / "API_KEY_SECURITY.md"

        with open(doc_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check for table of contents
        assert "## Table of Contents" in content or "## Contents" in content, \
            "API_KEY_SECURITY.md should have a Table of Contents"

        # Check for multiple section links
        section_link_pattern = r'\d+\.\s+\[.+\]\(#.+\)'
        section_links = re.findall(section_link_pattern, content)
        assert len(section_links) >= 5, \
            f"Table of Contents should have multiple sections, found {len(section_links)}"

    def test_security_doc_has_version_and_date(self):
        """Verify API_KEY_SECURITY.md includes version and last updated date."""
        doc_path = PROJECT_ROOT / "docs" / "api" / "API_KEY_SECURITY.md"

        with open(doc_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check for version
        assert "Version:" in content or "**Version:**" in content, \
            "API_KEY_SECURITY.md should include version information"

        # Check for last updated date
        assert "Last Updated:" in content or "**Last Updated:**" in content, \
            "API_KEY_SECURITY.md should include last updated date"

    def test_checklist_references_main_doc(self):
        """Verify checklist references the comprehensive security guide."""
        checklist_path = PROJECT_ROOT / "docs" / "quick-reference" / "API_KEY_SAFETY_CHECKLIST.md"

        with open(checklist_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check for reference to API_KEY_SECURITY.md
        assert "API_KEY_SECURITY.md" in content, \
            "API_KEY_SAFETY_CHECKLIST.md must reference API_KEY_SECURITY.md for detailed guidance"

    def test_backend_readme_structure(self):
        """Verify backend README has proper structure with security warning."""
        readme_path = PROJECT_ROOT / "backend" / "README.md"

        with open(readme_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Security warning should appear early in the document
        lines = content.split('\n')
        security_line = None

        for i, line in enumerate(lines):
            if 'SECURITY WARNING' in line.upper() or 'CRITICAL' in line.upper():
                security_line = i
                break

        assert security_line is not None, \
            "Backend README must have a SECURITY WARNING section"

        assert security_line < 50, \
            f"Security warning should appear early in README (found at line {security_line})"

    def test_documentation_formatting_quality(self):
        """Verify documentation uses proper markdown formatting."""
        doc_path = PROJECT_ROOT / "docs" / "api" / "API_KEY_SECURITY.md"

        with open(doc_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check for proper heading hierarchy (should start with # or ##)
        first_heading = re.search(r'^(#{1,6})\s+(.+)$', content, re.MULTILINE)
        assert first_heading is not None, \
            "API_KEY_SECURITY.md should start with a proper heading"

        # Check for code blocks with language specifiers
        code_blocks_with_lang = re.findall(r'```(\w+)', content)
        code_blocks_total = content.count('```') // 2

        if code_blocks_total > 0:
            lang_percentage = len(code_blocks_with_lang) / code_blocks_total
            assert lang_percentage > 0.5, \
                f"Most code blocks should specify language ({len(code_blocks_with_lang)}/{code_blocks_total})"

    def test_checklist_has_architecture_diagram(self):
        """Verify checklist includes architecture diagram or reference."""
        checklist_path = PROJECT_ROOT / "docs" / "quick-reference" / "API_KEY_SAFETY_CHECKLIST.md"

        with open(checklist_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check for architecture section or diagram
        assert any(term in content for term in ["Architecture", "architecture", "diagram", "```"]), \
            "API_KEY_SAFETY_CHECKLIST.md should include architecture reference"

    def test_security_doc_comprehensive_coverage(self):
        """Verify API_KEY_SECURITY.md covers all required security topics."""
        doc_path = PROJECT_ROOT / "docs" / "api" / "API_KEY_SECURITY.md"

        with open(doc_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Required security topics
        required_topics = [
            "environment variable",
            "backend proxy",
            "mobile",
            "incident response",
            "git",
            "secret",
            "authentication"
        ]

        missing_topics = []
        for topic in required_topics:
            if topic.lower() not in content.lower():
                missing_topics.append(topic)

        assert len(missing_topics) == 0, \
            f"API_KEY_SECURITY.md is missing required topics: {missing_topics}"


class TestSecurityDocumentationIntegration:
    """Integration tests for security documentation consistency."""

    def test_all_security_docs_cross_reference(self):
        """Verify all security docs reference each other appropriately."""
        # Read all security-related docs
        main_doc = PROJECT_ROOT / "docs" / "api" / "API_KEY_SECURITY.md"
        checklist = PROJECT_ROOT / "docs" / "quick-reference" / "API_KEY_SAFETY_CHECKLIST.md"
        backend_readme = PROJECT_ROOT / "backend" / "README.md"

        with open(main_doc, 'r', encoding='utf-8') as f:
            main_content = f.read()

        with open(checklist, 'r', encoding='utf-8') as f:
            checklist_content = f.read()

        with open(backend_readme, 'r', encoding='utf-8') as f:
            readme_content = f.read()

        # Backend README should reference main doc
        assert "API_KEY_SECURITY.md" in readme_content, \
            "Backend README must reference API_KEY_SECURITY.md"

        # Checklist should reference main doc
        assert "API_KEY_SECURITY.md" in checklist_content, \
            "Checklist must reference API_KEY_SECURITY.md"

        # Backend README should reference checklist
        assert "API_KEY_SAFETY_CHECKLIST.md" in readme_content, \
            "Backend README should reference API_KEY_SAFETY_CHECKLIST.md"

    def test_consistent_terminology_across_docs(self):
        """Verify consistent use of security terminology across all docs."""
        docs = [
            PROJECT_ROOT / "docs" / "api" / "API_KEY_SECURITY.md",
            PROJECT_ROOT / "docs" / "quick-reference" / "API_KEY_SAFETY_CHECKLIST.md",
            PROJECT_ROOT / "backend" / "README.md"
        ]

        # Key terms that should be used consistently
        key_terms = [
            "API key",
            "backend proxy",
            "client-side"
        ]

        for doc_path in docs:
            if not doc_path.exists():
                continue

            with open(doc_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # At least some key terms should appear
            found_terms = [term for term in key_terms if term.lower() in content.lower()]
            assert len(found_terms) >= 1, \
                f"{doc_path.name} should use consistent security terminology"

    def test_security_documentation_completeness(self):
        """Verify all required security documentation is in place."""
        required_docs = [
            PROJECT_ROOT / "docs" / "api" / "API_KEY_SECURITY.md",
            PROJECT_ROOT / "docs" / "quick-reference" / "API_KEY_SAFETY_CHECKLIST.md",
            PROJECT_ROOT / "backend" / "README.md"
        ]

        for doc_path in required_docs:
            assert doc_path.exists(), f"Required security doc missing: {doc_path}"

            # Check file is not empty
            stat = doc_path.stat()
            assert stat.st_size > 100, f"Security doc is too small (possibly empty): {doc_path}"


# Test markers for selective execution
pytestmark = pytest.mark.unit
