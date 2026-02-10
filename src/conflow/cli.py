"""Conflow."""

import logging
import sys
from datetime import datetime

import click
from rich.console import Console

from conflow.config import load_config
from conflow.confluence_client import ConfluenceClient
from conflow.documentation_table import process_documentation_table
from conflow.exceptions import ConflowError, InteractiveInputError
from conflow.interactive import (
    collect_placeholder_values,
    confirm_creation,
    confirm_update,
    prompt_for_page_id,
)
from conflow.template_processor import extract_placeholders, substitute_placeholders
from conflow.test_results import process_test_results

DEFAULT_TEMPLATE_PAGE_ID = "2517172967"

console = Console()
logger = logging.getLogger(__name__)


@click.group()
@click.version_option()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.pass_context
def cli(ctx, verbose):
    """Conflow - Create Confluence pages from templates."""
    # Setup logging
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose

    if verbose:
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        logger.debug("Verbose logging enabled")
    else:
        logging.basicConfig(level=logging.WARNING)


def _handle_edit_mode(ctx, non_interactive: bool, verbose: bool):
    """Handle edit mode workflow for updating existing pages.

    Args:
        ctx: Click context object.
        non_interactive: Whether to fail on interactive prompts.
        verbose: Whether verbose logging is enabled.
    """
    try:
        # Load configuration
        console.print("[dim]Loading configuration...[/dim]")
        logger.debug("Loading configuration from environment")
        config = load_config()
        logger.debug(f"Config loaded: base_url={config.base_url}, email={config.email}")

        # Initialize client
        logger.debug("Initializing Confluence client")
        client = ConfluenceClient(config)

        # Validate credentials
        console.print("[dim]Validating credentials...[/dim]")
        logger.debug("Validating credentials")
        try:
            client.validate_credentials()
            logger.debug("Credentials validated successfully")
        except Exception as e:
            logger.error(f"Credential validation failed: {e}", exc_info=verbose)
            raise

        # Prompt for page ID
        console.print()
        page_id = prompt_for_page_id(non_interactive)
        logger.debug(f"Page ID to edit: {page_id}")

        # Fetch existing page
        console.print(f"[dim]Fetching page {page_id}...[/dim]")
        logger.debug(f"Fetching page ID: {page_id}")
        try:
            existing_page = client.get_page_by_id(page_id)
            logger.debug(f"Page fetched: title={existing_page.title}, space={existing_page.space_key}")
        except Exception as e:
            logger.error(f"Failed to fetch page: {e}", exc_info=verbose)
            raise

        # Process test results (only step that modifies content)
        console.print("[dim]Processing test results table...[/dim]")
        logger.debug("Processing test results table")
        try:
            updated_body = process_test_results(existing_page.body, non_interactive)
        except InteractiveInputError:
            raise
        except Exception as e:
            logger.error(f"Failed to process test results: {e}", exc_info=verbose)
            raise

        # Confirm update
        if not non_interactive:
            logger.debug("Requesting user confirmation for page update")
            if not confirm_update(existing_page.title, page_id):
                logger.info("User cancelled page update")
                console.print("[yellow]Page update cancelled.[/yellow]")
                sys.exit(0)

        # Update page
        console.print("[dim]Updating page...[/dim]")
        logger.debug(f"Updating page: id={page_id}, title={existing_page.title}")
        try:
            updated_page = client.update_page(
                page_id=page_id,
                title=existing_page.title,
                body=updated_body,
                space_key=existing_page.space_key,
            )
            logger.debug(f"Page updated successfully: id={updated_page.id}, url={updated_page.url}")
        except Exception as e:
            logger.error(f"Failed to update page: {e}", exc_info=verbose)
            raise

        console.print()
        console.print("[bold green]Page updated successfully![/bold green]")
        console.print(f"  Title: {updated_page.title}")
        console.print(f"  URL: [link={updated_page.url}]{updated_page.url}[/link]")

    except InteractiveInputError as e:
        logger.debug(f"Interactive input error: {e.message}")
        console.print(f"[yellow]{e.message}[/yellow]")
        sys.exit(e.exit_code)
    except ConflowError as e:
        logger.error(f"Conflow error: {e.message}", exc_info=verbose)
        console.print(f"[red]Error:[/red] {e.message}")
        sys.exit(e.exit_code)
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        console.print(f"[red]Unexpected error:[/red] {e}")
        if verbose:
            console.print("\n[dim]Full traceback logged above[/dim]")
        sys.exit(99)


