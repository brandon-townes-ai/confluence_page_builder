"""Tests for interactive module."""

from unittest.mock import MagicMock, patch

import pytest

from conflow.exceptions import InteractiveInputError
from conflow.interactive import collect_placeholder_values, confirm_creation


class TestCollectPlaceholderValues:
    """Tests for collect_placeholder_values function."""

    def test_collect_single_value(self):
        """Test collecting a single placeholder value."""
        with patch("conflow.interactive.Prompt") as mock_prompt:
            mock_prompt.ask.return_value = "test value"

            result = collect_placeholder_values(["NAME"])

            assert result == {"NAME": "test value"}
            mock_prompt.ask.assert_called_once()

    def test_collect_multiple_values(self):
        """Test collecting multiple placeholder values."""
        with patch("conflow.interactive.Prompt") as mock_prompt:
            mock_prompt.ask.side_effect = ["Alice", "Bob"]

            result = collect_placeholder_values(["FIRST", "SECOND"])

            assert result == {"FIRST": "Alice", "SECOND": "Bob"}
            assert mock_prompt.ask.call_count == 2

    def test_collect_with_existing_values(self):
        """Test that existing values are not prompted for."""
        with patch("conflow.interactive.Prompt") as mock_prompt:
            mock_prompt.ask.return_value = "new value"

            result = collect_placeholder_values(
                ["EXISTING", "NEW"],
                existing_values={"EXISTING": "preset"},
            )

            assert result == {"EXISTING": "preset", "NEW": "new value"}
            assert mock_prompt.ask.call_count == 1

    def test_collect_empty_value_confirmed(self):
        """Test allowing empty value when user confirms."""
        with patch("conflow.interactive.Prompt") as mock_prompt:
            with patch("conflow.interactive.Confirm") as mock_confirm:
                mock_prompt.ask.return_value = ""
                mock_confirm.ask.return_value = True

                result = collect_placeholder_values(["NAME"])

                assert result == {"NAME": ""}

    def test_collect_empty_value_cancelled(self):
        """Test cancelling when empty value is not confirmed."""
        with patch("conflow.interactive.Prompt") as mock_prompt:
            with patch("conflow.interactive.Confirm") as mock_confirm:
                mock_prompt.ask.return_value = ""
                mock_confirm.ask.return_value = False

                with pytest.raises(InteractiveInputError):
                    collect_placeholder_values(["NAME"])

    def test_collect_keyboard_interrupt(self):
        """Test handling Ctrl+C."""
        with patch("conflow.interactive.Prompt") as mock_prompt:
            mock_prompt.ask.side_effect = KeyboardInterrupt()

            with pytest.raises(InteractiveInputError):
                collect_placeholder_values(["NAME"])


class TestConfirmCreation:
    """Tests for confirm_creation function."""

    def test_confirm_yes(self):
        """Test user confirms creation."""
        with patch("conflow.interactive.Confirm") as mock_confirm:
            mock_confirm.ask.return_value = True

            result = confirm_creation("Test Page", "TEST", "12345")

            assert result is True

    def test_confirm_no(self):
        """Test user declines creation."""
        with patch("conflow.interactive.Confirm") as mock_confirm:
            mock_confirm.ask.return_value = False

            result = confirm_creation("Test Page", "TEST", "12345")

            assert result is False

    def test_confirm_keyboard_interrupt(self):
        """Test handling Ctrl+C during confirmation."""
        with patch("conflow.interactive.Confirm") as mock_confirm:
            mock_confirm.ask.side_effect = KeyboardInterrupt()

            result = confirm_creation("Test Page", "TEST", "12345")

            assert result is False
