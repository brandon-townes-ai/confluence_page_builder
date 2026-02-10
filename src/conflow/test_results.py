"""Test results processing for Confluence templates.

This module handles parsing the Test section table from Confluence HTML
and prompting users for Pass/Fail results.
"""

import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from bs4 import BeautifulSoup, Tag

from conflow.exceptions import InteractiveInputError

logger = logging.getLogger(__name__)

# Column indices in the Test table (0-indexed)
SCENARIO_COL = 0              # Scenario name column
TEST_ID_COL = 1               # Test ID column
RAP107_FEATURE_COL = 2        # RAP-107 Feature Result column
RAP107_STABILITY_COL = 3      # RAP-107 Stack Stability column
KOM101_FEATURE_COL = 4        # KOM-101 Feature Result column
KOM101_STABILITY_COL = 5      # KOM-101 Stack Stability column


@dataclass
class TestResultRow:
    """Represents a single test row from the Test table."""

    scenario_name: str
    test_id: str                    # Test ID from column 1
    rap107_feature_status: str      # RAP-107 Feature Result
    rap107_stability_status: str    # RAP-107 Stack Stability
    kom101_feature_status: str      # KOM-101 Feature Result
    kom101_stability_status: str    # KOM-101 Stack Stability
    row_index: int                  # Index in the table (0 = first data row)


