"""Tests for config module."""

import pytest

from conflow.config import load_config
from conflow.exceptions import ConfigurationError


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_config_success(self, mock_env_vars):
        """Test successful config loading with all env vars set."""
        config = load_config(load_dotenv_file=False)

        assert config.base_url == "https://test.atlassian.net/wiki"
        assert config.email == "test@example.com"
        assert config.api_token == "test-token"

    def test_load_config_missing_all(self, clear_env_vars):
        """Test error when all env vars are missing."""
        with pytest.raises(ConfigurationError) as exc_info:
            load_config(load_dotenv_file=False)

        error_msg = str(exc_info.value)
        assert "CONFLUENCE_BASE_URL" in error_msg
        assert "CONFLUENCE_EMAIL" in error_msg
        assert "CONFLUENCE_API_TOKEN" in error_msg

    def test_load_config_missing_base_url(self, mock_env_vars, monkeypatch):
        """Test error when CONFLUENCE_BASE_URL is missing."""
        monkeypatch.delenv("CONFLUENCE_BASE_URL")

        with pytest.raises(ConfigurationError) as exc_info:
            load_config(load_dotenv_file=False)

        assert "CONFLUENCE_BASE_URL" in str(exc_info.value)

    def test_load_config_missing_email(self, mock_env_vars, monkeypatch):
        """Test error when CONFLUENCE_EMAIL is missing."""
        monkeypatch.delenv("CONFLUENCE_EMAIL")

        with pytest.raises(ConfigurationError) as exc_info:
            load_config(load_dotenv_file=False)

        assert "CONFLUENCE_EMAIL" in str(exc_info.value)

    def test_load_config_missing_api_token(self, mock_env_vars, monkeypatch):
        """Test error when CONFLUENCE_API_TOKEN is missing."""
        monkeypatch.delenv("CONFLUENCE_API_TOKEN")

        with pytest.raises(ConfigurationError) as exc_info:
            load_config(load_dotenv_file=False)

        assert "CONFLUENCE_API_TOKEN" in str(exc_info.value)

    def test_load_config_empty_values_treated_as_missing(self, monkeypatch):
        """Test that empty string values are treated as missing."""
        monkeypatch.setenv("CONFLUENCE_BASE_URL", "")
        monkeypatch.setenv("CONFLUENCE_EMAIL", "test@example.com")
        monkeypatch.setenv("CONFLUENCE_API_TOKEN", "token")

        with pytest.raises(ConfigurationError) as exc_info:
            load_config(load_dotenv_file=False)

        assert "CONFLUENCE_BASE_URL" in str(exc_info.value)
