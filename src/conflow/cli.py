"""Conflow."""

import logging
import sys

import click
from rich.console import Console

from conflow.config import load_config
from conflow.confluence_client import ConfluenceClient
from conflow.exceptions import ConflowError, InteractiveInputError
from conflow.interactive import collect_placeholder_values, confirm_creation
from conflow.template_processor import extract_placeholders, substitute_placeholders

DEFAULT_TEMPLATE_PAGE_ID = "2129789334"

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


@cli.command()
@click.option("--title", required=True, help="Title of the new page")
@click.option("--parent-page-id", required=True, help="ID of the parent page")
@click.option("--space-key", required=True, help="Confluence space key")
@click.option(
    "--template-page-id",
    default=DEFAULT_TEMPLATE_PAGE_ID,
    help=f"Template page ID (default: {DEFAULT_TEMPLATE_PAGE_ID})",
)
@click.option(
    "--non-interactive",
    is_flag=True,
    default=False,
    help="Fail if any placeholders need user input",
)
@click.pass_context
def new(
    ctx,
    title: str,
    parent_page_id: str,
    space_key: str,
    template_page_id: str,
    non_interactive: bool,
):
    """Create a new Confluence page from a template."""
    verbose = ctx.obj.get('verbose', False)

    try:
        # Load configuration
        console.print("[dim]Loading configuration...[/dim]")
        logger.debug("Loading configuration from environment")
        config = load_config()
        logger.debug(f"Config loaded: base_url={config.base_url}, email={config.email}")

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

        # Collect placeholder values
        if placeholders and non_interactive:
            logger.warning("Non-interactive mode but placeholders found")
            console.print(
                "[red]Error:[/red] Template has placeholders but --non-interactive "
                "was specified. Provide placeholder values or run interactively."
            )
            sys.exit(1)

        values = {}
        if placeholders:
            logger.debug("Collecting placeholder values from user")
            values = collect_placeholder_values(placeholders)
            logger.debug(f"Collected values for {len(values)} placeholders")

        # Substitute placeholders
        logger.debug("Substituting placeholders in template body")
        body = substitute_placeholders(template.body, values)

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
