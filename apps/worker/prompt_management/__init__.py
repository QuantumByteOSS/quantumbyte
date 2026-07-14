"""Centralized prompt management, sourced from ``shared/prompts``.

The boot lifecycle loads every prompt named in ``PromptKey`` once
from disk, caches the raw template text in-process, and every later
``get_prompt_text`` call resolves entirely from memory — no disk read at
request time.

Boot order (called once during the app/worker lifespan):

1. ``await fetch_and_cache()`` — load every ``PromptKey`` from
   ``shared/prompts`` and populate the process-wide cache.
2. ``await fetch_skills_and_cache()`` — materialize the skill prompts
   into a tmpdir laid out as a Claude Code plugin.

Runtime (sync):

- ``get_prompt_text(key, **vars)`` — return the compiled prompt body
  for a ``PromptKey``. Always served from the boot cache.
- ``get_skills()`` — return the skills plugin ``(plugin_root, names)``
  materialized at boot.
"""

from ._boot import fetch_and_cache
from ._client import get_prompt_text
from ._keys import PromptKey
from ._skills import fetch_skills_and_cache, get_skills, get_skills_by_name

__all__ = ["PromptKey", "fetch_and_cache", "fetch_skills_and_cache", "get_prompt_text", "get_skills", "get_skills_by_name"]
