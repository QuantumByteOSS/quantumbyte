"""App-preview dev-server manager — one process per project, tied to affinity.

The orchestrator allocates a preview port together with the affinity pin
(``Project.previewPort``); this module is the worker-side half: start the
generated app in the project's clone on that port, keep it running across turns
(dev servers hot-reload the agent's file writes), and kill it when the affinity
goes away (same eviction path as the warm SDK client).

Stack detection is heuristic — the generator pipeline (docs/architecture/
app-generator.md) has no fixed target stack yet, so:

  * ``package.json`` with a ``dev`` script → ``npm run dev`` (``npm install``
    first when ``node_modules`` is missing). The port is passed BOTH as the
    ``PORT`` env var (Next.js, CRA, express conventions) and as ``-- --port N``
    (Vite, Next.js CLI) — servers ignore the one they don't understand.
  * bare ``index.html`` → ``python3 -m http.server`` on the port.
  * anything else → no preview; the platform's ping test keeps failing and the
    UI stays in its "starting" state.

Everything here is fail-open: a preview that won't boot must never break a turn.
"""

import asyncio
import json
import logging
import os
import shutil
import signal
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger("worker.preview")

# npm install on a fresh clone can be slow; cap it so a broken registry can't
# wedge the launch task forever.
_INSTALL_TIMEOUT_SECONDS = float(os.environ.get("PREVIEW_INSTALL_TIMEOUT_SECONDS", "600"))


def _log_path(project_id: str) -> Path:
    base = Path(os.environ.get("PREVIEW_LOG_DIR", "/tmp/quantumbyte-preview"))
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{project_id}.log"


# Build/runtime litter the preview creates in the clone. The turn pipeline commits
# the whole tree (git add -A) after every turn, so anything the preview writes MUST
# be ignored or it ends up pushed to the project's GitHub repo.
_GITIGNORE_ENTRIES = ["node_modules/", ".next/", "dist/", "build/", ".turbo/", "*.log"]


def _ensure_gitignore(cwd: Path) -> None:
    """Append missing preview-artifact entries to the clone's .gitignore. The write
    itself is committed by the next turn — that's fine, it's a standard file the
    generated app should have anyway. Fail-open."""
    try:
        gitignore = cwd / ".gitignore"
        existing = gitignore.read_text().splitlines() if gitignore.is_file() else []
        have = {line.strip() for line in existing}
        missing = [e for e in _GITIGNORE_ENTRIES if e not in have]
        if missing:
            content = "\n".join(existing + missing) + "\n"
            gitignore.write_text(content)
            log.info("added %s to %s", ", ".join(missing), gitignore)
    except OSError:
        log.warning("could not update .gitignore in %s", cwd, exc_info=True)


def _package_runner(cwd: Path) -> str:
    """Match the package runner to the lockfile the agent actually used — a
    bun-built app served with npm mixes lockfiles and can fail to install."""
    if (cwd / "bun.lockb").is_file() or (cwd / "bun.lock").is_file():
        if shutil.which("bun"):
            return "bun"
    return "npm"


def _detect_command(cwd: Path) -> list[str] | None:
    """Pick the serve command for the clone's contents (see module docstring)."""
    pkg = cwd / "package.json"
    if pkg.is_file():
        try:
            scripts = (json.loads(pkg.read_text()).get("scripts") or {})
        except (OSError, ValueError):
            scripts = {}
        runner = _package_runner(cwd)
        if "dev" in scripts:
            return [runner, "run", "dev", "--", "--port"]  # port appended by caller
        if "start" in scripts:
            return [runner, "run", "start", "--", "--port"]
    if (cwd / "index.html").is_file():
        return ["python3", "-m", "http.server", "--bind", "127.0.0.1"]
    return None


@dataclass
class _Preview:
    port: int
    task: asyncio.Task
    process: asyncio.subprocess.Process | None = None


