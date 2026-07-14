"""qb-designer MCP server — product metadata + S3-backed assets.

v1 set: update the product's title/description/logo (Postgres Project columns,
with an ``updatedAt`` bump the FE picks up over the chat SSE), generate an image
(Gemini → S3 → Asset row), and list/get-url/delete assets (Postgres Asset + S3).

Deck-app deps (websocket, progress, Mongo app-config, Unsplash, cost-tracking) are
dropped. Descriptions come from shared/prompts (copied P2).
"""

from __future__ import annotations

import logging
from typing import Any

from claude_agent_sdk import create_sdk_mcp_server, tool
from mcp.types import ToolAnnotations
from ulid import ULID

from prompt_management import PromptKey as PK
from prompt_management import get_prompt_text

from . import s3
from ._shared import text_result
from .context import ToolContext
from .gemini import generate_image_bytes

logger = logging.getLogger("worker.mcp.designer")

# Designer field -> Project column.
_FIELD_COLUMN = {"title": "title", "description": "desc", "logo": "logo"}


async def _update_project_field(ctx: ToolContext, field: str, value: str) -> dict[str, Any]:
    """Set one Project column + bump updatedAt (the FE refetch trigger)."""
    column = _FIELD_COLUMN[field]
    try:
        result = await ctx.pool.execute(
            f'UPDATE "Project" SET "{column}"=$1, "updatedAt"=now() WHERE id=$2',
            value,
            ctx.project_id,
        )
        if result.endswith("0"):
            return text_result({"success": False, "error": f"Project {ctx.project_id} not found"})
        return text_result({"success": True, "field": field, "value": value})
    except Exception as e:
        logger.exception("update product %s failed", field)
        return text_result({"success": False, "error": str(e)})


