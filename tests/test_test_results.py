"""Tests for test_results module."""

from unittest.mock import MagicMock, patch

import pytest
from bs4 import BeautifulSoup

from conflow.exceptions import InteractiveInputError
from conflow.test_results import (
    TestResultRow,
    extract_test_rows,
    find_test_table,
    process_test_results,
    update_test_table,
)


@pytest.fixture
def sample_test_table_html():
    """Sample HTML with a Test section table (new 6-column format)."""
    return """
    <h1>Project</h1>
    <h2>Test</h2>
    <table>
      <tbody>
        <tr>
          <th>Scenario</th>
          <th>Test ID</th>
          <th colspan="2">RAP-107</th>
          <th colspan="2">KOM-101</th>
        </tr>
        <tr>
          <th></th>
          <th></th>
          <th>Feature Result</th>
          <th>Stack Stability</th>
          <th>Feature Result</th>
          <th>Stack Stability</th>
        </tr>
        <tr>
          <td><p>Load Haul Dump Cycle</p></td>
          <td><p>TC-001</p></td>
          <td><p>I</p></td>
          <td><p>I</p></td>
          <td><p>I</p></td>
          <td><p>I</p></td>
        </tr>
        <tr>
          <td><p>Emergency Stop</p></td>
          <td><p>TC-002</p></td>
          <td><p>P</p></td>
          <td><p>I</p></td>
          <td><p>I</p></td>
          <td><p>P</p></td>
        </tr>
        <tr>
          <td><p>Obstacle Avoidance</p></td>
          <td><p>TC-003</p></td>
          <td><p>P</p></td>
          <td><p>P</p></td>
          <td><p>F</p></td>
          <td><p>F</p></td>
        </tr>
      </tbody>
    </table>
    <h2>Documentation</h2>
    """


@pytest.fixture
def sample_test_table_with_rowspan():
    """Sample HTML with Test table that has rowspan (new 6-column format)."""
    return """
    <h2>Test</h2>
    <table>
      <tbody>
        <tr>
          <th>Scenario</th>
          <th>Test ID</th>
          <th colspan="2">RAP-107</th>
          <th colspan="2">KOM-101</th>
        </tr>
        <tr>
          <th></th>
          <th></th>
          <th>Feature Result</th>
          <th>Stack Stability</th>
          <th>Feature Result</th>
          <th>Stack Stability</th>
        </tr>
        <tr>
          <td rowspan="2"><p>Obstacle Avoidance</p></td>
          <td><p>TC-001</p></td>
          <td><p>I</p></td>
          <td><p>I</p></td>
          <td><p>I</p></td>
          <td><p>I</p></td>
        </tr>
        <tr>
          <td><p>TC-002</p></td>
          <td><p>I</p></td>
          <td><p>I</p></td>
          <td><p>I</p></td>
          <td><p>I</p></td>
        </tr>
      </tbody>
    </table>
    """


class TestFindTestTable:
    """Tests for find_test_table function."""

    def test_finds_test_table_after_h2(self, sample_test_table_html):
        """Test that it finds table after <h2>Test</h2>."""
        table = find_test_table(sample_test_table_html)
        assert table is not None
        assert table.name == "table"

    def test_returns_none_when_no_test_section(self):
        """Test returns None when no Test section exists."""
        html = "<h1>Project</h1><h2>Documentation</h2><table></table>"
        table = find_test_table(html)
        assert table is None

    def test_returns_none_when_no_table_after_test_h2(self):
        """Test returns None when Test h2 exists but no table follows."""
        html = "<h2>Test</h2><p>Some text</p><h2>Other</h2>"
        table = find_test_table(html)
        assert table is None

    def test_case_insensitive_test_header(self):
        """Test that it finds table with lowercase 'test' header."""
        html = "<h2>test</h2><table><tbody><tr><td>data</td></tr></tbody></table>"
        table = find_test_table(html)
        assert table is not None


