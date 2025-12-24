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

    def test_placeholder_command_line(self, runner):
        """Test providing placeholder values via command line."""
        mock_config = MagicMock()
        mock_client = MagicMock()
        mock_client.get_page_by_id.return_value = PageContent(
            id="999",
            title="Template",
            body="<p>Hello {{NAME}} from {{LOCATION}}!</p>",
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
                        "-p", "NAME=Alice",
                        "-p", "LOCATION=Wonderland",
                    ])

                    assert result.exit_code == 0
                    # Verify the page was created with substituted values
                    mock_client.create_page.assert_called_once()
                    call_args = mock_client.create_page.call_args
                    assert "Alice" in call_args.kwargs["body"]
                    assert "Wonderland" in call_args.kwargs["body"]

    def test_placeholder_non_interactive_with_all_values(self, runner):
        """Test non-interactive mode with all placeholders provided."""
        mock_config = MagicMock()
        mock_client = MagicMock()
        mock_client.get_page_by_id.return_value = PageContent(
            id="999",
            title="Template",
            body="<p>{{NAME}} {{VALUE}}</p>",
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
                    "--placeholder", "NAME=Test",
                    "--placeholder", "VALUE=123",
                    "--non-interactive",
                ])

                assert result.exit_code == 0
                assert "successfully" in result.output.lower()

    def test_placeholder_non_interactive_missing_values(self, runner):
        """Test non-interactive mode with missing placeholder values."""
        mock_config = MagicMock()
        mock_client = MagicMock()
        mock_client.get_page_by_id.return_value = PageContent(
            id="999",
            title="Template",
            body="<p>{{NAME}} {{VALUE}}</p>",
            space_key="TEST",
        )

        with patch("conflow.cli.load_config", return_value=mock_config):
            with patch("conflow.cli.ConfluenceClient", return_value=mock_client):
                result = runner.invoke(cli, [
                    "new",
                    "--title", "New Page",
                    "--parent-page-id", "123",
                    "--space-key", "TEST",
                    "--placeholder", "NAME=Test",
                    "--non-interactive",
                ])

                assert result.exit_code == 1
                assert "Missing values for placeholders" in result.output
                assert "VALUE" in result.output

    def test_date_placeholder_auto_populated(self, runner):
        """Test DATE placeholder is automatically populated with current date."""
        mock_config = MagicMock()
        mock_client = MagicMock()
        mock_client.get_page_by_id.return_value = PageContent(
            id="999",
            title="Template",
            body="<p>Date: {{DATE}}</p>",
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
                # Verify the page was created with a date
                mock_client.create_page.assert_called_once()
                call_args = mock_client.create_page.call_args
                body = call_args.kwargs["body"]
                # Check that DATE placeholder was replaced (not still {{DATE}})
                assert "{{DATE}}" not in body
                # Check that body contains a date-like string (month abbreviation)
                assert any(month in body for month in ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                                                        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])

    def test_date_placeholder_can_be_overridden(self, runner):
        """Test DATE placeholder can be overridden via command line."""
        mock_config = MagicMock()
        mock_client = MagicMock()
        mock_client.get_page_by_id.return_value = PageContent(
            id="999",
            title="Template",
            body="<p>Date: {{DATE}}</p>",
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
                    "--placeholder", "DATE=Custom Date",
                    "--non-interactive",
                ])

                assert result.exit_code == 0
                # Verify the page was created with custom date
                mock_client.create_page.assert_called_once()
                call_args = mock_client.create_page.call_args
                body = call_args.kwargs["body"]
                assert "Custom Date" in body

    def test_date_placeholder_case_insensitive(self, runner):
        """Test Date placeholder works with different casing (Date, date, DATE)."""
        mock_config = MagicMock()
        mock_client = MagicMock()
        mock_client.get_page_by_id.return_value = PageContent(
            id="999",
            title="Template",
            body="<p>Date: {{Date}}</p>",
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
                # Verify the page was created with a date
                mock_client.create_page.assert_called_once()
                call_args = mock_client.create_page.call_args
                body = call_args.kwargs["body"]
                # Check that Date placeholder was replaced (not still {{Date}})
                assert "{{Date}}" not in body
                # Check that body contains a date-like string
                assert any(month in body for month in ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                                                        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])


