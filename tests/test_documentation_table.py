"""Tests for documentation_table module."""

from conflow.documentation_table import (
    find_documentation_table,
    process_documentation_table,
    update_documentation_date,
)


class TestFindDocumentationTable:
    """Tests for find_documentation_table function."""

    def test_finds_documentation_table_after_h2(self):
        """Test finding Documentation table after <h2> tag."""
        html = """
        <h2>Documentation</h2>
        <table>
          <tbody>
            <tr><td>Date</td><td></td></tr>
          </tbody>
        </table>
        """
        table = find_documentation_table(html)
        assert table is not None
        assert table.name == "table"

    def test_finds_documentation_table_after_h1(self):
        """Test finding Documentation table after <h1> tag."""
        html = """
        <h1>Documentation</h1>
        <table>
          <tbody>
            <tr><td>Date</td><td></td></tr>
          </tbody>
        </table>
        """
        table = find_documentation_table(html)
        assert table is not None
        assert table.name == "table"

    def test_returns_none_when_no_documentation_section(self):
        """Test returns None when no Documentation section exists."""
        html = """
        <h2>Other Section</h2>
        <table><tbody><tr><td>Test</td></tr></tbody></table>
        """
        table = find_documentation_table(html)
        assert table is None

    def test_returns_none_when_no_table_after_documentation_h2(self):
        """Test returns None when Documentation h2 has no table sibling."""
        html = """
        <h2>Documentation</h2>
        <p>Some text here</p>
        """
        table = find_documentation_table(html)
        assert table is None

    def test_case_insensitive_documentation_header(self):
        """Test Documentation header matching is case-insensitive."""
        html = """
        <h2>DOCUMENTATION</h2>
        <table><tbody><tr><td>Date</td><td></td></tr></tbody></table>
        """
        table = find_documentation_table(html)
        assert table is not None


class TestUpdateDocumentationDate:
    """Tests for update_documentation_date function."""

    def test_updates_empty_date_field(self):
        """Test updating an empty Date field."""
        html = """
        <h2>Documentation</h2>
        <table>
          <tbody>
            <tr><td><p>Date</p></td><td><p></p></td></tr>
            <tr><td><p>Tester</p></td><td><p></p></td></tr>
          </tbody>
        </table>
        """
        result = update_documentation_date(html, "Dec 23, 2025")
        assert "Dec 23, 2025" in result
        assert "<td><p>Date</p></td>" in result

    def test_updates_empty_date_field_with_h1(self):
        """Test updating an empty Date field when Documentation uses h1."""
        html = """
        <h1>Documentation</h1>
        <table>
          <tbody>
            <tr><td><p>Date</p></td><td><p></p></td></tr>
            <tr><td><p>Tester</p></td><td><p></p></td></tr>
          </tbody>
        </table>
        """
        result = update_documentation_date(html, "Dec 23, 2025")
        assert "Dec 23, 2025" in result
        assert "<td><p>Date</p></td>" in result

    def test_updates_date_field_with_custom_value(self):
        """Test updating Date field with a custom date value."""
        html = """
        <h2>Documentation</h2>
        <table>
          <tbody>
            <tr><td>Date</td><td></td></tr>
          </tbody>
        </table>
        """
        result = update_documentation_date(html, "Jan 1, 2024")
        assert "Jan 1, 2024" in result

    def test_updates_date_field_without_p_tags(self):
        """Test updating Date field when cells don't have <p> tags."""
        html = """
        <h2>Documentation</h2>
        <table>
          <tbody>
            <tr><td>Date</td><td></td></tr>
          </tbody>
        </table>
        """
        result = update_documentation_date(html, "Dec 23, 2025")
        assert "Dec 23, 2025" in result

    def test_does_not_update_already_filled_date(self):
        """Test that already filled Date field is not overwritten."""
        html = """
        <h2>Documentation</h2>
        <table>
          <tbody>
            <tr><td><p>Date</p></td><td><p>Existing Date</p></td></tr>
          </tbody>
        </table>
        """
        result = update_documentation_date(html, "Dec 23, 2025")
        assert "Existing Date" in result
        assert "Dec 23, 2025" not in result

    def test_updates_placeholder_in_date_field(self):
        """Test that placeholder {{DATE}} in Date field gets replaced."""
        html = """
        <h2>Documentation</h2>
        <table>
          <tbody>
            <tr><td><p>Date</p></td><td><p>{{DATE}}</p></td></tr>
          </tbody>
        </table>
        """
        result = update_documentation_date(html, "Dec 23, 2025")
        assert "Dec 23, 2025" in result
        assert "{{DATE}}" not in result

    def test_case_insensitive_date_row_detection(self):
        """Test that Date row is found regardless of case."""
        html = """
        <h2>Documentation</h2>
        <table>
          <tbody>
            <tr><td><p>date</p></td><td><p></p></td></tr>
          </tbody>
        </table>
        """
        result = update_documentation_date(html, "Dec 23, 2025")
        assert "Dec 23, 2025" in result

    def test_returns_unchanged_html_when_no_documentation_table(self):
        """Test returns unchanged HTML when no Documentation table found."""
        html = """
        <h2>Other Section</h2>
        <p>Some content</p>
        """
        result = update_documentation_date(html, "Dec 23, 2025")
        assert result == html

    def test_handles_multiple_rows(self):
        """Test updating Date field when table has multiple rows."""
        html = """
        <h2>Documentation</h2>
        <table>
          <tbody>
            <tr><td><p>Date</p></td><td><p></p></td></tr>
            <tr><td><p>Tester</p></td><td><p>Alice</p></td></tr>
            <tr><td><p>Branch</p></td><td><p>main</p></td></tr>
          </tbody>
        </table>
        """
        result = update_documentation_date(html, "Dec 23, 2025")
        assert "Dec 23, 2025" in result
        assert "Alice" in result
        assert "main" in result


class TestProcessDocumentationTable:
    """Tests for process_documentation_table function."""

    def test_full_workflow_with_date_update(self):
        """Test full workflow processes date correctly."""
        html = """
        <h2>Documentation</h2>
        <table>
          <tbody>
            <tr><td>Date</td><td></td></tr>
            <tr><td>Tester</td><td>Bob</td></tr>
          </tbody>
        </table>
        """
        result = process_documentation_table(html)
        # Should contain a date (check for month abbreviations)
        assert any(month in result for month in ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                                                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
        assert "Bob" in result

    def test_no_documentation_table_returns_unchanged(self):
        """Test returns unchanged HTML when no Documentation table."""
        html = """
        <h2>Other Section</h2>
        <p>Content here</p>
        """
        result = process_documentation_table(html)
        assert result == html
