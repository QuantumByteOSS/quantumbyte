"""In-process MCP servers the worker's agent can call.

v1 (P4): ``qb-partner`` (about_you, get_project_info) and ``qb-designer``
(product metadata + S3 assets). Both are registered top-level in
``ClaudeAgentOptions.mcp_servers`` and used directly by PARTNER (single-agent —
no subagents)."""

from __future__ import annotations

from typing import Any

from .context import S3Config, ToolContext
from .designer import build_designer_mcp
from .partner import build_partner_mcp


def build_mcp_servers(ctx: ToolContext) -> dict[str, Any]:
    """Return every in-process MCP server keyed by name for ``mcp_servers``."""
    return {
        "qb-partner": build_partner_mcp(ctx),
        "qb-designer": build_designer_mcp(ctx),
    }


__all__ = ["S3Config", "ToolContext", "build_mcp_servers"]
