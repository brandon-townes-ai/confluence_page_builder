"""Documentation table processing for Confluence templates.

This module handles parsing the Documentation section table from Confluence HTML
and automatically filling in the Date field.
"""

import logging
from datetime import datetime
from typing import Optional

from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)


def find_documentation_table(html: str) -> Optional[Tag]:
    """Find the Documentation section table in HTML.

    Looks for an <h1> or <h2> element containing "Documentation" and returns the next
    sibling <table> element.

    Args:
        html: The HTML content to search.

    Returns:
        The BeautifulSoup Tag for the table, or None if not found.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Find all h1 and h2 elements and log them
    all_headings = soup.find_all(["h1", "h2"])
    logger.debug(f"Found {len(all_headings)} h1/h2 elements in HTML")
    for heading in all_headings:
        heading_text = heading.get_text(strip=True)
        logger.debug(f"  {heading.name} text: '{heading_text}'")

    # Find all h1 and h2 elements
    for heading in soup.find_all(["h1", "h2"]):
        # Get text content and check if it contains "Documentation"
        heading_text = heading.get_text(strip=True)
        if heading_text.lower() == "documentation":
            logger.debug(f"Found Documentation {heading.name}: '{heading_text}'")
            # Look for next sibling table
            next_sibling = heading.find_next_sibling()
            while next_sibling:
                logger.debug(f"  Checking sibling: {next_sibling.name}")
                if next_sibling.name == "table":
                    logger.info(f"Found Documentation table after <{heading.name}>{heading_text}</{heading.name}>")
                    return next_sibling
                next_sibling = next_sibling.find_next_sibling()

    logger.warning("No Documentation table found in HTML")
    return None


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


def update_documentation_date(html: str, date_value: Optional[str] = None) -> str:
    """Update the Date field in the Documentation table.

    Args:
        html: The original HTML content.
        date_value: The date value to insert. If None, uses current date.

    Returns:
        The modified HTML with date inserted.
    """
    if date_value is None:
        date_value = datetime.now().strftime("%b %d, %Y")

    soup = BeautifulSoup(html, "html.parser")
    table = find_documentation_table(str(soup))

    if not table:
        logger.debug("No Documentation table found, skipping date update")
        return html

    # Re-parse to get modifiable soup
    soup = BeautifulSoup(html, "html.parser")

    # Find the table again in the modifiable soup
    for heading in soup.find_all(["h1", "h2"]):
        heading_text = heading.get_text(strip=True)
        if heading_text.lower() == "documentation":
            table = heading.find_next_sibling("table")
            if table:
                break
    else:
        return html

    tbody = table.find("tbody")
    if not tbody:
        logger.warning("No tbody found in Documentation table")
        return html

    # Find the Date row by looking for a cell with "Date" text in the first column
    all_rows = tbody.find_all("tr")
    logger.debug(f"Found {len(all_rows)} rows in Documentation table tbody")

    found_date_row = False
    for row_idx, tr in enumerate(all_rows):
        # Get both th and td cells (first column might be th, second is td)
        cells = tr.find_all(["th", "td"])
        logger.debug(f"  Row {row_idx}: {len(cells)} cells")

        if len(cells) >= 2:
            first_cell_text = _get_cell_text(cells[0])
            logger.debug(f"    First cell text: '{first_cell_text}'")

            # Check if this is the Date row (case-insensitive)
            if first_cell_text.lower() == "date":
                found_date_row = True
                logger.debug(f"    Found Date row at index {row_idx}")

                # Check if the second cell is empty or has placeholder content
                second_cell = cells[1]
                current_text = _get_cell_text(second_cell)
                logger.debug(f"    Current date cell value: '{current_text}'")

                # Only update if empty or if it's still a placeholder
                if not current_text or current_text.startswith("{{"):
                    logger.debug(f"    Updating date cell with: {date_value}")
                    # Update the <p> tag inside, or the cell directly
                    p_tag = second_cell.find("p")
                    if p_tag:
                        p_tag.string = date_value
                        logger.debug("    Updated <p> tag")
                    else:
                        # Create a <p> tag with the date
                        new_p = soup.new_tag("p")
                        new_p.string = date_value
                        second_cell.clear()
                        second_cell.append(new_p)
                        logger.debug("    Created new <p> tag")

                    logger.info(f"Successfully updated Documentation Date field to: {date_value}")
                else:
                    logger.info(f"Date field already has value: '{current_text}' - skipping update")
                break

    if not found_date_row:
        logger.warning("Did not find Date row in Documentation table")

    return str(soup)


def process_documentation_table(html: str) -> str:
    """Main entry point for documentation table processing.

    Finds the Documentation table and fills in the Date field.

    Args:
        html: The HTML content to process.

    Returns:
        The modified HTML with Date field filled in.
    """
    return update_documentation_date(html)
