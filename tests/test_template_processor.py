"""Tests for template_processor module."""

import pytest

from conflow.exceptions import TemplateError
from conflow.template_processor import (
    extract_placeholders,
    format_placeholder_name,
    substitute_placeholders,
)


class TestExtractPlaceholders:
    """Tests for extract_placeholders function."""

    def test_extract_single_placeholder(self):
        """Test extracting a single placeholder."""
        content = "Hello {{NAME}}!"
        result = extract_placeholders(content)
        assert result == ["NAME"]

    def test_extract_multiple_placeholders(self):
        """Test extracting multiple unique placeholders."""
        content = "{{FIRST}} and {{SECOND}} and {{THIRD}}"
        result = extract_placeholders(content)
        assert result == ["FIRST", "SECOND", "THIRD"]

    def test_extract_duplicate_placeholders(self):
        """Test that duplicates are only returned once."""
        content = "{{NAME}} likes {{NAME}} and {{OTHER}}"
        result = extract_placeholders(content)
        assert result == ["NAME", "OTHER"]

    def test_extract_no_placeholders(self):
        """Test content with no placeholders."""
        content = "Just plain text with no placeholders"
        result = extract_placeholders(content)
        assert result == []

    def test_extract_placeholder_with_underscores(self):
        """Test placeholder with underscores."""
        content = "{{PROJECT_NAME}} and {{OWNER_EMAIL}}"
        result = extract_placeholders(content)
        assert result == ["PROJECT_NAME", "OWNER_EMAIL"]

    def test_extract_ignores_lowercase(self):
        """Test that lowercase placeholders are ignored."""
        content = "{{VALID}} and {{invalid}} and {{Also_Invalid}}"
        result = extract_placeholders(content)
        assert result == ["VALID"]

    def test_extract_ignores_numbers(self):
        """Test that placeholders with numbers are ignored."""
        content = "{{VALID}} and {{INVALID1}}"
        result = extract_placeholders(content)
        assert result == ["VALID"]

    def test_extract_ignores_malformed(self):
        """Test that malformed placeholders are ignored."""
        content = "{{VALID}} and {SINGLE} and {{ SPACED }} and {{}}",
        result = extract_placeholders(content[0])
        assert result == ["VALID"]

    def test_extract_preserves_order(self):
        """Test that placeholders are returned in order of first appearance."""
        content = "{{THIRD}} {{FIRST}} {{THIRD}} {{SECOND}} {{FIRST}}"
        result = extract_placeholders(content)
        assert result == ["THIRD", "FIRST", "SECOND"]


class TestSubstitutePlaceholders:
    """Tests for substitute_placeholders function."""

    def test_substitute_single(self):
        """Test substituting a single placeholder."""
        content = "Hello {{NAME}}!"
        result = substitute_placeholders(content, {"NAME": "World"})
        assert result == "Hello World!"

    def test_substitute_multiple(self):
        """Test substituting multiple placeholders."""
        content = "{{GREETING}} {{NAME}}!"
        result = substitute_placeholders(
            content, {"GREETING": "Hello", "NAME": "World"}
        )
        assert result == "Hello World!"

    def test_substitute_duplicates(self):
        """Test that all occurrences are substituted."""
        content = "{{NAME}} meets {{NAME}}"
        result = substitute_placeholders(content, {"NAME": "Alice"})
        assert result == "Alice meets Alice"

    def test_substitute_preserves_extra_values(self):
        """Test that extra values don't affect the result."""
        content = "Hello {{NAME}}!"
        result = substitute_placeholders(
            content, {"NAME": "World", "UNUSED": "Extra"}
        )
        assert result == "Hello World!"

    def test_substitute_leaves_unknown_placeholders(self):
        """Test that unknown placeholders remain unchanged."""
        content = "{{KNOWN}} and {{UNKNOWN}}"
        result = substitute_placeholders(content, {"KNOWN": "replaced"})
        assert result == "replaced and {{UNKNOWN}}"

    def test_substitute_strict_mode_success(self):
        """Test strict mode with all values provided."""
        content = "{{A}} {{B}}"
        result = substitute_placeholders(
            content, {"A": "1", "B": "2"}, strict=True
        )
        assert result == "1 2"

    def test_substitute_strict_mode_missing(self):
        """Test strict mode raises error for missing values."""
        content = "{{A}} {{B}} {{C}}"
        with pytest.raises(TemplateError) as exc_info:
            substitute_placeholders(content, {"A": "1"}, strict=True)

        error_msg = str(exc_info.value)
        assert "B" in error_msg
        assert "C" in error_msg

    def test_substitute_empty_value(self):
        """Test substituting with empty string value."""
        content = "Hello {{NAME}}!"
        result = substitute_placeholders(content, {"NAME": ""})
        assert result == "Hello !"

    def test_substitute_special_characters(self):
        """Test values with special characters."""
        content = "Code: {{CODE}}"
        result = substitute_placeholders(content, {"CODE": "<script>alert('xss')</script>"})
        assert result == "Code: <script>alert('xss')</script>"


class TestFormatPlaceholderName:
    """Tests for format_placeholder_name function."""

    def test_format_simple(self):
        """Test formatting a simple name."""
        assert format_placeholder_name("NAME") == "Name"

    def test_format_with_underscores(self):
        """Test formatting name with underscores."""
        assert format_placeholder_name("PROJECT_NAME") == "Project Name"

    def test_format_multiple_underscores(self):
        """Test formatting with multiple underscores."""
        assert format_placeholder_name("FIRST_MIDDLE_LAST") == "First Middle Last"

    def test_format_single_word(self):
        """Test formatting a single word."""
        assert format_placeholder_name("TITLE") == "Title"
