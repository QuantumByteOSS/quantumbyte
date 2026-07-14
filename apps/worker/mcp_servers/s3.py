"""Thin async S3 (minio) helpers over aioboto3.

The bucket is public-read (see docker-compose minio-init), so the public URL is a
plain ``<public_url>/<bucket>/<key>`` — no signing.
"""

from __future__ import annotations

from .context import ToolContext


def public_url_for(ctx: ToolContext, key: str) -> str:
    return f"{ctx.s3cfg.public_url.rstrip('/')}/{ctx.s3cfg.bucket}/{key}"


def _client(ctx: ToolContext):
    """Open an aioboto3 S3 client bound to this context's config (async ctx mgr)."""
    return ctx.s3_session.client(
        "s3",
        endpoint_url=ctx.s3cfg.endpoint,
        aws_access_key_id=ctx.s3cfg.access_key,
        aws_secret_access_key=ctx.s3cfg.secret_key,
    )


async def upload_bytes(ctx: ToolContext, key: str, data: bytes, content_type: str) -> str:
    """Upload ``data`` under ``key`` and return its public direct URL."""
    async with _client(ctx) as s3:
        await s3.put_object(
            Bucket=ctx.s3cfg.bucket, Key=key, Body=data, ContentType=content_type
        )
    return public_url_for(ctx, key)


async def delete_object(ctx: ToolContext, key: str) -> None:
    async with _client(ctx) as s3:
        await s3.delete_object(Bucket=ctx.s3cfg.bucket, Key=key)