class TestExtractTestRows:
    """Tests for extract_test_rows function."""

    def test_extracts_rows_with_I_status(self, sample_test_table_html):
        """Test extraction of rows with 'I' status."""
        table = find_test_table(sample_test_table_html)
        rows = extract_test_rows(table)

        # Should find 2 rows: Load Haul Dump Cycle (all I) and Emergency Stop (has some I)
        assert len(rows) == 2
        assert rows[0].scenario_name == "Load Haul Dump Cycle"
        assert rows[0].rap107_feature_status == "I"
        assert rows[0].rap107_stability_status == "I"
        assert rows[0].kom101_feature_status == "I"
        assert rows[0].kom101_stability_status == "I"
        assert rows[1].scenario_name == "Emergency Stop"
        assert rows[1].rap107_feature_status == "P"
        assert rows[1].rap107_stability_status == "I"
        assert rows[1].kom101_feature_status == "I"
        assert rows[1].kom101_stability_status == "P"

    def test_skips_rows_without_I(self, sample_test_table_html):
        """Test that rows with P/F are skipped."""
        table = find_test_table(sample_test_table_html)
        rows = extract_test_rows(table)

        # "Obstacle Avoidance" has P/F, should not be included
        scenario_names = [row.scenario_name for row in rows]
        assert "Obstacle Avoidance" not in scenario_names

    def test_handles_rowspan(self, sample_test_table_with_rowspan):
        """Test handling of tables with rowspan."""
        table = find_test_table(sample_test_table_with_rowspan)
        rows = extract_test_rows(table)

        assert len(rows) == 2
        # Both rows should have "Obstacle Avoidance" as scenario
        assert rows[0].scenario_name == "Obstacle Avoidance"
        assert rows[0].test_id == "TC-001"
        assert rows[1].scenario_name == "Obstacle Avoidance"
        assert rows[1].test_id == "TC-002"

    def test_returns_empty_list_for_empty_table(self):
        """Test returns empty list when table has no data rows."""
        html = "<h2>Test</h2><table><tbody><tr><th>Header</th></tr></tbody></table>"
        table = find_test_table(html)
        rows = extract_test_rows(table)
        assert rows == []

    def test_returns_empty_list_when_no_tbody(self):
        """Test returns empty list when table has no tbody."""
        html = "<h2>Test</h2><table><tr><th>Header</th></tr></table>"
        table = find_test_table(html)
        rows = extract_test_rows(table)
        assert rows == []