@cli.command()
@click.option(
    "--test-results",
    is_flag=True,
    default=True,
    help="Interactively fill in test results table (P/F/I/-)",
)
@click.option(
    "--non-interactive",
    is_flag=True,
    default=False,
    help="Fail if any test results need user input",
)
@click.pass_context
def edit(ctx, test_results: bool, non_interactive: bool):
    """Edit an existing Confluence page's test results."""
    verbose = ctx.obj.get('verbose', False)

    if not test_results:
        console.print("[yellow]Note:[/yellow] Edit mode currently only supports updating test results.")
        console.print("The --test-results flag will be enabled automatically.")

    _handle_edit_mode(ctx, non_interactive, verbose)


@cli.command()
@click.option("--title", required=True, help="Title of the new page")
@click.option("--parent-page-id", help="ID of the parent page (uses CONFLUENCE_DEFAULT_PARENT_PAGE_ID if not provided)")
@click.option("--space-key", help="Confluence space key (uses CONFLUENCE_DEFAULT_SPACE_KEY if not provided)")
@click.option(
    "--template-page-id",
    default=DEFAULT_TEMPLATE_PAGE_ID,
    help=f"Template page ID (default: {DEFAULT_TEMPLATE_PAGE_ID})",
)
@click.option(
    "--placeholder",
    "-p",
    multiple=True,
    help='Placeholder value in format KEY=VALUE (e.g., -p PROJECT_NAME="My Project")',
)
@click.option(
    "--non-interactive",
    is_flag=True,
    default=False,
    help="Fail if any placeholders need user input",
)
@click.option(
    "--test-results",
    is_flag=True,
    default=False,
    help="Interactively fill in test results table (P/F/I/-)",
)
@click.pass_context
def new(
    ctx,
    title: str,
    parent_page_id: str,
    space_key: str,
    template_page_id: str,
    placeholder: tuple,
    non_interactive: bool,
    test_results: bool,
):
    """Create a new Confluence page from a template."""
    verbose = ctx.obj.get('verbose', False)

    try:
        # Load configuration first to get defaults
        console.print("[dim]Loading configuration...[/dim]")
        logger.debug("Loading configuration from environment")
        config = load_config()
        logger.debug(f"Config loaded: base_url={config.base_url}, email={config.email}")

        # Use config defaults if flags not provided
        if not parent_page_id:
            parent_page_id = config.default_parent_page_id
            if parent_page_id:
                logger.debug(f"Using default parent page ID from config: {parent_page_id}")

        if not space_key:
            space_key = config.default_space_key
            if space_key:
                logger.debug(f"Using default space key from config: {space_key}")

        if not template_page_id:
            template_page_id = config.default_template_page_id or DEFAULT_TEMPLATE_PAGE_ID
            if template_page_id:
                logger.debug(f"Using default template page ID from config: {template_page_id}")

        # Validate required values (either from flags or config)
        if not parent_page_id:
            console.print("[red]Error:[/red] --parent-page-id is required (or set CONFLUENCE_DEFAULT_PARENT_PAGE_ID)")
            sys.exit(1)
        if not space_key:
            console.print("[red]Error:[/red] --space-key is required (or set CONFLUENCE_DEFAULT_SPACE_KEY)")
            sys.exit(1)

        # Parse placeholder arguments
        placeholder_values = {}
        for p in placeholder:
            if "=" not in p:
                console.print(f"[red]Error:[/red] Invalid placeholder format: '{p}'. Use KEY=VALUE")
                sys.exit(1)
            key, value = p.split("=", 1)
            key = key.strip()
            value = value.strip()
            placeholder_values[key] = value
            logger.debug(f"Command-line placeholder: {key}={value}")

        # Initialize client
        logger.debug("Initializing Confluence client")
        client = ConfluenceClient(config)

        # Validate credentials (403 errors are treated as success)
        console.print("[dim]Validating credentials...[/dim]")
        logger.debug("Validating credentials")
        try:
            client.validate_credentials()
            logger.debug("Credentials validated successfully")
        except Exception as e:
            logger.error(f"Credential validation failed: {e}", exc_info=verbose)
            raise

        # Fetch template
        console.print(f"[dim]Fetching template page {template_page_id}...[/dim]")
        logger.debug(f"Fetching template page ID: {template_page_id}")
        try:
            template = client.get_page_by_id(template_page_id)
            logger.debug(f"Template fetched: title={template.title}, space={template.space_key}")
        except Exception as e:
            logger.error(f"Failed to fetch template page: {e}", exc_info=verbose)
            raise

        # Extract placeholders
        logger.debug("Extracting placeholders from template")
        placeholders = extract_placeholders(template.body)
        logger.debug(f"Found {len(placeholders)} placeholders: {placeholders}")

        if placeholders:
            console.print(
                f"[dim]Found {len(placeholders)} placeholder(s): "
                f"{', '.join(placeholders)}[/dim]"
            )

        # Automatically populate DATE placeholder with current date
        # Check for any case variation of DATE (DATE, Date, date, etc.)
        date_placeholder = None
        for placeholder in placeholders:
            if placeholder.upper() == "DATE" and placeholder not in placeholder_values:
                date_placeholder = placeholder
                break

        if date_placeholder:
            current_date = datetime.now().strftime("%b %d, %Y")
            placeholder_values[date_placeholder] = current_date
            logger.debug(f"Auto-populated {date_placeholder} placeholder: {current_date}")

        # Check which placeholders still need values
        missing_placeholders = [p for p in placeholders if p not in placeholder_values]

        # Collect placeholder values
        if missing_placeholders and non_interactive:
            logger.warning(f"Non-interactive mode but {len(missing_placeholders)} placeholder(s) missing")
            console.print(
                f"[red]Error:[/red] Missing values for placeholders: {', '.join(missing_placeholders)}. "
                "Use --placeholder KEY=VALUE or run in interactive mode."
            )
            sys.exit(1)

        values = placeholder_values.copy()
        if missing_placeholders:
            logger.debug(f"Collecting {len(missing_placeholders)} placeholder values from user")
            interactive_values = collect_placeholder_values(missing_placeholders, existing_values=placeholder_values)
            values.update(interactive_values)
            logger.debug(f"Collected values for {len(interactive_values)} placeholders")
        elif placeholders:
            logger.debug(f"All {len(placeholders)} placeholders provided via command line")

        # Substitute placeholders
        logger.debug("Substituting placeholders in template body")
        body = substitute_placeholders(template.body, values)

        # Process Documentation table to auto-fill Date field
        console.print("[dim]Processing Documentation table...[/dim]")
        logger.debug("Processing Documentation table")
        body = process_documentation_table(body)

        # Process test results if enabled
        if test_results:
            console.print("[dim]Processing test results table...[/dim]")
            logger.debug("Processing test results table")
            try:
                body = process_test_results(body, non_interactive)
            except InteractiveInputError:
                raise
            except Exception as e:
                logger.error(f"Failed to process test results: {e}", exc_info=verbose)
                raise

        # Confirm creation
        if not non_interactive:
            logger.debug("Requesting user confirmation for page creation")
            if not confirm_creation(title, space_key, parent_page_id):
                logger.info("User cancelled page creation")
                console.print("[yellow]Page creation cancelled.[/yellow]")
                sys.exit(0)

        # Create page
        console.print("[dim]Creating page...[/dim]")
        logger.debug(f"Creating page: title={title}, parent={parent_page_id}, space={space_key}")
        try:
            created_page = client.create_page(
                space_key=space_key,
                parent_id=parent_page_id,
                title=title,
                body=body,
            )
            logger.debug(f"Page created successfully: id={created_page.id}, url={created_page.url}")
        except Exception as e:
            logger.error(f"Failed to create page: {e}", exc_info=verbose)
            raise

        console.print()
        console.print("[bold green]Page created successfully![/bold green]")
        console.print(f"  Title: {created_page.title}")
        console.print(f"  URL: [link={created_page.url}]{created_page.url}[/link]")

    except InteractiveInputError as e:
        logger.debug(f"Interactive input error: {e.message}")
        console.print(f"[yellow]{e.message}[/yellow]")
        sys.exit(e.exit_code)
    except ConflowError as e:
        logger.error(f"Conflow error: {e.message}", exc_info=verbose)
        console.print(f"[red]Error:[/red] {e.message}")
        sys.exit(e.exit_code)
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        console.print(f"[red]Unexpected error:[/red] {e}")
        if verbose:
            console.print("\n[dim]Full traceback logged above[/dim]")
        sys.exit(99)


if __name__ == "__main__":
    cli()
