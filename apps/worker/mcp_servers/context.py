"""Per-session context the in-process MCP tools close over.

Built once per warm session open (one per project) and handed to the tool
builders so the tools never take ids/creds as arguments — they are bound here.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import aioboto3
import asyncpg


@dataclass(frozen=True)
class S3Config:
    """S3 / minio connection config, read from the environment once at boot."""

    endpoint: str
    public_url: str
    access_key: str
    secret_key: str
    bucket: str

    @classmethod
    def from_env(cls) -> "S3Config":
        return cls(
            endpoint=os.environ.get("S3_ENDPOINT", "http://localhost:9000"),
            public_url=os.environ.get("S3_PUBLIC_URL", "http://localhost:9000"),
            access_key=os.environ.get("S3_ACCESS_KEY", "quantumbyte"),
            secret_key=os.environ.get("S3_SECRET_KEY", "quantumbyte"),
            bucket=os.environ.get("S3_BUCKET", "qb-assets"),
        )


@dataclass(frozen=True)
class ToolContext:
    """Everything the qb-partner / qb-designer tools need, bound per session."""

    project_id: str
    pool: asyncpg.Pool
    s3cfg: S3Config
    s3_session: aioboto3.Session
