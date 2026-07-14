"""Per-project git workspace — the directory a project's agent runs in.

A project owns one GitHub repo (canonical) and one local clone (the agent's
working directory). ``ensure_workspace`` creates both if missing and returns the
local path; ``ClaudeAgentOptions.cwd`` is set to it.

Both steps are idempotent, so it is safe to call once per turn:

  * create GitHub repo  — a 422 "name already exists" is treated as success
  * clone to local dir  — skipped when ``<path>/.git`` already exists

New repos are created empty (``auto_init=false``). The local HEAD is pointed at
``main`` so the first commit + push lands on ``main`` and GitHub adopts it as the
default branch (an empty repo has no branch to set as default via the API).
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
from pathlib import Path

import httpx

log = logging.getLogger("worker.workspace")

# --- config -----------------------------------------------------------------

GIT_PAT = os.environ.get("GIT_PAT", "")
# Root under which every project's clone lives: <LOCAL_STORAGE>/qb-<project_id>.
LOCAL_STORAGE = Path(os.environ.get("LOCAL_STORAGE", "/var/qb-workspaces"))

GITHUB_API = "https://api.github.com"
DEFAULT_BRANCH = "main"

# Commit identity for agent-authored commits.
GIT_AUTHOR_NAME = os.environ.get("GIT_AUTHOR_NAME", "QuantumByte")
GIT_AUTHOR_EMAIL = os.environ.get("GIT_AUTHOR_EMAIL", "agent@quantumbyte.local")

# The repo owner (GitHub login) is derived from the PAT via GET /user and cached
# for the process — no GIT_USERNAME needed.
_owner_cache: str | None = None


def repo_name(project_id: str) -> str:
    return f"qb-{project_id}"


def _gh_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {GIT_PAT}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


async def repo_owner() -> str:
    """Authenticated user's login, resolved once from the PAT and cached."""
    global _owner_cache
    if _owner_cache is not None:
        return _owner_cache
    if not GIT_PAT:
        raise RuntimeError("GIT_PAT is not set — cannot resolve GitHub owner")
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f"{GITHUB_API}/user", headers=_gh_headers())
    if resp.status_code != 200:
        raise RuntimeError(f"GET /user failed (HTTP {resp.status_code}): {resp.text[:300]}")
    _owner_cache = resp.json()["login"]
    return _owner_cache


def local_path(project_id: str) -> Path:
    return LOCAL_STORAGE / repo_name(project_id)


async def _remote_url(name: str) -> str:
    """Auth-embedded HTTPS remote. Never log this — it carries the PAT."""
    owner = await repo_owner()
    return f"https://{GIT_PAT}@github.com/{owner}/{name}.git"


def _redact(text: str) -> str:
    return text.replace(GIT_PAT, "***") if GIT_PAT else text


# --- git subprocess ---------------------------------------------------------


async def _run_git(*args: str, cwd: str | Path | None = None) -> tuple[int, str]:
    proc = await asyncio.create_subprocess_exec(
        "git",
        *args,
        cwd=str(cwd) if cwd else None,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    out, _ = await proc.communicate()
    return proc.returncode or 0, _redact(out.decode(errors="replace").strip())


# --- github repo (idempotent) -----------------------------------------------


async def ensure_github_repo(name: str) -> None:
    """Create the private GitHub repo if it does not exist.

    Idempotent: a 422 whose body says the name already exists is a success, so
    concurrent workers / repeated turns never fail here.
    """
    if not GIT_PAT:
        raise RuntimeError("GIT_PAT is not set — cannot create GitHub repo")

    body = {"name": name, "private": True, "auto_init": False}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{GITHUB_API}/user/repos", headers=_gh_headers(), json=body
        )

    if resp.status_code in (200, 201):
        log.info("created GitHub repo %s", name)
        return

    # 422 = validation error; the only expected one is "already exists".
    if resp.status_code == 422 and "already exists" in resp.text:
        log.info("GitHub repo %s already exists — skipping create", name)
        return

    raise RuntimeError(
        f"GitHub repo create failed for {name} (HTTP {resp.status_code}): {resp.text[:500]}"
    )


async def github_repo_exists(name: str) -> bool:
    """True if the repo exists on GitHub (200), False on 404."""
    owner = await repo_owner()
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f"{GITHUB_API}/repos/{owner}/{name}", headers=_gh_headers())
    if resp.status_code == 200:
        return True
    if resp.status_code == 404:
        return False
    raise RuntimeError(
        f"GitHub repo lookup failed for {name} (HTTP {resp.status_code}): {resp.text[:300]}"
    )


# --- local clone (idempotent) -----------------------------------------------


async def _clone_repo(project_id: str) -> Path:
    """Clone the project repo into its local path. A non-git file or dir sitting
    at the path is cleared first (defensive). After cloning an empty repo, HEAD
    is pointed at ``main`` so the first commit lands there."""
    path = local_path(project_id)
    if path.exists():
        log.warning("clearing non-git path before clone: %s", path)
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        else:
            path.unlink()

    path.parent.mkdir(parents=True, exist_ok=True)
    name = repo_name(project_id)
    code, out = await _run_git("clone", await _remote_url(name), str(path))
    if code != 0:
        raise RuntimeError(f"git clone failed for {name} (exit {code}): {out}")

    # Empty repo → no branch yet. Make HEAD track main so the first commit/push
    # creates `main` and GitHub adopts it as the default branch.
    code, out = await _run_git(
        "symbolic-ref", "HEAD", f"refs/heads/{DEFAULT_BRANCH}", cwd=path
    )
    if code != 0:
        log.warning("could not set HEAD to %s in %s: %s", DEFAULT_BRANCH, path, out)

    log.info("cloned %s into %s", name, path)
    return path