def find_test_table(html: str) -> Optional[Tag]:
    """Find the Test section table in HTML.

    Looks for an <h2> element containing "Test" and returns the next
    sibling <table> element.

    Args:
        html: The HTML content to search.

    Returns:
        The BeautifulSoup Tag for the table, or None if not found.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Find all h2 elements
    for h2 in soup.find_all("h2"):
        # Get text content and check if it contains "Test"
        h2_text = h2.get_text(strip=True)
        if h2_text == "Test" or h2_text.lower() == "test":
            # Look for next sibling table
            next_sibling = h2.find_next_sibling()
            while next_sibling:
                if next_sibling.name == "table":
                    logger.debug(f"Found Test table after <h2>{h2_text}</h2>")
                    return next_sibling
                next_sibling = next_sibling.find_next_sibling()

    logger.debug("No Test table found in HTML")
    return None


def extract_test_rows(table: Tag) -> List[TestResultRow]:
    """Extract test rows that need user input (have 'I' status).

    Args:
        table: BeautifulSoup Tag for the table element.

    Returns:
        List of TestResultRow objects for rows where any of the 4 result columns has 'I' status.
    """
    rows = []
    tbody = table.find("tbody")
    if not tbody:
        logger.debug("No tbody found in table")
        return rows

    # Get all tr elements
    all_trs = tbody.find_all("tr")
    if not all_trs:
        logger.debug("No tr elements found in tbody")
        return rows

    # Skip header rows (rows with th elements)
    # New template has 2 header rows
    data_rows = []
    for tr in all_trs:
        # If row contains th elements, it's a header row
        if tr.find("th"):
            continue
        data_rows.append(tr)

    logger.debug(f"Found {len(data_rows)} data rows in Test table")

    # Track scenario for rows with rowspan
    current_scenario = ""

    for row_idx, tr in enumerate(data_rows):
        cells = tr.find_all("td")

        if len(cells) < 6:
            # This might be a row that's part of a rowspan
            # Try to use fewer columns with current_scenario
            if len(cells) >= 5:
                # Row has Test ID and 4 result columns (no Scenario due to rowspan)
                test_id = _get_cell_text(cells[0])
                rap107_feature = _get_cell_text(cells[1])
                rap107_stability = _get_cell_text(cells[2])
                kom101_feature = _get_cell_text(cells[3])
                kom101_stability = _get_cell_text(cells[4])
                scenario = current_scenario
            else:
                logger.debug(f"Row {row_idx} has insufficient cells: {len(cells)}")
                continue
        else:
            # Full row with all 6 columns
            scenario_cell = cells[SCENARIO_COL]
            # Check for rowspan and update current_scenario
            if scenario_cell.get("rowspan"):
                current_scenario = _get_cell_text(scenario_cell)
            scenario = _get_cell_text(scenario_cell) or current_scenario

            test_id = _get_cell_text(cells[TEST_ID_COL])
            rap107_feature = _get_cell_text(cells[RAP107_FEATURE_COL])
            rap107_stability = _get_cell_text(cells[RAP107_STABILITY_COL])
            kom101_feature = _get_cell_text(cells[KOM101_FEATURE_COL])
            kom101_stability = _get_cell_text(cells[KOM101_STABILITY_COL])

        # Only include rows where any of the 4 result columns has 'I' status
        if (rap107_feature == "I" or rap107_stability == "I" or
            kom101_feature == "I" or kom101_stability == "I"):
            test_row = TestResultRow(
                scenario_name=scenario,
                test_id=test_id,
                rap107_feature_status=rap107_feature,
                rap107_stability_status=rap107_stability,
                kom101_feature_status=kom101_feature,
                kom101_stability_status=kom101_stability,
                row_index=row_idx,
            )
            rows.append(test_row)
            logger.debug(
                f"Row {row_idx}: {scenario} (Test ID: {test_id}) - "
                f"RAP107 Feature={rap107_feature}, RAP107 Stability={rap107_stability}, "
                f"KOM101 Feature={kom101_feature}, KOM101 Stability={kom101_stability}"
            )

    return rows


def _get_cell_text(cell: Tag) -> str:
    """Extract text content from a table cell.

    Handles cells with nested <p> tags.

    Args:
        cell: BeautifulSoup Tag for a td element.

    Returns:
        The text content, stripped of whitespace.
    """
    # Try to get text from nested <p> tag first
    p_tag = cell.find("p")
    if p_tag:
        return p_tag.get_text(strip=True)
    return cell.get_text(strip=True)


def collect_test_results(
    test_rows: List[TestResultRow],
    non_interactive: bool = False,
) -> Dict[Tuple[int, str], str]:
    """Collect Pass/Fail/Incomplete/Skipped results from user for test rows.

    Args:
        test_rows: List of TestResultRow objects to collect results for.
        non_interactive: If True, raise error instead of prompting.

    Returns:
        Dict mapping (row_index, column_name) to result ("P", "F", "I", or "-").
        column_name should be one of: "rap107_feature", "rap107_stability",
        "kom101_feature", "kom101_stability"

    Raises:
        InteractiveInputError: If non_interactive=True and there are rows
            that need input.
    """
    if non_interactive and test_rows:
        incomplete_scenarios = [row.scenario_name for row in test_rows]
        raise InteractiveInputError(
            f"Test results table contains {len(test_rows)} incomplete entries "
            f"(marked with 'I'). Use interactive mode or remove --test-results flag. "
            f"Scenarios: {', '.join(set(incomplete_scenarios))}"
        )

    # Import here to avoid circular imports
    from conflow.interactive import collect_test_result

    results: Dict[Tuple[int, str], str] = {}

    for row in test_rows:
        # Create display name with Test ID
        display_name = row.scenario_name
        if row.test_id and row.test_id.upper() != "N/A":
            display_name = f"{row.scenario_name} (Test ID: {row.test_id})"

        if row.rap107_feature_status == "I":
            result = collect_test_result(display_name, "RAP-107 Feature Result")
            results[(row.row_index, "rap107_feature")] = result

        if row.rap107_stability_status == "I":
            result = collect_test_result(display_name, "RAP-107 Stack Stability")
            results[(row.row_index, "rap107_stability")] = result

        if row.kom101_feature_status == "I":
            result = collect_test_result(display_name, "KOM-101 Feature Result")
            results[(row.row_index, "kom101_feature")] = result

        if row.kom101_stability_status == "I":
            result = collect_test_result(display_name, "KOM-101 Stack Stability")
            results[(row.row_index, "kom101_stability")] = result

    return results


def update_test_table(
    html: str,
    results: Dict[Tuple[int, str], str],
) -> str:
    """Update the Test table HTML with test results.

    Updates cells with colored backgrounds for the new template structure.
    Pass (P) and Fail (F) results display as colored cells with no text.
    Incomplete (I) displays text with no color. Skipped (-) displays text
    with gray background.

    Args:
        html: The original HTML content.
        results: Dict mapping (row_index, column_name) to result ("P", "F", "I", or "-").
                 column_name should be one of: "rap107_feature", "rap107_stability",
                 "kom101_feature", "kom101_stability"

    Returns:
        The modified HTML with results inserted. P/F cells will be colored
        but empty, I/- cells will contain text.
    """
    if not results:
        return html

    soup = BeautifulSoup(html, "html.parser")
    table = find_test_table(str(soup))

    if not table:
        logger.warning("Could not find Test table when updating results")
        return html

    # Re-parse to get modifiable soup
    soup = BeautifulSoup(html, "html.parser")

    # Find the table again in the modifiable soup
    for h2 in soup.find_all("h2"):
        h2_text = h2.get_text(strip=True)
        if h2_text == "Test" or h2_text.lower() == "test":
            table = h2.find_next_sibling("table")
            if table:
                break
    else:
        return html

    tbody = table.find("tbody")
    if not tbody:
        return html

    # Get data rows (skip header)
    data_rows = []
    for tr in tbody.find_all("tr"):
        if not tr.find("th"):
            data_rows.append(tr)

    # Apply results
    for (row_idx, column), result in results.items():
        if row_idx >= len(data_rows):
            logger.warning(f"Row index {row_idx} out of range")
            continue

        tr = data_rows[row_idx]
        cells = tr.find_all("td")

        # Determine column index based on cell count (handling rowspan)
        # Map column name to index
        column_map_full = {
            "rap107_feature": RAP107_FEATURE_COL,
            "rap107_stability": RAP107_STABILITY_COL,
            "kom101_feature": KOM101_FEATURE_COL,
            "kom101_stability": KOM101_STABILITY_COL,
        }

        column_map_rowspan = {
            "rap107_feature": 1,
            "rap107_stability": 2,
            "kom101_feature": 3,
            "kom101_stability": 4,
        }

        if len(cells) >= 6:
            # Full row with all 6 columns
            col_idx = column_map_full.get(column)
        elif len(cells) >= 5:
            # Row without scenario (due to rowspan) - 5 columns
            col_idx = column_map_rowspan.get(column)
        else:
            logger.warning(f"Row {row_idx} has insufficient cells for update: {len(cells)}")
            continue

        if col_idx is None or col_idx >= len(cells):
            logger.warning(f"Column {column} not found or out of range in row {row_idx}")
            continue

        cell = cells[col_idx]

        # Determine background color and display text based on result
        if result in ["P", "Pass"]:
            confluence_color = "subtle-green"
            display_text = ""  # Empty string for Pass
        elif result in ["F", "Fail"]:
            confluence_color = "subtle-red"
            display_text = ""  # Empty string for Fail
        elif result == "-":
            confluence_color = "bold-gray"
            display_text = "-"
        elif result in ["I", "Incomplete"]:
            confluence_color = None
            display_text = "I"
        else:
            confluence_color = None
            display_text = result

        # Update the cell text
        p_tag = cell.find("p")
        if p_tag:
            p_tag.string = display_text
        else:
            cell.string = display_text

        # Set Confluence background color using class and data attributes
        if confluence_color:
            # Map to Confluence's highlight classes
            color_class_map = {
                "subtle-green": "rgb(227, 252, 239)",
                "subtle-red": "rgb(255,235,230)",
                "bold-gray": "rgb(230, 230, 230)",
            }

            if confluence_color in color_class_map:
                color_name = color_class_map[confluence_color]

                # Set both the class and data-highlight-colour attributes
                # This is the correct format for Confluence storage format
                # Note: Must set class as a list to prevent BeautifulSoup from splitting on spaces
                cell["class"] = [f"highlight-{color_name}"]
                cell["data-highlight-colour"] = color_name

                logger.debug(f"Set cell color class: highlight-{color_name}, data-highlight-colour: {color_name}")

        logger.debug(f"Updated row {row_idx} {column} to '{display_text}' with color {confluence_color}")

    return str(soup)


def process_test_results(
    html: str,
    non_interactive: bool = False,
) -> str:
    """Main entry point for test results processing.

    Finds the Test table, extracts rows needing input, collects results
    from the user, and returns the updated HTML.

    Args:
        html: The HTML content to process.
        non_interactive: If True, raise error if any rows need input.

    Returns:
        The modified HTML with test results filled in.

    Raises:
        InteractiveInputError: If non_interactive=True and there are
            incomplete test rows.
    """
    # Find the test table
    table = find_test_table(html)
    if not table:
        logger.debug("No Test table found, skipping test results processing")
        return html

    # Extract rows that need input
    test_rows = extract_test_rows(table)
    if not test_rows:
        logger.debug("No incomplete test rows found")
        return html

    logger.info(f"Found {len(test_rows)} test row(s) needing results")

    # Collect results from user
    results = collect_test_results(test_rows, non_interactive)

    # Update the HTML with results
    return update_test_table(html, results)
