"""Postgres-backed Claude Agent SDK ``SessionStore``.

The SDK persists its per-session JSONL transcript through a ``SessionStore`` so a
turn can cold-resume after the warm client is gone (worker restart, LRU evict, or
a different worker on a different host picking up the project). The SDK default
writes those entries to LOCAL DISK (``~/.claude/projects/...``) — useless in an
N-worker fleet, where the next worker to touch the project runs elsewhere and
cannot see that file, so ``resume`` silently starts a fresh session and loses
continuity.

This store puts the transcript in Postgres instead — the same channel the worker
already coordinates through (RFC 0003, no Redis/broker) — so any worker can
resume any project's session. One row per JSONL entry, ordered by ``seq``.

Ported from the reference ``kernel/session_store.py`` (MongoDB), swapped to
asyncpg. The silent-marker logic there is a PARTNER/subagent concern and is
intentionally dropped.
"""

from __future__ import annotations

import json
import logging

import asyncpg
from claude_agent_sdk import SessionStore
from claude_agent_sdk.types import (
    SessionKey,
    SessionListSubkeysKey,
    SessionStoreEntry,
)
from ulid import ULID

logger = logging.getLogger("worker.session_store")


class PostgresSessionStore(SessionStore):
    """SDK ``SessionStore`` backed by the ``AgentSessionEntry`` table.

    A single instance is shared across every project; entries are keyed by the
    SDK ``SessionKey`` (``project_key`` + ``session_id`` + optional ``subpath``
    branch). ``subpath`` is ``NULL`` for the main session.
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        super().__init__()
        self._pool = pool

    async def append(self, key: SessionKey, entries: list[SessionStoreEntry]) -> None:
        """Append JSONL entries for a session, preserving order via a monotonic
        ``seq``. Runs in one transaction: read the current max ``seq`` for the
        key, then insert the batch sequentially after it. The worker enforces
        one-agent-per-project, so concurrent appends to the same session don't
        happen — a plain read-then-insert is safe."""
        if not entries:
            return

        project_key = key["project_key"]
        session_id = key["session_id"]
        subpath = key.get("subpath")

        async with self._pool.acquire() as conn:
            async with conn.transaction():
                base = await conn.fetchval(
                    """SELECT coalesce(max(seq), -1) FROM "AgentSessionEntry"
                       WHERE "projectKey"=$1 AND "sessionId"=$2
                         AND subpath IS NOT DISTINCT FROM $3""",
                    project_key,
                    session_id,
                    subpath,
                )
                rows = [
                    (
                        str(ULID()),
                        project_key,
                        session_id,
                        subpath,
                        base + 1 + i,
                        json.dumps(dict(entry)),
                    )
                    for i, entry in enumerate(entries)
                ]
                await conn.executemany(
                    """INSERT INTO "AgentSessionEntry"
                       (id,"projectKey","sessionId",subpath,seq,entry,"createdAt")
                       VALUES($1,$2,$3,$4,$5,$6::jsonb,now())""",
                    rows,
                )
        logger.debug(
            "appended %d entries (session=%s subpath=%s)",
            len(entries),
            session_id,
            subpath,
        )

    async def load(self, key: SessionKey) -> list[SessionStoreEntry] | None:
        """Load every stored entry for the session (or a branch, if ``subpath``
        is set), in append order. Returns ``None`` when nothing is stored."""
        subpath = key.get("subpath")
        rows = await self._pool.fetch(
            """SELECT entry FROM "AgentSessionEntry"
               WHERE "projectKey"=$1 AND "sessionId"=$2
                 AND subpath IS NOT DISTINCT FROM $3
               ORDER BY seq""",
            key["project_key"],
            key["session_id"],
            subpath,
        )
        if not rows:
            return None
        return [json.loads(r["entry"]) for r in rows]

    async def delete(self, key: SessionKey) -> None:
        """Wipe every entry (main session and all branches) for the session."""
        await self._pool.execute(
            """DELETE FROM "AgentSessionEntry"
               WHERE "projectKey"=$1 AND "sessionId"=$2""",
            key["project_key"],
            key["session_id"],
        )
        logger.info("deleted session entries (session=%s)", key["session_id"])

    async def list_subkeys(self, key: SessionListSubkeysKey) -> list[str]:
        """List every branch subpath stored for this session."""
        rows = await self._pool.fetch(
            """SELECT DISTINCT subpath FROM "AgentSessionEntry"
               WHERE "projectKey"=$1 AND "sessionId"=$2 AND subpath IS NOT NULL""",
            key["project_key"],
            key["session_id"],
        )
        return [r["subpath"] for r in rows]