async def _pull_latest(path: Path) -> None:
    """Sync an existing clone to the remote — git-as-truth: fetch + reset --hard
    origin/main. Remote is canonical; any local drift (uncommitted agent edits
    from a dead warm session, divergent history) is discarded so every cold open
    mirrors the remote exactly. No-op on an empty remote (no origin/main yet)."""
    code, out = await _run_git("fetch", "origin", cwd=path)
    if code != 0:
        raise RuntimeError(f"git fetch failed in {path}: {out}")

    code, _ = await _run_git(
        "rev-parse", "--verify", "--quiet", f"origin/{DEFAULT_BRANCH}", cwd=path
    )
    if code != 0:
        return  # empty remote — nothing to reset to yet

    code, out = await _run_git("reset", "--hard", f"origin/{DEFAULT_BRANCH}", cwd=path)
    if code != 0:
        raise RuntimeError(f"git reset --hard failed in {path}: {out}")
    log.info("synced %s to origin/%s", path, DEFAULT_BRANCH)


async def stage_and_diff(project_id: str) -> str:
    """Stage every working-tree change (``git add -A``) and return the staged diff.
    Empty string = clean tree. Caller uses the diff to generate a commit message,
    then calls ``commit_and_push``."""
    path = local_path(project_id)
    code, out = await _run_git("add", "-A", cwd=path)
    if code != 0:
        raise RuntimeError(f"git add failed in {path}: {out}")
    code, out = await _run_git("diff", "--cached", cwd=path)
    if code != 0:
        raise RuntimeError(f"git diff --cached failed in {path}: {out}")
    return out


async def head_sha(project_id: str) -> str | None:
    """Current HEAD commit sha of the project's clone, or None on an unborn branch
    (empty repo, no commit yet) or any git error. Used by the harness to stamp
    ``lastVerifiedSha`` and diff-scope which requirements need re-verifying."""
    path = local_path(project_id)
    code, out = await _run_git("rev-parse", "--verify", "--quiet", "HEAD", cwd=path)
    if code != 0 or not out.strip():
        return None
    return out.strip()


async def changed_files_since(project_id: str, base_sha: str) -> set[str] | None:
    """Repo-relative paths changed between ``base_sha`` and HEAD (both endpoints).
    None when the diff can't be computed (base commit gone after a history rewrite,
    bad sha) — callers treat None as "assume changed" and re-verify rather than
    serve a stale verdict."""
    path = local_path(project_id)
    code, out = await _run_git("diff", "--name-only", f"{base_sha}..HEAD", cwd=path)
    if code != 0:
        return None
    return {line.strip() for line in out.splitlines() if line.strip()}


# Top-level entries that are not "the app": planning docs, git plumbing, and
# dependency litter. Anything else in the clone counts as app code.
_NON_CODE_TOP_LEVEL = {"_doc", "node_modules"}


def _has_app_code_sync(root: Path) -> bool:
    if not root.is_dir():
        return False
    for entry in root.iterdir():
        if entry.name in _NON_CODE_TOP_LEVEL or entry.name.startswith("."):
            continue
        if entry.is_file():
            return True
        for sub in entry.rglob("*"):
            if sub.is_file():
                return True
    return False


async def workspace_has_code(project_id: str) -> bool:
    """True when the clone contains app code — any file outside ``_doc/``,
    dot-entries (.git, .gitignore, …) and ``node_modules``. Gates the harness's
    deterministic fail-all (nothing built → every requirement FAILs without
    spending an SDK run) and the agent's bootstrap context line."""
    return await asyncio.to_thread(_has_app_code_sync, local_path(project_id))


async def commit_and_push(project_id: str, message: str) -> bool:
    """Commit any working-tree changes and push to origin/main. Returns False when
    the tree is clean (nothing to commit). Called after every agent turn so the
    agent's file writes survive the next cold open's ``reset --hard`` (git-as-truth).

    Single-writer per project (one-agent-per-project claim) → the push is always a
    fast-forward; no rebase/merge handling needed.
    """
    path = local_path(project_id)

    code, out = await _run_git("status", "--porcelain", cwd=path)
    if code != 0:
        raise RuntimeError(f"git status failed in {path}: {out}")
    if not out.strip():
        return False  # clean tree — nothing the agent changed

    # Per-repo identity (idempotent, cheap).
    await _run_git("config", "user.name", GIT_AUTHOR_NAME, cwd=path)
    await _run_git("config", "user.email", GIT_AUTHOR_EMAIL, cwd=path)

    code, out = await _run_git("add", "-A", cwd=path)
    if code != 0:
        raise RuntimeError(f"git add failed in {path}: {out}")

    code, out = await _run_git("commit", "-m", message, cwd=path)
    if code != 0:
        raise RuntimeError(f"git commit failed in {path}: {out}")

    # First push on a fresh repo creates `main` and makes it the default branch.
    code, out = await _run_git("push", "origin", f"HEAD:{DEFAULT_BRANCH}", cwd=path)
    if code != 0:
        raise RuntimeError(f"git push failed in {path}: {out}")

    log.info("committed + pushed agent changes in %s", path)
    return True


async def ensure_workspace(project_id: str) -> Path:
    """Prepare the project's working directory and return its local path.

    Decision tree (idempotent, safe once per cold open):
      * local clone exists  → git pull (fetch + reset --hard to remote)
      * else repo on GitHub → clone
      * else                → create repo, then clone
    """
    path = local_path(project_id)
    name = repo_name(project_id)

    if (path / ".git").is_dir():
        await _pull_latest(path)
        return path

    if not await github_repo_exists(name):
        await ensure_github_repo(name)

    return await _clone_repo(project_id)