class TestTestResultsFlag:
    """Tests for --test-results flag functionality."""

    def test_test_results_flag_processes_table(self, runner):
        """Test --test-results flag processes the test table."""
        mock_config = MagicMock()
        mock_client = MagicMock()

        # Template with test table
        mock_client.get_page_by_id.return_value = PageContent(
            id="999",
            title="Template",
            body="""
            <h2>Test</h2>
            <table>
              <tbody>
                <tr><th>Scenario</th><th>Test ID</th><th>Variation</th><th>Raptor</th><th>HM400</th></tr>
                <tr>
                  <td><p>Load Haul</p></td>
                  <td><p>TC-001</p></td>
                  <td><p>N/A</p></td>
                  <td><p>I</p></td>
                  <td><p>I</p></td>
                </tr>
              </tbody>
            </table>
            """,
            space_key="TEST",
        )
        mock_client.create_page.return_value = CreatedPage(
            id="888",
            title="New Page",
            url="https://test.atlassian.net/wiki/spaces/TEST/pages/888",
        )

        with patch("conflow.cli.load_config", return_value=mock_config):
            with patch("conflow.cli.ConfluenceClient", return_value=mock_client):
                with patch("conflow.cli.process_test_results") as mock_process:
                    with patch("conflow.cli.confirm_creation", return_value=True):
                        # Mock process_test_results to return modified HTML
                        mock_process.return_value = "<h2>Test</h2><table><tbody><tr><td>P</td></tr></tbody></table>"

                        result = runner.invoke(cli, [
                            "new",
                            "--title", "New Page",
                            "--parent-page-id", "123",
                            "--space-key", "TEST",
                            "--test-results",
                        ])

                        assert result.exit_code == 0
                        # Verify process_test_results was called
                        mock_process.assert_called_once()
                        # Check that non_interactive=False was passed
                        call_args = mock_process.call_args
                        assert call_args[0][1] is False  # Second positional arg is non_interactive

    def test_test_results_with_non_interactive_fails(self, runner):
        """Test --test-results with --non-interactive fails when table has 'I'."""
        mock_config = MagicMock()
        mock_client = MagicMock()

        mock_client.get_page_by_id.return_value = PageContent(
            id="999",
            title="Template",
            body="""
            <h2>Test</h2>
            <table>
              <tbody>
                <tr><th>Scenario</th><th>Test ID</th><th>Variation</th><th>Raptor</th><th>HM400</th></tr>
                <tr>
                  <td><p>Test</p></td>
                  <td><p>TC-001</p></td>
                  <td><p>N/A</p></td>
                  <td><p>I</p></td>
                  <td><p>I</p></td>
                </tr>
              </tbody>
            </table>
            """,
            space_key="TEST",
        )

        with patch("conflow.cli.load_config", return_value=mock_config):
            with patch("conflow.cli.ConfluenceClient", return_value=mock_client):
                result = runner.invoke(cli, [
                    "new",
                    "--title", "New Page",
                    "--parent-page-id", "123",
                    "--space-key", "TEST",
                    "--test-results",
                    "--non-interactive",
                ])

                assert result.exit_code != 0
                assert "incomplete entries" in result.output.lower()

    def test_test_results_skipped_when_flag_absent(self, runner):
        """Test test results processing is skipped when flag not provided."""
        mock_config = MagicMock()
        mock_client = MagicMock()

        mock_client.get_page_by_id.return_value = PageContent(
            id="999",
            title="Template",
            body="<h2>Test</h2><table><tbody><tr><td>I</td></tr></tbody></table>",
            space_key="TEST",
        )
        mock_client.create_page.return_value = CreatedPage(
            id="888",
            title="New Page",
            url="https://test.atlassian.net/wiki/spaces/TEST/pages/888",
        )

        with patch("conflow.cli.load_config", return_value=mock_config):
            with patch("conflow.cli.ConfluenceClient", return_value=mock_client):
                with patch("conflow.cli.process_test_results") as mock_process:
                    with patch("conflow.cli.confirm_creation", return_value=True):
                        result = runner.invoke(cli, [
                            "new",
                            "--title", "New Page",
                            "--parent-page-id", "123",
                            "--space-key", "TEST",
                            # Note: no --test-results flag
                        ])

                        assert result.exit_code == 0
                        # Verify process_test_results was NOT called
                        mock_process.assert_not_called()
