"""Conflow."""

from typing import Dict, Optional

from pydantic import BaseModel, HttpUrl


class ConfluenceConfig(BaseModel):
    """Configuration for Confluence API connection."""

    base_url: str
    email: str
    api_token: str
    default_parent_page_id: Optional[str] = None
    default_space_key: Optional[str] = None
    default_template_page_id: Optional[str] = None


class PageContent(BaseModel):
    """Content of a Confluence page."""

    id: str
    title: str
    body: str
    body_adf: Optional[str] = None
    space_key: str


class CreatedPage(BaseModel):
    """Information about a newly created page."""

    id: str
    title: str
    url: str


class NewPageRequest(BaseModel):
    """Request to create a new page."""

    title: str
    parent_id: str
    space_key: str
    template_id: str
    placeholder_values: Dict[str, str] = {}
