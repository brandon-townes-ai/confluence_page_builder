"""Confluence API client wrapper."""

import logging
from typing import Optional
from urllib.parse import urlparse

from atlassian import Confluence
from requests.exceptions import ConnectionError, Timeout

from conflow.exceptions import (
    AuthenticationError,
    ConfluenceAPIError,
    NetworkError,
    PageNotFoundError,
    ParentPageError,
)
from conflow.models import ConfluenceConfig, CreatedPage, PageContent

logger = logging.getLogger(__name__)


class ConfluenceClient:
    """Wrapper around the Confluence API."""

    def __init__(self, config: ConfluenceConfig):
        """Initialize the Confluence client.

        Args:
            config: Configuration with credentials and base URL.
        """
        self.config = config
        self._client = Confluence(
            url=config.base_url,
            username=config.email,
            password=config.api_token,
            cloud=True,
        )
        parsed = urlparse(config.base_url.rstrip("/"))
        self._host_url = f"{parsed.scheme}://{parsed.netloc}"

    def validate_credentials(self) -> bool:
        """Validate that the credentials are correct.

        Returns:
            True if credentials are valid.

        Raises:
            AuthenticationError: If credentials are invalid (401).
            NetworkError: If there's a network issue.

        Note:
            403 Forbidden errors are treated as success - the token is valid
            but may have restricted permissions. Actual operations will fail
            if permissions are insufficient.
        """
        try:
            self._client.get_all_spaces(start=0, limit=1)
            return True
        except ConnectionError as e:
            raise NetworkError(f"Failed to connect to Confluence: {e}")
        except Timeout as e:
            raise NetworkError(f"Connection timed out: {e}")
        except Exception as e:
            error_str = str(e).lower()
            if "401" in error_str or "unauthorized" in error_str:
                raise AuthenticationError(
                    "Authentication failed. Check your email and API token."
                )
            if "403" in error_str or "forbidden" in error_str:
                return True
            raise NetworkError(f"Failed to validate credentials: {e}")

    def get_page_by_id(self, page_id: str) -> PageContent:
        """Fetch a page by its ID, including both storage and ADF representations.

        Args:
            page_id: The Confluence page ID.

        Returns:
            PageContent with the page details. body_adf contains the native
            Atlassian Document Format if available.

        Raises:
            PageNotFoundError: If the page doesn't exist.
            ConfluenceAPIError: If the API call fails.
        """
        try:
            page = self._client.get_page_by_id(
                page_id,
                expand="body.storage,body.atlas_doc_format,space",
            )
            if not page:
                raise PageNotFoundError(f"Page with ID {page_id} not found")

            body_storage = page["body"]["storage"]["value"]
            body_adf = page["body"].get("atlas_doc_format", {}).get("value")

            return PageContent(
                id=str(page["id"]),
                title=page["title"],
                body=body_storage,
                body_adf=body_adf,
                space_key=page["space"]["key"],
            )
        except PageNotFoundError:
            raise
        except ConnectionError as e:
            raise NetworkError(f"Failed to connect to Confluence: {e}")
        except Timeout as e:
            raise NetworkError(f"Connection timed out: {e}")
        except Exception as e:
            error_str = str(e).lower()
            if "404" in error_str or "not found" in error_str:
                raise PageNotFoundError(f"Page with ID {page_id} not found")
            if "401" in error_str or "unauthorized" in error_str:
                raise AuthenticationError(
                    "Authentication failed. Check your email and API token."
                )
            raise ConfluenceAPIError(f"Failed to fetch page {page_id}: {e}")

    def create_page(
        self,
        space_key: str,
        parent_id: str,
        title: str,
        body: str,
        body_adf: Optional[str] = None,
    ) -> CreatedPage:
        """Create a new page under a parent page.

        If body_adf (native Atlassian Document Format) is provided, it is used
        for creation to avoid Fabric editor validation errors that occur when
        posting storage format content back to Confluence Cloud.

        Args:
            space_key: The space key where the page will be created.
            parent_id: The ID of the parent page.
            title: The title of the new page.
            body: The body content in storage format (used as fallback).
            body_adf: The body content in ADF format (preferred).

        Returns:
            CreatedPage with the new page details.

        Raises:
            ParentPageError: If the parent page is invalid.
            ConfluenceAPIError: If the API call fails.
        """
        try:
            if body_adf:
                logger.debug("Creating page using native ADF representation")
                result = self._client.create_page(
                    space=space_key,
                    parent_id=parent_id,
                    title=title,
                    body=body_adf,
                    representation="atlas_doc_format",
                )
            else:
                logger.debug("Creating page using storage representation")
                result = self._client.create_page(
                    space=space_key,
                    parent_id=parent_id,
                    title=title,
                    body=body,
                    representation="storage",
                )

            page_id = result["id"]
            webui_path = result.get("_links", {}).get(
                "webui", f"/wiki/spaces/{space_key}/pages/{page_id}"
            )
            page_url = f"{self._host_url}{webui_path}"

            return CreatedPage(
                id=str(page_id),
                title=result["title"],
                url=page_url,
            )
        except ConnectionError as e:
            raise NetworkError(f"Failed to connect to Confluence: {e}")
        except Timeout as e:
            raise NetworkError(f"Connection timed out: {e}")
        except Exception as e:
            error_str = str(e).lower()
            if "parent" in error_str or "ancestor" in error_str:
                raise ParentPageError(
                    f"Parent page {parent_id} is invalid or inaccessible"
                )
            if "401" in error_str or "unauthorized" in error_str:
                raise AuthenticationError(
                    "Authentication failed. Check your email and API token."
                )
            if "404" in error_str:
                raise ParentPageError(
                    f"Parent page {parent_id} not found or space {space_key} doesn't exist"
                )
            raise ConfluenceAPIError(f"Failed to create page: {e}")

    def update_page(
        self,
        page_id: str,
        title: str,
        body: str,
        space_key: str,
    ) -> CreatedPage:
        """Update an existing page.

        Args:
            page_id: The ID of the page to update.
            title: The title of the page.
            body: The updated body content in storage format.
            space_key: The space key (required for URL construction).

        Returns:
            CreatedPage with the updated page details.

        Raises:
            PageNotFoundError: If the page doesn't exist.
            ConfluenceAPIError: If the API call fails.
        """
        try:
            result = self._client.update_page(
                page_id=page_id,
                title=title,
                body=body,
                representation="storage",
            )

            webui_path = result.get("_links", {}).get(
                "webui", f"/wiki/spaces/{space_key}/pages/{page_id}"
            )
            page_url = f"{self._host_url}{webui_path}"

            return CreatedPage(
                id=str(result["id"]),
                title=result["title"],
                url=page_url,
            )
        except PageNotFoundError:
            raise
        except ConnectionError as e:
            raise NetworkError(f"Failed to connect to Confluence: {e}")
        except Timeout as e:
            raise NetworkError(f"Connection timed out: {e}")
        except Exception as e:
            error_str = str(e).lower()
            if "404" in error_str or "not found" in error_str:
                raise PageNotFoundError(f"Page with ID {page_id} not found")
            if "401" in error_str or "unauthorized" in error_str:
                raise AuthenticationError(
                    "Authentication failed. Check your email and API token."
                )
            if "409" in error_str or "conflict" in error_str:
                raise ConfluenceAPIError(
                    f"Version conflict when updating page {page_id}. "
                    "The page may have been modified by another user."
                )
            raise ConfluenceAPIError(f"Failed to update page {page_id}: {e}")
