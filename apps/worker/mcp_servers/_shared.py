"""Small helpers shared by the in-process MCP tools."""

from __future__ import annotations

import json
from typing import Any


def text_result(payload: dict[str, Any]) -> dict[str, Any]:
    """Package a tool result in the shape the Claude Agent SDK expects — a single
    text content block carrying the JSON payload."""
    return {"content": [{"type": "text", "text": json.dumps(payload)}]}
