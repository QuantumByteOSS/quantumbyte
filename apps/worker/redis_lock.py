"""Redis-backed per-key mutex — ports the deck-app ``RedisService`` lock.

The harness (and any future pass) can run from two triggers for the same project:
the turn-triggered run in the claim loop, and the user-facing "Run harness" button.
A per-project lock collapses those into one run instead of two concurrent audits
racing on the same workspace.

RFC 0003 coordinates through Postgres and calls out "no Redis"; this introduces a
Redis dependency specifically for this cross-trigger lock (a Postgres advisory lock
would also work — this mirrors the platform's Redis lock instead).

Degrade-open: if Redis is unreachable, ``acquire`` returns a sentinel token so the
caller proceeds WITHOUT dedup rather than dropping the run — a Redis outage must not
disable the harness. The verdict upserts are idempotent, so a rare double-run is safe.
"""

from __future__ import annotations

import logging
import os
import uuid

from redis.asyncio import Redis

log = logging.getLogger("worker.redis_lock")

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# Returned when Redis is down: "proceed, but there is nothing real to release".
_DEGRADED_TOKEN = "__degraded__"

# Atomic compare-and-delete so a run only ever releases its OWN lock (never one a
# later run re-acquired after this run's TTL lapsed).
_RELEASE_LUA = (
    "if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('del', KEYS[1]) else return 0 end"
)

_client: Redis | None = None


def _redis() -> Redis:
    global _client
    if _client is None:
        _client = Redis.from_url(REDIS_URL, decode_responses=True)
    return _client


async def acquire(key: str, ttl_seconds: int) -> str | None:
    """Try to take ``key``. Returns an opaque token on success (pass it to ``release``),
    None when the lock is already held, or the degraded sentinel when Redis is
    unreachable (caller proceeds lock-free)."""
    token = uuid.uuid4().hex
    try:
        ok = await _redis().set(key, token, nx=True, ex=ttl_seconds)
    except Exception:
        log.warning("redis unreachable acquiring %s; proceeding without lock", key, exc_info=True)
        return _DEGRADED_TOKEN
    return token if ok else None


async def release(key: str, token: str | None) -> None:
    """Release ``key`` iff we still hold it. No-op for the degraded sentinel / None."""
    if not token or token == _DEGRADED_TOKEN:
        return
    try:
        await _redis().eval(_RELEASE_LUA, 1, key, token)
    except Exception:
        log.warning("redis unreachable releasing %s; lock will expire via TTL", key, exc_info=True)


async def close() -> None:
    """Close the shared client on worker shutdown."""
    global _client
    if _client is not None:
        try:
            await _client.aclose()
        except Exception:
            log.warning("error closing redis client", exc_info=True)
        _client = None
