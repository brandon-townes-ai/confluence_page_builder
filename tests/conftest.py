"""Conflow tests."""

import os
from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from conflow.models import ConfluenceConfig, PageContent


@pytest.fixture
def cli_runner():
    """Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set mock environment variables."""
    monkeypatch.setenv("CONFLUENCE_BASE_URL", "https://test.atlassian.net/wiki")
    monkeypatch.setenv("CONFLUENCE_EMAIL", "test@example.com")
    monkeypatch.setenv("CONFLUENCE_API_TOKEN", "test-token")


@pytest.fixture
def clear_env_vars(monkeypatch):
    """Clear Confluence environment variables."""
    monkeypatch.delenv("CONFLUENCE_BASE_URL", raising=False)
    monkeypatch.delenv("CONFLUENCE_EMAIL", raising=False)
    monkeypatch.delenv("CONFLUENCE_API_TOKEN", raising=False)


@pytest.fixture
def mock_confluence_config():
    """Valid ConfluenceConfig for testing."""
    return ConfluenceConfig(
        base_url="https://test.atlassian.net/wiki",
        email="test@example.com",
        api_token="test-token",
    )


@pytest.fixture
def mock_page_content():
    """Sample page content with placeholders."""
    return PageContent(
        id="12345",
        title="Test Template",
        body="""
        <h1>Project: {{PROJECT_NAME}}</h1>
        <p>Owner: {{OWNER_NAME}}</p>
        <p>Description: {{DESCRIPTION}}</p>
        <p>Project {{PROJECT_NAME}} is owned by {{OWNER_NAME}}.</p>
        """,
        space_key="TEST",
    )


@pytest.fixture
def mock_page_content_no_placeholders():
    """Sample page content without placeholders."""
    return PageContent(
        id="12345",
        title="Test Template",
        body="<h1>Static Content</h1><p>No placeholders here.</p>",
        space_key="TEST",
    )


@pytest.fixture
def mock_confluence_client(mock_confluence_config, mock_page_content):
    """Mocked ConfluenceClient."""
    from conflow.confluence_client import ConfluenceClient
    from conflow.models import CreatedPage

    client = MagicMock(spec=ConfluenceClient)
    client.config = mock_confluence_config
    client.validate_credentials.return_value = True
    client.get_page_by_id.return_value = mock_page_content
    client.create_page.return_value = CreatedPage(
        id="99999",
        title="New Test Page",
        url="https://test.atlassian.net/wiki/spaces/TEST/pages/99999",
    )
    return client
