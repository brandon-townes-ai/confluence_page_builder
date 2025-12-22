"""Tests for CLI module."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from conflow.cli import cli
from conflow.exceptions import ConfigurationError, PageNotFoundError
from conflow.models import CreatedPage, PageContent


@pytest.fixture
def runner():
    """Click CLI test runner."""
    return CliRunner()


class TestCliHelp:
    """Tests for CLI help commands."""

    def test_main_help(self, runner):
        """Test main CLI help."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Conflow" in result.output
        assert "new" in result.output

    def test_new_help(self, runner):
        """Test 'new' command help."""
        result = runner.invoke(cli, ["new", "--help"])
        assert result.exit_code == 0
        assert "--title" in result.output
        assert "--parent-page-id" in result.output
        assert "--space-key" in result.output
        assert "--template-page-id" in result.output
        assert "--non-interactive" in result.output


class TestNewCommand:
    """Tests for 'new' command."""

    def test_missing_required_options(self, runner):
        """Test error when required options are missing."""
        result = runner.invoke(cli, ["new"])
        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()

    def test_config_error(self, runner):
        """Test error when config is missing."""
        with patch("conflow.cli.load_config") as mock_load:
            mock_load.side_effect = ConfigurationError("Missing CONFLUENCE_API_TOKEN")

            result = runner.invoke(cli, [
                "new",
                "--title", "Test",
                "--parent-page-id", "123",
                "--space-key", "TEST",
            ])

            assert result.exit_code == 1
            assert "CONFLUENCE_API_TOKEN" in result.output

    def test_successful_page_creation(self, runner):
        """Test successful page creation."""
        mock_config = MagicMock()
        mock_client = MagicMock()
        mock_client.get_page_by_id.return_value = PageContent(
            id="999",
            title="Template",
            body="<p>Hello {{NAME}}!</p>",
            space_key="TEST",
        )
        mock_client.create_page.return_value = CreatedPage(
            id="888",
            title="New Page",
            url="https://test.atlassian.net/wiki/spaces/TEST/pages/888",
        )

        with patch("conflow.cli.load_config", return_value=mock_config):
            with patch("conflow.cli.ConfluenceClient", return_value=mock_client):
                with patch("conflow.cli.collect_placeholder_values") as mock_collect:
                    with patch("conflow.cli.confirm_creation", return_value=True):
                        mock_collect.return_value = {"NAME": "World"}

                        result = runner.invoke(cli, [
                            "new",
                            "--title", "New Page",
                            "--parent-page-id", "123",
                            "--space-key", "TEST",
                        ])

                        assert result.exit_code == 0
                        assert "successfully" in result.output.lower()

    def test_page_creation_cancelled(self, runner):
        """Test page creation when user cancels."""
        mock_config = MagicMock()
        mock_client = MagicMock()
        mock_client.get_page_by_id.return_value = PageContent(
            id="999",
            title="Template",
            body="<p>No placeholders</p>",
            space_key="TEST",
        )

        with patch("conflow.cli.load_config", return_value=mock_config):
            with patch("conflow.cli.ConfluenceClient", return_value=mock_client):
                with patch("conflow.cli.confirm_creation", return_value=False):
                    result = runner.invoke(cli, [
                        "new",
                        "--title", "New Page",
                        "--parent-page-id", "123",
                        "--space-key", "TEST",
                    ])

                    assert result.exit_code == 0
                    assert "cancelled" in result.output.lower()

    def test_non_interactive_with_placeholders(self, runner):
        """Test non-interactive mode fails when placeholders exist."""
        mock_config = MagicMock()
        mock_client = MagicMock()
        mock_client.get_page_by_id.return_value = PageContent(
            id="999",
            title="Template",
            body="<p>Hello {{NAME}}!</p>",
            space_key="TEST",
        )

        with patch("conflow.cli.load_config", return_value=mock_config):
            with patch("conflow.cli.ConfluenceClient", return_value=mock_client):
                result = runner.invoke(cli, [
                    "new",
                    "--title", "New Page",
                    "--parent-page-id", "123",
                    "--space-key", "TEST",
                    "--non-interactive",
                ])

                assert result.exit_code == 1
                assert "placeholder" in result.output.lower()

    def test_non_interactive_without_placeholders(self, runner):
        """Test non-interactive mode succeeds without placeholders."""
        mock_config = MagicMock()
        mock_client = MagicMock()
        mock_client.get_page_by_id.return_value = PageContent(
            id="999",
            title="Template",
            body="<p>Static content</p>",
            space_key="TEST",
        )
        mock_client.create_page.return_value = CreatedPage(
            id="888",
            title="New Page",
            url="https://test.atlassian.net/wiki/spaces/TEST/pages/888",
        )

        with patch("conflow.cli.load_config", return_value=mock_config):
            with patch("conflow.cli.ConfluenceClient", return_value=mock_client):
                result = runner.invoke(cli, [
                    "new",
                    "--title", "New Page",
                    "--parent-page-id", "123",
                    "--space-key", "TEST",
                    "--non-interactive",
                ])

                assert result.exit_code == 0
                assert "successfully" in result.output.lower()

    def test_template_not_found(self, runner):
        """Test error when template page is not found."""
        mock_config = MagicMock()
        mock_client = MagicMock()
        mock_client.get_page_by_id.side_effect = PageNotFoundError("Page not found")

        with patch("conflow.cli.load_config", return_value=mock_config):
            with patch("conflow.cli.ConfluenceClient", return_value=mock_client):
                result = runner.invoke(cli, [
                    "new",
                    "--title", "New Page",
                    "--parent-page-id", "123",
                    "--space-key", "TEST",
                ])

                assert result.exit_code == 3
                assert "not found" in result.output.lower()

    def test_custom_template_id(self, runner):
        """Test using a custom template page ID."""
        mock_config = MagicMock()
        mock_client = MagicMock()
        mock_client.get_page_by_id.return_value = PageContent(
            id="custom",
            title="Custom Template",
            body="<p>Custom content</p>",
            space_key="TEST",
        )
        mock_client.create_page.return_value = CreatedPage(
            id="888",
            title="New Page",
            url="https://test.atlassian.net/wiki/spaces/TEST/pages/888",
        )

        with patch("conflow.cli.load_config", return_value=mock_config):
            with patch("conflow.cli.ConfluenceClient", return_value=mock_client):
                with patch("conflow.cli.confirm_creation", return_value=True):
                    result = runner.invoke(cli, [
                        "new",
                        "--title", "New Page",
                        "--parent-page-id", "123",
                        "--space-key", "TEST",
                        "--template-page-id", "custom-id",
                    ])

                    mock_client.get_page_by_id.assert_called_with("custom-id")
