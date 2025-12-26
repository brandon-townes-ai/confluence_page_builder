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
SCENARIO_COL = 0
TEST_ID_COL = 1
VARIATION_COL = 2
RAPTOR_COL = 3
HM400_COL = 4


@dataclass
class TestResultRow:
    """Represents a single test row from the Test table."""

    scenario_name: str
    variation: str
    raptor_status: str  # "I", "P", "F", or other
    hm400_status: str  # "I", "P", "F", or other
    row_index: int  # Index in the table (0 = first data row)


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
        List of TestResultRow objects for rows where Raptor or HM400 has 'I' status.
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

    # Skip header row (first row with th elements)
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

        if len(cells) < 5:
            # This might be a row that's part of a rowspan
            # Try to use fewer columns with current_scenario
            if len(cells) >= 4:
                # Row has Test ID, Variation, Raptor, HM400 (no Scenario due to rowspan)
                variation = _get_cell_text(cells[1])
                raptor_status = _get_cell_text(cells[2])
                hm400_status = _get_cell_text(cells[3])
                scenario = current_scenario
            else:
                logger.debug(f"Row {row_idx} has insufficient cells: {len(cells)}")
                continue
        else:
            # Full row with all columns
            scenario_cell = cells[SCENARIO_COL]
            # Check for rowspan and update current_scenario
            if scenario_cell.get("rowspan"):
                current_scenario = _get_cell_text(scenario_cell)
            scenario = _get_cell_text(scenario_cell) or current_scenario

            variation = _get_cell_text(cells[VARIATION_COL])
            raptor_status = _get_cell_text(cells[RAPTOR_COL])
            hm400_status = _get_cell_text(cells[HM400_COL])

        # Only include rows where Raptor or HM400 has 'I' status
        if raptor_status == "I" or hm400_status == "I":
            test_row = TestResultRow(
                scenario_name=scenario,
                variation=variation,
                raptor_status=raptor_status,
                hm400_status=hm400_status,
                row_index=row_idx,
            )
            rows.append(test_row)
            logger.debug(
                f"Row {row_idx}: {scenario} ({variation}) - "
                f"Raptor={raptor_status}, HM400={hm400_status}"
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
    """Collect Pass/Fail/Incomplete results from user for test rows.

    Args:
        test_rows: List of TestResultRow objects to collect results for.
        non_interactive: If True, raise error instead of prompting.

    Returns:
        Dict mapping (row_index, column_name) to result ("P", "F", or "I").

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
        # Create display name with variation if present
        display_name = row.scenario_name
        if row.variation and row.variation.upper() != "N/A":
            display_name = f"{row.scenario_name} ({row.variation})"

        if row.raptor_status == "I":
            result = collect_test_result(display_name, "Raptor")
            results[(row.row_index, "raptor")] = result

        if row.hm400_status == "I":
            result = collect_test_result(display_name, "HM400")
            results[(row.row_index, "hm400")] = result

    return results


def update_test_table(
    html: str,
    results: Dict[Tuple[int, str], str],
) -> str:
    """Update the Test table HTML with test results.

    Args:
        html: The original HTML content.
        results: Dict mapping (row_index, column_name) to result ("P" or "F").

    Returns:
        The modified HTML with results inserted.
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
        if len(cells) >= 5:
            # Full row
            col_idx = RAPTOR_COL if column == "raptor" else HM400_COL
        elif len(cells) >= 4:
            # Row without scenario (due to rowspan)
            col_idx = 2 if column == "raptor" else 3
        else:
            logger.warning(f"Row {row_idx} has insufficient cells for update")
            continue

        if col_idx < len(cells):
            cell = cells[col_idx]

            # Determine background color based on result
            if result in ["P", "Pass"]:
                bg_color = "#dff0d8"  # Light green for Pass
            elif result in ["F", "Fail"]:
                bg_color = "#f2dede"  # Light red for Fail
            else:
                bg_color = None  # No color for Incomplete

            # Update the <p> tag inside, or the cell directly
            p_tag = cell.find("p")
            if p_tag:
                p_tag.string = result
                if bg_color:
                    # Add background color to the p tag
                    current_style = p_tag.get("style", "")
                    if current_style and not current_style.endswith(";"):
                        current_style += ";"
                    p_tag["style"] = f"{current_style}background-color: {bg_color};"
            else:
                cell.string = result

            # Also set background color on the cell itself
            if bg_color:
                current_style = cell.get("style", "")
                if current_style and not current_style.endswith(";"):
                    current_style += ";"
                cell["style"] = f"{current_style}background-color: {bg_color};"

            logger.debug(f"Updated row {row_idx} {column} to '{result}' with color {bg_color}")

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
