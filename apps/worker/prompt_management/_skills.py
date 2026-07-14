"""Materialize the ``shared/prompts/agents/main_agent/skills/`` tree into a
Claude Code plugin the SDK can load via ``ClaudeAgentOptions.plugins``.

Sync + hot-reload: ``get_skills()`` rebuilds the plugin dir from source on EVERY
call (mirrors the prompt loader). Edit a ``SKILL.md`` and the next cold session
open picks it up — no worker restart. The plugin dir is a STABLE path outside the
repo and outside every project clone, so neither the quantumbyte repo nor a
project's ``git add -A`` ever sweeps it.

Layout — ``shared/prompts/agents/main_agent/skills/<skill_dir>/<file>.md``
becomes ``<SKILLS_PLUGIN_DIR>/skills/<skill_dir>/<file>.md``. A skill is any
top-level ``<skill_dir>/`` that contains a ``SKILL.md`` (stray ``*.md``-only dirs
are copied but NOT returned as enabled skill names).
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import tempfile
from pathlib import Path

from ._client import PROMPTS_ROOT

logger = logging.getLogger(__name__)

# First ``name:`` line inside a SKILL.md YAML frontmatter block.
_SKILL_NAME_RE = re.compile(r"^name:\s*(.+?)\s*$", re.MULTILINE)


def _skill_name(skill_md: Path) -> str:
    """Canonical skill name = the frontmatter ``name:`` (what the SDK matches on;
    often hyphenated even when the dir uses underscores). Falls back to the dir
    name if no ``name:`` is present."""
    match = _SKILL_NAME_RE.search(skill_md.read_text())
    return match.group(1).strip() if match else skill_md.parent.name

_SKILLS_SRC = PROMPTS_ROOT / "agents" / "main_agent" / "skills"

# Stable output dir (env-overridable). Default: <tempdir>/qb-skills-plugin — a
# fixed, writable path that is NOT inside the source repo or any project clone.
SKILLS_PLUGIN_DIR = Path(
    os.environ.get("SKILLS_PLUGIN_DIR") or Path(tempfile.gettempdir()) / "qb-skills-plugin"
)

_PLUGIN_MANIFEST = {
    "name": "qb-skills",
    "version": "1.0.0",
    "description": "QuantumBytes agentic skills (shared/prompts-sourced). Materialized from shared/prompts on each session open and injected into the Claude Agent SDK session as a local plugin.",
}


def materialize_skills_plugin() -> tuple[Path, list[str]]:
    """Rebuild the plugin dir from ``shared/prompts`` and return ``(plugin_root,
    skill_names)``. Wipes and recreates ``SKILLS_PLUGIN_DIR`` each call so edits
    (and deletions) hot-reload. ``skill_names`` = top-level dirs that contain a
    ``SKILL.md``."""
    root = SKILLS_PLUGIN_DIR
    if root.exists():
        shutil.rmtree(root)
    (root / ".claude-plugin").mkdir(parents=True)
    (root / ".claude-plugin" / "plugin.json").write_text(json.dumps(_PLUGIN_MANIFEST, indent=2))
    skills_root = root / "skills"
    skills_root.mkdir()

    names: list[str] = []
    if not _SKILLS_SRC.is_dir():
        logger.warning("[skills] source dir not found at %s", _SKILLS_SRC)
        return root, names

    for src in sorted(_SKILLS_SRC.rglob("*.md")):
        rel = src.relative_to(_SKILLS_SRC)
        target = skills_root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(src.read_text())

    # Enabled skills = frontmatter names of dirs with a SKILL.md (skip stray
    # backup-md-only dirs). Frontmatter name — not dir name — is what the SDK
    # (and subagent skills=[...] refs) match on.
    names = sorted(
        _skill_name(d / "SKILL.md")
        for d in _SKILLS_SRC.iterdir()
        if d.is_dir() and (d / "SKILL.md").is_file()
    )
    logger.info("[skills] materialized %d skill(s) at %s: %s", len(names), root, names)
    return root, names


def get_skills() -> tuple[Path, list[str]]:
    """Return the freshly-materialized skills plugin ``(plugin_root, skill_names)``."""
    return materialize_skills_plugin()


def get_skills_by_name(names: list[str]) -> tuple[Path, list[str]]:
    """Materialize the plugin, then filter the enabled skill names to ``names``.
    The plugin root is shared, so the returned ``(plugin_root, filtered_names)``
    can be passed straight into the SDK exactly like ``get_skills()``."""
    plugin_root, all_names = get_skills()
    name_set = set(names)
    return plugin_root, [n for n in all_names if n in name_set]


# Back-compat: the old async boot loader is gone (hot-reload replaces it). Keep a
# thin async shim so any lingering caller / __init__ export still works.
async def fetch_skills_and_cache() -> tuple[Path, list[str]]:
    return materialize_skills_plugin()