class PreviewManager:
    """Tracks at most a handful of preview processes (capacity-1 worker → usually one)."""

    def __init__(self) -> None:
        self._previews: dict[str, _Preview] = {}

    async def ensure(self, project_id: str, cwd: str, port: int | None) -> None:
        """Idempotent: make the project's preview match ``port``.

        None port → stop. Same port + live process (or still-launching task) → no-op.
        Port change → restart on the new port. Called after every turn, so a server
        that died in between gets relaunched on the next activity.
        """
        current = self._previews.get(project_id)
        if port is None:
            if current is not None:
                await self.stop(project_id)
            return
        if current is not None:
            still_launching = not current.task.done()
            alive = current.process is not None and current.process.returncode is None
            if current.port == port and (still_launching or alive):
                return
            await self.stop(project_id)

        preview = _Preview(port=port, task=None)  # type: ignore[arg-type]
        preview.task = asyncio.create_task(self._launch(project_id, Path(cwd), port, preview))
        self._previews[project_id] = preview
        log.info("preview launch scheduled for project %s on port %s", project_id, port)

    async def _launch(self, project_id: str, cwd: Path, port: int, preview: _Preview) -> None:
        """Background launch: (npm install) → spawn the dev server. Fail-open."""
        try:
            command = _detect_command(cwd)
            if command is None:
                log.info("no runnable app detected for project %s; preview skipped", project_id)
                return

            # The turn pipeline commits the whole tree — keep preview artifacts out.
            _ensure_gitignore(cwd)

            log_file = open(_log_path(project_id), "ab")
            try:
                if command[0] in ("npm", "bun") and not (cwd / "node_modules").is_dir():
                    install_cmd = (
                        ["bun", "install"]
                        if command[0] == "bun"
                        else ["npm", "install", "--no-audit", "--no-fund"]
                    )
                    install = await asyncio.create_subprocess_exec(
                        *install_cmd,
                        cwd=str(cwd), stdout=log_file, stderr=log_file,
                        start_new_session=True,
                    )
                    # Expose the install as the preview's process so stop() kills it
                    # if the affinity drops mid-install.
                    preview.process = install
                    try:
                        await asyncio.wait_for(install.wait(), _INSTALL_TIMEOUT_SECONDS)
                    except asyncio.TimeoutError:
                        _kill_group(install)
                        log.warning("npm install timed out for project %s", project_id)
                        return
                    finally:
                        preview.process = None
                    if install.returncode != 0:
                        log.warning(
                            "npm install failed (%s) for project %s — see %s",
                            install.returncode, project_id, _log_path(project_id),
                        )
                        return

                env = {**os.environ, "PORT": str(port), "BROWSER": "none", "HOST": "127.0.0.1"}
                preview.process = await asyncio.create_subprocess_exec(
                    *command, str(port),
                    cwd=str(cwd), env=env, stdout=log_file, stderr=log_file,
                    start_new_session=True,  # own process group → clean tree kill
                )
                log.info(
                    "preview for project %s serving on 127.0.0.1:%s (pid %s, log %s)",
                    project_id, port, preview.process.pid, _log_path(project_id),
                )
            finally:
                log_file.close()
        except Exception:
            log.warning("preview launch failed for project %s", project_id, exc_info=True)

    async def stop(self, project_id: str) -> None:
        preview = self._previews.pop(project_id, None)
        if preview is None:
            return
        # Snapshot before cancelling — _launch's finally clears preview.process on
        # cancellation, and the kill below must still reach a mid-install npm.
        candidates = [preview.process]
        preview.task.cancel()
        try:
            await preview.task
        except (asyncio.CancelledError, Exception):
            pass
        candidates.append(preview.process)  # server spawned before the cancel landed
        for process in candidates:
            if process is not None and process.returncode is None:
                _kill_group(process)
                try:
                    await asyncio.wait_for(process.wait(), 10)
                except asyncio.TimeoutError:
                    _kill_group(process, signal.SIGKILL)
        log.info("preview stopped for project %s (port %s)", project_id, preview.port)

    async def stop_all(self) -> None:
        for project_id in list(self._previews):
            await self.stop(project_id)


def _kill_group(process: asyncio.subprocess.Process, sig: int = signal.SIGTERM) -> None:
    """Signal the whole process group — npm spawns the real server as a child."""
    try:
        os.killpg(os.getpgid(process.pid), sig)
    except (ProcessLookupError, PermissionError):
        pass
