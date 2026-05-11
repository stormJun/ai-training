"""Shared models for the plugin hot reload demo."""

from __future__ import annotations

from collections.abc import Callable

from pydantic import BaseModel


class PluginSpec(BaseModel):
    """Plugin metadata and executable handler."""

    name: str
    description: str
    handler: Callable[[str], str]

    model_config = {"arbitrary_types_allowed": True}


class ChatRequest(BaseModel):
    """Chat API request."""

    query: str


class ChatResponse(BaseModel):
    """Chat API response."""

    response: str
