"""Boot-time prompt loader.

``fetch_and_cache()`` reads every ``PromptKey`` from the on-disk
``shared/prompts`` tree and pushes the raw template text into the
process-wide cache so every later ``get_prompt_text`` call resolves
in-memory.

Idempotent — only runs once per process; later calls are no-ops. A key
whose ``<shared/prompts>/<path>.md`` file is missing raises ``RuntimeError``.
"""

from __future__ import annotations

import logging
import time

from ._client import PROMPTS_ROOT, _set_cached
from ._keys import PromptKey

logger = logging.getLogger(__name__)

_initialized = False


async def fetch_and_cache() -> None:
    """Load every ``PromptKey`` from ``shared/prompts`` into the cache."""
    global _initialized  # noqa: PLW0603
    if _initialized:
        return

    keys = list(PromptKey)
    total = len(keys)
    start = time.monotonic()

    cached = 0
    missing: list[str] = []

    for key in keys:
        path = PROMPTS_ROOT / f"{key.value}.md"
        try:
            _set_cached(str(key), path.read_text())
            cached += 1
        except OSError as exc:
            missing.append(f"{key} ({exc})")
            logger.error("[prompt_management] MISSING %s — %s", key, exc)

    elapsed = time.monotonic() - start

    if missing:
        raise RuntimeError(f"[prompt_management] {len(missing)} prompt file(s) missing under {PROMPTS_ROOT}: {', '.join(missing)}")

    _initialized = True
    logger.info("[prompt_management] cached %d/%d prompts from %s (%.3fs)", cached, total, PROMPTS_ROOT, elapsed)
