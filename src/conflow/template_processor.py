"""Conflow."""

import re
from typing import Dict, List

from conflow.exceptions import TemplateError

_LOCAL_ID_PATTERN = re.compile(r'\s+(?:(?:ac|ri):)?local-id="[^"]*"')
_CARD_APPEARANCE_PATTERN = re.compile(r'\s+ac:card-appearance="[^"]*"')
_LINK_BODY_PATTERN = re.compile(r'<ac:link-body>(.*?)</ac:link-body>', re.DOTALL)
_VERSION_AT_SAVE_PATTERN = re.compile(r'\s+ri:version-at-save="[^"]*"')
_MACRO_ID_PATTERN = re.compile(r'\s+ac:macro-id="[^"]*"')
_TABLE_LAYOUT_PATTERN = re.compile(r'\s+data-layout="[^"]*"')
_TABLE_WIDTH_PATTERN = re.compile(r'\s+data-table-width="[^"]*"')

PLACEHOLDER_PATTERN = re.compile(r"\{\{([A-Za-z_]+)\}\}")


def extract_placeholders(content: str) -> List[str]:
    """Extract all unique placeholder names from content.

    Args:
        content: The template content to scan.

    Returns:
        List of unique placeholder names (without braces), in order of first appearance.
    """
    matches = PLACEHOLDER_PATTERN.findall(content)
    seen = set()
    unique = []
    for match in matches:
        if match not in seen:
            seen.add(match)
            unique.append(match)
    return unique


def substitute_placeholders(
    content: str,
    values: Dict[str, str],
    strict: bool = False,
) -> str:
    """Substitute placeholders in content with provided values.

    Args:
        content: The template content with placeholders.
        values: Dictionary mapping placeholder names to values.
        strict: If True, raise an error for missing placeholder values.

    Returns:
        Content with placeholders replaced by values.

    Raises:
        TemplateError: If strict=True and any placeholder lacks a value.
    """
    placeholders = extract_placeholders(content)

    if strict:
        missing = [p for p in placeholders if p not in values]
        if missing:
            raise TemplateError(
                f"Missing values for placeholders: {', '.join(missing)}"
            )

    result = content
    for name, value in values.items():
        placeholder = f"{{{{{name}}}}}"
        result = result.replace(placeholder, value)

    return result


def strip_fabric_metadata(content: str) -> str:
    """Remove Fabric editor metadata from Confluence storage format content.

    Confluence's REST API rejects content containing Fabric-specific attributes
    and elements when using the storage representation.
    """
    content = _LOCAL_ID_PATTERN.sub("", content)
    content = _CARD_APPEARANCE_PATTERN.sub("", content)
    content = _LINK_BODY_PATTERN.sub(r'\1', content)
    content = _VERSION_AT_SAVE_PATTERN.sub("", content)
    content = _MACRO_ID_PATTERN.sub("", content)
    content = _TABLE_LAYOUT_PATTERN.sub("", content)
    content = _TABLE_WIDTH_PATTERN.sub("", content)
    return content


# Keep old name as alias for backwards compatibility
strip_local_ids = strip_fabric_metadata


def format_placeholder_name(name: str) -> str:
    """Format a placeholder name for display.

    Converts FIELD_NAME to "Field Name" for user-friendly prompts.

    Args:
        name: The placeholder name (e.g., "PROJECT_NAME").

    Returns:
        Human-readable formatted name (e.g., "Project Name").
    """
    return name.replace("_", " ").title()