class TestUpdateTestTable:
    """Tests for update_test_table function."""

    def test_updates_single_cell(self, sample_test_table_html):
        """Test updating a single cell."""
        results = {(0, "rap107_feature"): "P"}
        updated_html = update_test_table(sample_test_table_html, results)

        # Parse and verify the update
        soup = BeautifulSoup(updated_html, "html.parser")
        table = find_test_table(str(soup))
        tbody = table.find("tbody")
        data_rows = [tr for tr in tbody.find_all("tr") if not tr.find("th")]

        # First data row, RAP-107 Feature column (index 2)
        rap107_feature_cell = data_rows[0].find_all("td")[2]
        assert rap107_feature_cell.get_text(strip=True) == ""  # Empty for Pass

    def test_updates_multiple_cells(self, sample_test_table_html):
        """Test updating multiple cells."""
        results = {
            (0, "rap107_feature"): "P",
            (0, "kom101_feature"): "F",
            (1, "kom101_stability"): "P",
        }
        updated_html = update_test_table(sample_test_table_html, results)

        soup = BeautifulSoup(updated_html, "html.parser")
        table = find_test_table(str(soup))
        tbody = table.find("tbody")
        data_rows = [tr for tr in tbody.find_all("tr") if not tr.find("th")]

        # Check first row
        row0_cells = data_rows[0].find_all("td")
        assert row0_cells[2].get_text(strip=True) == ""  # RAP-107 Feature - empty for Pass
        assert row0_cells[4].get_text(strip=True) == ""  # KOM-101 Feature - empty for Fail

        # Check second row
        row1_cells = data_rows[1].find_all("td")
        assert row1_cells[5].get_text(strip=True) == ""  # KOM-101 Stack Stability - empty for Pass

    def test_returns_unchanged_html_when_no_results(self, sample_test_table_html):
        """Test returns unchanged HTML when results dict is empty."""
        results = {}
        updated_html = update_test_table(sample_test_table_html, results)
        assert updated_html == sample_test_table_html

    def test_returns_unchanged_html_when_no_table(self):
        """Test returns unchanged HTML when no Test table exists."""
        html = "<h1>No test table</h1>"
        results = {(0, "raptor"): "P"}
        updated_html = update_test_table(html, results)
        assert updated_html == html

    def test_skipped_displays_with_gray_background(self, sample_test_table_html):
        """Test that '-' (skipped) displays with bold-gray background."""
        results = {(0, "rap107_feature"): "-"}
        updated_html = update_test_table(sample_test_table_html, results)

        soup = BeautifulSoup(updated_html, "html.parser")
        table = find_test_table(str(soup))
        tbody = table.find("tbody")
        data_rows = [tr for tr in tbody.find_all("tr") if not tr.find("th")]

        rap107_feature_cell = data_rows[0].find_all("td")[2]
        assert rap107_feature_cell.get_text(strip=True) == "-"
        # BeautifulSoup splits class on spaces, so rgb(230, 230, 230) becomes multiple classes
        assert "highlight-rgb(230," in rap107_feature_cell.get("class", [])
        assert rap107_feature_cell.get("data-highlight-colour") == "rgb(230, 230, 230)"

    def test_incomplete_displays_with_no_background(self, sample_test_table_html):
        """Test that 'I' (incomplete) displays with no background color."""
        results = {(0, "rap107_feature"): "I"}
        updated_html = update_test_table(sample_test_table_html, results)

        soup = BeautifulSoup(updated_html, "html.parser")
        table = find_test_table(str(soup))
        tbody = table.find("tbody")
        data_rows = [tr for tr in tbody.find_all("tr") if not tr.find("th")]

        rap107_feature_cell = data_rows[0].find_all("td")[2]
        assert rap107_feature_cell.get_text(strip=True) == "I"
        assert rap107_feature_cell.get("class") is None
        assert rap107_feature_cell.get("data-highlight-colour") is None

    def test_pass_displays_with_green_background(self, sample_test_table_html):
        """Test that 'P' (pass) displays with green background and empty text."""
        results = {(0, "rap107_feature"): "P"}
        updated_html = update_test_table(sample_test_table_html, results)

        soup = BeautifulSoup(updated_html, "html.parser")
        table = find_test_table(str(soup))
        tbody = table.find("tbody")
        data_rows = [tr for tr in tbody.find_all("tr") if not tr.find("th")]

        rap107_feature_cell = data_rows[0].find_all("td")[2]
        assert rap107_feature_cell.get_text(strip=True) == ""  # Empty for Pass
        # BeautifulSoup splits class on spaces, so rgb(227, 252, 239) becomes multiple classes
        assert "highlight-rgb(227," in rap107_feature_cell.get("class", [])
        assert rap107_feature_cell.get("data-highlight-colour") == "rgb(227, 252, 239)"

    def test_fail_displays_with_red_background(self, sample_test_table_html):
        """Test that 'F' (fail) displays with red background and empty text."""
        results = {(0, "rap107_feature"): "F"}
        updated_html = update_test_table(sample_test_table_html, results)

        soup = BeautifulSoup(updated_html, "html.parser")
        table = find_test_table(str(soup))
        tbody = table.find("tbody")
        data_rows = [tr for tr in tbody.find_all("tr") if not tr.find("th")]

        rap107_feature_cell = data_rows[0].find_all("td")[2]
        assert rap107_feature_cell.get_text(strip=True) == ""  # Empty for Fail
        assert rap107_feature_cell.get("class") == ["highlight-rgb(255,235,230)"]
        assert rap107_feature_cell.get("data-highlight-colour") == "rgb(255,235,230)"


