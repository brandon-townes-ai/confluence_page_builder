"""Conflow."""

from typing import Dict, List, Optional

from rich.console import Console
from rich.prompt import Confirm, Prompt

from conflow.exceptions import InteractiveInputError
from conflow.template_processor import format_placeholder_name

console = Console()


def collect_placeholder_values(
    placeholders: List[str],
    existing_values: Optional[Dict[str, str]] = None,
) -> Dict[str, str]:
    """Collect values for placeholders interactively.

    Args:
        placeholders: List of placeholder names to collect values for.
        existing_values: Optional pre-existing values to skip prompting for.

    Returns:
        Dictionary mapping placeholder names to user-provided values.

    Raises:
        InteractiveInputError: If the user cancels input.
    """
    existing_values = existing_values or {}
    values: Dict[str, str] = {}

    console.print()
    console.print("[bold]Fill in the template placeholders:[/bold]")
    console.print()

    try:
        for placeholder in placeholders:
            if placeholder in existing_values:
                values[placeholder] = existing_values[placeholder]
                continue

            display_name = format_placeholder_name(placeholder)
            value = Prompt.ask(f"  [cyan]{display_name}[/cyan]")

            if not value.strip():
                if not Confirm.ask(
                    f"    [yellow]'{display_name}' is empty. Continue?[/yellow]",
                    default=True,
                ):
                    raise InteractiveInputError("User cancelled input")

            values[placeholder] = value

    except KeyboardInterrupt:
        console.print()
        raise InteractiveInputError("User cancelled input")

    return values


def confirm_creation(title: str, space_key: str, parent_id: str) -> bool:
    """Confirm page creation with the user.

    Args:
        title: The page title.
        space_key: The space key.
        parent_id: The parent page ID.

    Returns:
        True if user confirms, False otherwise.
    """
    console.print()
    console.print("[bold]Page creation summary:[/bold]")
    console.print(f"  Title: [green]{title}[/green]")
    console.print(f"  Space: [green]{space_key}[/green]")
    console.print(f"  Parent ID: [green]{parent_id}[/green]")
    console.print()

    try:
        return Confirm.ask("Create this page?", default=True)
    except KeyboardInterrupt:
        console.print()
        return False


def _parse_page_id(user_input: str) -> str:
    """Parse page ID from user input.

    Handles formats:
    - "pageID: 2436039300"
    - "2436039300"
    - "pageID:2436039300" (no space)

    Args:
        user_input: Raw user input string.

    Returns:
        The extracted page ID, or empty string if invalid.
    """
    # Remove whitespace
    user_input = user_input.strip()

    # Check if it starts with "pageID:" (case-insensitive)
    if user_input.lower().startswith("pageid:"):
        # Extract everything after "pageID:"
        page_id = user_input.split(":", 1)[1].strip()
    else:
        # Assume the entire input is the page ID
        page_id = user_input

    # Validate that it's numeric
    if not page_id.isdigit():
        return ""

    return page_id


def prompt_for_page_id(non_interactive: bool = False) -> str:
    """Prompt for page ID to edit.

    Args:
        non_interactive: If True, raise error instead of prompting.

    Returns:
        The page ID as a string.

    Raises:
        InteractiveInputError: If non_interactive=True or user cancels.
    """
    if non_interactive:
        raise InteractiveInputError(
            "Page ID required for edit mode. Cannot prompt in non-interactive mode."
        )

    console.print("[bold]Enter the page ID to edit:[/bold]")
    console.print("[dim]Format: 'pageID: 2436039300' or just '2436039300'[/dim]")
    console.print()

    try:
        user_input = Prompt.ask("  [cyan]Page ID[/cyan]")

        # Parse the input - handle both "pageID: 123" and "123" formats
        page_id = _parse_page_id(user_input)

        if not page_id:
            raise InteractiveInputError("Invalid page ID format")

        return page_id

    except KeyboardInterrupt:
        console.print()
        raise InteractiveInputError("User cancelled input")


def confirm_update(title: str, page_id: str) -> bool:
    """Confirm page update with the user.

    Args:
        title: The page title.
        page_id: The page ID.

    Returns:
        True if user confirms, False otherwise.
    """
    console.print()
    console.print("[bold]Page update summary:[/bold]")
    console.print(f"  Title: [green]{title}[/green]")
    console.print(f"  Page ID: [green]{page_id}[/green]")
    console.print(f"  [yellow]Only test results table will be updated[/yellow]")
    console.print()

    try:
        return Confirm.ask("Update this page?", default=True)
    except KeyboardInterrupt:
        console.print()
        return False


def collect_test_result(scenario_name: str, platform: str) -> str:
    """Collect a single test result (Pass/Fail/Incomplete/Skipped) for a scenario.

    Args:
        scenario_name: Name of the test scenario.
        platform: Platform name ("Raptor" or "HM400").

    Returns:
        "P" for Pass, "F" for Fail, "I" for Incomplete, or "-" for Skipped.

    Raises:
        InteractiveInputError: If user cancels input.
    """
    prompt_text = f"  [cyan]{scenario_name}[/cyan] - [bold]{platform}[/bold]"

    while True:
        try:
            result = Prompt.ask(
                prompt_text,
                choices=["P", "F", "I", "-", "Pass", "Fail", "Incomplete", "Skipped", "p", "f", "i", "pass", "fail", "incomplete", "skipped"],
                show_choices=False,
            )
            normalized = result.strip().upper()

            if normalized in ["PASS", "P"]:
                return "P"
            elif normalized in ["FAIL", "F"]:
                return "F"
            elif normalized in ["INCOMPLETE", "I"]:
                return "I"
            elif normalized in ["SKIPPED", "-"]:
                return "-"
            else:
                console.print(
                    "    [yellow]Please enter 'Pass', 'Fail', 'Incomplete', or 'Skipped' (or 'P'/'F'/'I'/'-')[/yellow]"
                )
        except KeyboardInterrupt:
            console.print()
            raise InteractiveInputError("User cancelled input")
