"""Conflow."""

import os
from typing import Optional

from dotenv import load_dotenv # type: ignore

from conflow.exceptions import ConfigurationError
from conflow.models import ConfluenceConfig


def load_config(env_file: Optional[str] = None, load_dotenv_file: bool = True) -> ConfluenceConfig:
    """Load and validate configuration from environment variables.

    Args:
        env_file: Optional path to .env file. If None, looks for .env in current directory.
        load_dotenv_file: Whether to load from .env file. Set to False for testing.

    Returns:
        ConfluenceConfig with validated settings.

    Raises:
        ConfigurationError: If required environment variables are missing.
    """
    if load_dotenv_file:
        load_dotenv(env_file)

    base_url = os.environ.get("CONFLUENCE_BASE_URL")
    email = os.environ.get("CONFLUENCE_EMAIL")
    api_token = os.environ.get("CONFLUENCE_API_TOKEN")
    default_parent_page_id = os.environ.get("CONFLUENCE_DEFAULT_PARENT_PAGE_ID")
    default_space_key = os.environ.get("CONFLUENCE_DEFAULT_SPACE_KEY")
    default_template_page_id = os.environ.get("CONFLUENCE_DEFAULT_TEMPLATE_PAGE_ID")

    missing = []
    if not base_url:
        missing.append("CONFLUENCE_BASE_URL")
    if not email:
        missing.append("CONFLUENCE_EMAIL")
    if not api_token:
        missing.append("CONFLUENCE_API_TOKEN")

    if missing:
        raise ConfigurationError(
            f"Missing required environment variables: {', '.join(missing)}. "
            "Set these in your environment or in a .env file."
        )

    return ConfluenceConfig(
        base_url=base_url,
        email=email,
        api_token=api_token,
        default_parent_page_id=default_parent_page_id,
        default_space_key=default_space_key,
        default_template_page_id=default_template_page_id,
    )