class TestProcessTestResults:
    """Tests for process_test_results function."""

    def test_full_workflow_with_results(self, sample_test_table_html):
        """Test full workflow from finding table to updating."""
        with patch("conflow.test_results.collect_test_results") as mock_collect:
            # Mock user providing results
            mock_collect.return_value = {
                (0, "rap107_feature"): "P",
                (0, "kom101_feature"): "F",
                (1, "kom101_stability"): "P",
            }

            updated_html = process_test_results(sample_test_table_html, non_interactive=False)

            # Verify collect was called
            mock_collect.assert_called_once()
            test_rows = mock_collect.call_args[0][0]
            assert len(test_rows) == 2

            # Verify HTML was updated
            soup = BeautifulSoup(updated_html, "html.parser")
            table = find_test_table(str(soup))
            tbody = table.find("tbody")
            data_rows = [tr for tr in tbody.find_all("tr") if not tr.find("th")]

            row0_cells = data_rows[0].find_all("td")
            assert row0_cells[2].get_text(strip=True) == ""  # RAP-107 Feature - empty for Pass
            assert row0_cells[4].get_text(strip=True) == ""  # KOM-101 Feature - empty for Fail

    def test_no_test_table_returns_unchanged(self):
        """Test returns unchanged HTML when no Test table."""
        html = "<h1>No test section</h1>"
        updated_html = process_test_results(html, non_interactive=False)
        assert updated_html == html

    def test_no_I_values_returns_unchanged(self):
        """Test returns unchanged HTML when no rows need input."""
        html = """
        <h2>Test</h2>
        <table>
          <tbody>
            <tr>
              <th>Scenario</th>
              <th>Test ID</th>
              <th colspan="2">RAP-107</th>
              <th colspan="2">KOM-101</th>
            </tr>
            <tr>
              <th></th>
              <th></th>
              <th>Feature Result</th>
              <th>Stack Stability</th>
              <th>Feature Result</th>
              <th>Stack Stability</th>
            </tr>
            <tr>
              <td><p>Test</p></td>
              <td><p>TC-001</p></td>
              <td><p>P</p></td>
              <td><p>P</p></td>
              <td><p>F</p></td>
              <td><p>F</p></td>
            </tr>
          </tbody>
        </table>
        """
        updated_html = process_test_results(html, non_interactive=False)
        assert updated_html == html

    def test_non_interactive_with_I_raises_error(self, sample_test_table_html):
        """Test non-interactive mode raises error when rows have 'I'."""
        with pytest.raises(InteractiveInputError) as exc_info:
            process_test_results(sample_test_table_html, non_interactive=True)

        assert "incomplete entries" in str(exc_info.value.message)
        assert "marked with 'I'" in str(exc_info.value.message)

    def test_non_interactive_without_I_succeeds(self):
        """Test non-interactive mode succeeds when no rows have 'I'."""
        html = """
        <h2>Test</h2>
        <table>
          <tbody>
            <tr>
              <th>Scenario</th>
              <th>Test ID</th>
              <th colspan="2">RAP-107</th>
              <th colspan="2">KOM-101</th>
            </tr>
            <tr>
              <th></th>
              <th></th>
              <th>Feature Result</th>
              <th>Stack Stability</th>
              <th>Feature Result</th>
              <th>Stack Stability</th>
            </tr>
            <tr>
              <td><p>Test</p></td>
              <td><p>TC-001</p></td>
              <td><p>P</p></td>
              <td><p>P</p></td>
              <td><p>P</p></td>
              <td><p>P</p></td>
            </tr>
          </tbody>
        </table>
        """
        updated_html = process_test_results(html, non_interactive=True)
        # Should return unchanged since no updates needed
        assert updated_html == html
