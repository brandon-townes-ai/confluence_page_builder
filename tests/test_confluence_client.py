"""Tests for confluence_client module."""

from unittest.mock import MagicMock, patch

import pytest
from requests.exceptions import ConnectionError, Timeout

from conflow.confluence_client import ConfluenceClient
from conflow.exceptions import (
    AuthenticationError,
    ConfluenceAPIError,
    NetworkError,
    PageNotFoundError,
)
from conflow.models import ConfluenceConfig


@pytest.fixture
def config():
    """Valid config for testing."""
    return ConfluenceConfig(
        base_url="https://test.atlassian.net/wiki",
        email="test@example.com",
        api_token="test-token",
    )


@pytest.fixture
def mock_confluence_api():
    """Mocked Confluence API client."""
    with patch("conflow.confluence_client.Confluence") as mock:
        yield mock


class TestConfluenceClientInit:
    """Tests for ConfluenceClient initialization."""

    def test_init_creates_client(self, config, mock_confluence_api):
        """Test that init creates the underlying client."""
        client = ConfluenceClient(config)

        mock_confluence_api.assert_called_once_with(
            url=config.base_url,
            username=config.email,
            password=config.api_token,
            cloud=True,
        )


class TestValidateCredentials:
    """Tests for validate_credentials method."""

    def test_validate_success(self, config, mock_confluence_api):
        """Test successful credential validation."""
        mock_instance = mock_confluence_api.return_value
        mock_instance.get_all_spaces.return_value = {"results": []}

        client = ConfluenceClient(config)
        result = client.validate_credentials()

        assert result is True

    def test_validate_auth_failure(self, config, mock_confluence_api):
        """Test authentication failure."""
        mock_instance = mock_confluence_api.return_value
        mock_instance.get_all_spaces.side_effect = Exception("401 Unauthorized")

        client = ConfluenceClient(config)
        with pytest.raises(AuthenticationError):
            client.validate_credentials()

    def test_validate_network_error(self, config, mock_confluence_api):
        """Test network error during validation."""
        mock_instance = mock_confluence_api.return_value
        mock_instance.get_all_spaces.side_effect = ConnectionError("Connection failed")

        client = ConfluenceClient(config)
        with pytest.raises(NetworkError):
            client.validate_credentials()

    def test_validate_forbidden_treated_as_success(self, config, mock_confluence_api):
        """Test that 403 Forbidden is treated as successful validation."""
        mock_instance = mock_confluence_api.return_value
        mock_instance.get_all_spaces.side_effect = Exception("403 FORBIDDEN")

        client = ConfluenceClient(config)
        result = client.validate_credentials()

        assert result is True


class TestGetPageById:
    """Tests for get_page_by_id method."""

    def test_get_page_success(self, config, mock_confluence_api):
        """Test successful page fetch."""
        mock_instance = mock_confluence_api.return_value
        mock_instance.get_page_by_id.return_value = {
            "id": "12345",
            "title": "Test Page",
            "body": {"storage": {"value": "<p>Content</p>"}},
            "space": {"key": "TEST"},
        }

        client = ConfluenceClient(config)
        page = client.get_page_by_id("12345")

        assert page.id == "12345"
        assert page.title == "Test Page"
        assert page.body == "<p>Content</p>"
        assert page.space_key == "TEST"

    def test_get_page_not_found(self, config, mock_confluence_api):
        """Test page not found error."""
        mock_instance = mock_confluence_api.return_value
        mock_instance.get_page_by_id.side_effect = Exception("404 Not Found")

        client = ConfluenceClient(config)
        with pytest.raises(PageNotFoundError):
            client.get_page_by_id("99999")

    def test_get_page_returns_none(self, config, mock_confluence_api):
        """Test when API returns None."""
        mock_instance = mock_confluence_api.return_value
        mock_instance.get_page_by_id.return_value = None

        client = ConfluenceClient(config)
        with pytest.raises(PageNotFoundError):
            client.get_page_by_id("99999")


class TestCreatePage:
    """Tests for create_page method."""

    def test_create_page_success(self, config, mock_confluence_api):
        """Test successful page creation."""
        mock_instance = mock_confluence_api.return_value
        mock_instance.create_page.return_value = {
            "id": "99999",
            "title": "New Page",
            "_links": {"webui": "/spaces/TEST/pages/99999"},
        }

        client = ConfluenceClient(config)
        created = client.create_page(
            space_key="TEST",
            parent_id="12345",
            title="New Page",
            body="<p>Content</p>",
        )

        assert created.id == "99999"
        assert created.title == "New Page"
        assert "99999" in created.url

    def test_create_page_auth_failure(self, config, mock_confluence_api):
        """Test authentication failure during create."""
        mock_instance = mock_confluence_api.return_value
        mock_instance.create_page.side_effect = Exception("401 Unauthorized")

        client = ConfluenceClient(config)
        with pytest.raises(AuthenticationError):
            client.create_page(
                space_key="TEST",
                parent_id="12345",
                title="New Page",
                body="<p>Content</p>",
            )

    def test_create_page_timeout(self, config, mock_confluence_api):
        """Test timeout during create."""
        mock_instance = mock_confluence_api.return_value
        mock_instance.create_page.side_effect = Timeout("Request timed out")

        client = ConfluenceClient(config)
        with pytest.raises(NetworkError):
            client.create_page(
                space_key="TEST",
                parent_id="12345",
                title="New Page",
                body="<p>Content</p>",
            )
