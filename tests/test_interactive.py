"""Tests for interactive module."""

from unittest.mock import MagicMock, patch

import pytest

from conflow.exceptions import InteractiveInputError
from conflow.interactive import (
    collect_placeholder_values,
    collect_test_result,
    confirm_creation,
)


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


class TestCollectTestResult:
    """Tests for collect_test_result function."""

    def test_accepts_pass(self):
        """Test accepts 'Pass' as valid input."""
        with patch("conflow.interactive.Prompt") as mock_prompt:
            mock_prompt.ask.return_value = "Pass"

            result = collect_test_result("Test Scenario", "Raptor")

            assert result == "P"

    def test_accepts_p(self):
        """Test accepts 'P' as valid input."""
        with patch("conflow.interactive.Prompt") as mock_prompt:
            mock_prompt.ask.return_value = "P"

            result = collect_test_result("Test Scenario", "Raptor")

            assert result == "P"

    def test_accepts_fail(self):
        """Test accepts 'Fail' as valid input."""
        with patch("conflow.interactive.Prompt") as mock_prompt:
            mock_prompt.ask.return_value = "Fail"

            result = collect_test_result("Test Scenario", "HM400")

            assert result == "F"

    def test_accepts_f(self):
        """Test accepts 'F' as valid input."""
        with patch("conflow.interactive.Prompt") as mock_prompt:
            mock_prompt.ask.return_value = "F"

            result = collect_test_result("Test Scenario", "HM400")

            assert result == "F"

    def test_accepts_incomplete(self):
        """Test accepts 'Incomplete' as valid input."""
        with patch("conflow.interactive.Prompt") as mock_prompt:
            mock_prompt.ask.return_value = "Incomplete"

            result = collect_test_result("Test Scenario", "Raptor")

            assert result == "I"

    def test_accepts_i(self):
        """Test accepts 'I' as valid input."""
        with patch("conflow.interactive.Prompt") as mock_prompt:
            mock_prompt.ask.return_value = "I"

            result = collect_test_result("Test Scenario", "HM400")

            assert result == "I"

    def test_case_insensitive(self):
        """Test input is case insensitive."""
        with patch("conflow.interactive.Prompt") as mock_prompt:
            # Test lowercase pass
            mock_prompt.ask.return_value = "pass"
            result = collect_test_result("Test", "Raptor")
            assert result == "P"

            # Test mixed case fail
            mock_prompt.ask.return_value = "fAiL"
            result = collect_test_result("Test", "Raptor")
            assert result == "F"

            # Test lowercase incomplete
            mock_prompt.ask.return_value = "incomplete"
            result = collect_test_result("Test", "Raptor")
            assert result == "I"

    def test_reprompts_on_invalid_input(self):
        """Test reprompts when invalid input is provided."""
        with patch("conflow.interactive.Prompt") as mock_prompt:
            # First invalid, then valid
            mock_prompt.ask.side_effect = ["invalid", "Pass"]

            result = collect_test_result("Test Scenario", "Raptor")

            assert result == "P"
            assert mock_prompt.ask.call_count == 2

    def test_keyboard_interrupt_raises_error(self):
        """Test Ctrl+C raises InteractiveInputError."""
        with patch("conflow.interactive.Prompt") as mock_prompt:
            mock_prompt.ask.side_effect = KeyboardInterrupt()

            with pytest.raises(InteractiveInputError) as exc_info:
                collect_test_result("Test Scenario", "Raptor")

            assert "cancelled" in str(exc_info.value.message)