def build_designer_mcp(ctx: ToolContext) -> Any:
    """Build the qb-designer in-process MCP server bound to this project."""

    @tool(
        "update_product_title",
        get_prompt_text(PK.AGENTS__MAIN_AGENT__SUBAGENTS__DESIGNER_AGENT__TOOLS__UPDATE_PRODUCT_TITLE__DESCRIPTION),
        {"type": "object", "properties": {"title": {"type": "string", "description": "New product title."}}, "required": ["title"]},
    )
    async def update_product_title(args: dict[str, Any]) -> dict[str, Any]:
        return await _update_project_field(ctx, "title", args["title"])

    @tool(
        "update_product_description",
        get_prompt_text(PK.AGENTS__MAIN_AGENT__SUBAGENTS__DESIGNER_AGENT__TOOLS__UPDATE_PRODUCT_DESCRIPTION__DESCRIPTION),
        {"type": "object", "properties": {"description": {"type": "string", "description": "New product description (short pitch)."}}, "required": ["description"]},
    )
    async def update_product_description(args: dict[str, Any]) -> dict[str, Any]:
        return await _update_project_field(ctx, "description", args["description"])

    @tool(
        "update_product_logo",
        get_prompt_text(PK.AGENTS__MAIN_AGENT__SUBAGENTS__DESIGNER_AGENT__TOOLS__UPDATE_PRODUCT_LOGO__DESCRIPTION),
        {"type": "object", "properties": {"logo": {"type": "string", "description": "Public URL of the new logo image (e.g. from generate_image)."}}, "required": ["logo"]},
    )
    async def update_product_logo(args: dict[str, Any]) -> dict[str, Any]:
        return await _update_project_field(ctx, "logo", args["logo"])

    @tool(
        "generate_image",
        get_prompt_text(PK.AGENTS__MAIN_AGENT__SUBAGENTS__DESIGNER_AGENT__TOOLS__IMAGES_SEARCH__DESCRIPTION),
        {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "What image to generate."},
                "count": {"type": "integer", "default": 1, "minimum": 1, "maximum": 4},
            },
            "required": ["query"],
        },
    )
    async def generate_image(args: dict[str, Any]) -> dict[str, Any]:
        query = args["query"]
        count = min(max(int(args.get("count", 1)), 1), 4)
        images: list[dict[str, Any]] = []
        try:
            for _ in range(count):
                data, mime = await generate_image_bytes(query)
                ext = (mime.split("/")[-1] or "png").split(";")[0]
                filename = f"{ctx.project_id}/{ULID()}.{ext}"
                url = await s3.upload_bytes(ctx, filename, data, mime)
                await ctx.pool.execute(
                    '''INSERT INTO "Asset"(id,"projectId",filename,"originalFilename",url,size,"mimeType","createdAt")
                       VALUES($1,$2,$3,$4,$5,$6,$7,now())''',
                    str(ULID()), ctx.project_id, filename, query, url, len(data), mime,
                )
                images.append({"filename": filename, "url": url, "mime_type": mime, "size": len(data)})
            return text_result({
                "success": True,
                "images": images,
                "count": len(images),
                "message": f"Generated {len(images)} image(s), stored in assets. Use a url to embed or set as logo.",
            })
        except Exception as e:
            logger.exception("generate_image failed")
            return text_result({"success": False, "error": str(e), "images": images})

    @tool(
        "list_assets",
        get_prompt_text(PK.AGENTS__MAIN_AGENT__SUBAGENTS__DESIGNER_AGENT__TOOLS__LIST_ASSETS__DESCRIPTION),
        {},
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    async def list_assets(args: dict[str, Any]) -> dict[str, Any]:
        try:
            rows = await ctx.pool.fetch(
                '''SELECT filename, "originalFilename", url, size, "mimeType", "createdAt"
                   FROM "Asset" WHERE "projectId"=$1 ORDER BY "createdAt"''',
                ctx.project_id,
            )
            assets = [
                {
                    "filename": r["filename"],
                    "original_filename": r["originalFilename"],
                    "url": r["url"],
                    "size": r["size"],
                    "mime_type": r["mimeType"],
                    "created_at": r["createdAt"].isoformat(),
                }
                for r in rows
            ]
            return text_result({"success": True, "assets": assets, "count": len(assets)})
        except Exception as e:
            logger.exception("list_assets failed")
            return text_result({"success": False, "error": str(e)})

    @tool(
        "get_asset_url",
        get_prompt_text(PK.AGENTS__MAIN_AGENT__SUBAGENTS__DESIGNER_AGENT__TOOLS__GET_ASSET_URL__DESCRIPTION),
        {"type": "object", "properties": {"filename": {"type": "string", "description": "Stored filename or original name."}}, "required": ["filename"]},
        annotations=ToolAnnotations(readOnlyHint=True),
    )
    async def get_asset_url(args: dict[str, Any]) -> dict[str, Any]:
        filename = args["filename"]
        try:
            row = await ctx.pool.fetchrow(
                '''SELECT filename, "originalFilename", url, size, "mimeType" FROM "Asset"
                   WHERE "projectId"=$1 AND (filename=$2 OR "originalFilename"=$2) LIMIT 1''',
                ctx.project_id, filename,
            )
            if row is None:
                return text_result({"success": False, "error": f"Asset '{filename}' not found. Use list_assets."})
            return text_result({
                "success": True, "filename": row["filename"], "original_filename": row["originalFilename"],
                "url": row["url"], "mime_type": row["mimeType"], "size": row["size"],
            })
        except Exception as e:
            logger.exception("get_asset_url failed")
            return text_result({"success": False, "error": str(e)})

    @tool(
        "delete_asset",
        get_prompt_text(PK.AGENTS__MAIN_AGENT__SUBAGENTS__DESIGNER_AGENT__TOOLS__DELETE_ASSET__DESCRIPTION),
        {"type": "object", "properties": {"filename": {"type": "string", "description": "Stored filename or original name to delete."}}, "required": ["filename"]},
        annotations=ToolAnnotations(destructiveHint=True),
    )
    async def delete_asset(args: dict[str, Any]) -> dict[str, Any]:
        filename = args["filename"]
        try:
            row = await ctx.pool.fetchrow(
                '''SELECT filename FROM "Asset"
                   WHERE "projectId"=$1 AND (filename=$2 OR "originalFilename"=$2) LIMIT 1''',
                ctx.project_id, filename,
            )
            if row is None:
                return text_result({"success": False, "error": f"Asset '{filename}' not found. Use list_assets."})
            key = row["filename"]
            await s3.delete_object(ctx, key)
            await ctx.pool.execute(
                'DELETE FROM "Asset" WHERE "projectId"=$1 AND filename=$2', ctx.project_id, key
            )
            return text_result({"success": True, "deleted_filename": key})
        except Exception as e:
            logger.exception("delete_asset failed")
            return text_result({"success": False, "error": str(e)})

    return create_sdk_mcp_server(
        name="qb-designer",
        version="1.0.0",
        tools=[
            update_product_title, update_product_description, update_product_logo,
            generate_image, list_assets, get_asset_url, delete_asset,
        ],
    )
