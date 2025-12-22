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
