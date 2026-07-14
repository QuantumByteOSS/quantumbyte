"""Sync prompt lookup, sourced from ``shared/prompts``.

Read-on-demand + hot-reload: ``get_prompt_text`` re-reads the ``<key>.md`` file
from disk on EVERY call and renders it. Editing a prompt takes effect on the next
turn with no worker restart. A missing file logs an error and returns ``""``
(graceful-miss contract preserved). No boot preload is required.

(``_set_cached`` / ``_prompt_cache`` are retained only so the copied ``_boot.py``
still imports; they are unused at runtime — prune-later.)
"""

import logging
import os
import re
from pathlib import Path

from ._keys import PromptKey

logger = logging.getLogger(__name__)

# Prompt source tree. The loader lives at ``apps/worker/prompt_management/``, so
# the tree is one level up at ``apps/worker/shared/prompts``. Overridable via the
# ``PROMPTS_ROOT`` env var (e.g. a mounted volume).
PROMPTS_ROOT = Path(
    os.environ.get("PROMPTS_ROOT")
    or Path(__file__).resolve().parent.parent / "shared" / "prompts"
)

# Matches a single ``{{ var_name }}`` mustache placeholder.
_PLACEHOLDER = re.compile(r"\{\{\s*(\w+)\s*\}\}")

# Retained for _boot.py import compatibility only (unused at runtime).
_prompt_cache: dict[str, str] = {}


def render(template: str, variables: dict[str, object]) -> str:
    """Substitute ``{{var}}`` placeholders; leave unknown placeholders intact."""
    if not variables:
        return template

    def _sub(match: re.Match[str]) -> str:
        name = match.group(1)
        return str(variables[name]) if name in variables else match.group(0)

    return _PLACEHOLDER.sub(_sub, template)


def _set_cached(name: str, template: str) -> None:
    """Retained for _boot.py import compatibility only (unused at runtime)."""
    _prompt_cache[name] = template


def get_prompt_text(key: PromptKey | str, **variables: object) -> str:
    """Return the rendered prompt body for ``key``, read fresh from disk.

    Reads ``<PROMPTS_ROOT>/<key>.md`` on every call (hot-reload). A missing file
    logs an error and returns ``""``.
    """
    name = str(key)
    path = PROMPTS_ROOT / f"{name}.md"
    try:
        template = path.read_text()
    except OSError as exc:
        logger.error("[prompt_management] missing prompt %r at %s — %s; returning empty string", name, path, exc)
        return ""
    return render(template, variables)
