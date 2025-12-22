"""Conflow."""

from typing import Optional


class ConflowError(Exception):
    """Conflow errors."""

    exit_code: int = 1

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class ConfigurationError(ConflowError):
    """Raised when required configuration is missing or invalid."""

    exit_code = 1


class ConfluenceAPIError(ConflowError):
    """Raised when Confluence API calls fail."""

    exit_code = 6

    def __init__(self, message: str, status_code: Optional[int] = None):
        self.status_code = status_code
        super().__init__(message)


class AuthenticationError(ConfluenceAPIError):
    """Raised when authentication fails."""

    exit_code = 2


class PageNotFoundError(ConfluenceAPIError):
    """Raised when a requested page is not found."""

    exit_code = 3


class ParentPageError(ConfluenceAPIError):
    """Raised when the parent page is invalid or inaccessible."""

    exit_code = 4


class NetworkError(ConfluenceAPIError):
    """Raised when network errors occur."""

    exit_code = 5


class TemplateError(ConflowError):
    """Raised when there are issues with template processing."""

    exit_code = 3


class InteractiveInputError(ConflowError):
    """Raised when user cancels or provides invalid input."""

    exit_code = 130
