"""Preempt-and-coalesce scheduler for pass-3 harness runs.

The harness is read-only, fail-open, and upserts verdicts per requirement, so a
run can be cancelled at any await point without losing completed verdicts —
cancelled requirements simply stay unverified until the next run. That makes
this scheduling model sound:

  * after each turn the harness runs as a BACKGROUND task — the claim loop no
    longer awaits it, so the next user chat is never blocked behind an audit;
  * a new turn for the project PREEMPTS (cancels) the in-flight run before the
    agent touches the clone — turn and harness never overlap on the same repo,
    and the preempted run's remaining verdicts were about to go stale anyway;
  * the harness of the FINAL turn is never preempted, so it always runs to
    completion — determinism is preserved where it matters.

``run_harness`` already cleans up correctly under cancellation: its ``finally``
clears ``harnessRunning`` and releases the per-project redis lock, and its
``except Exception`` does not swallow ``CancelledError``. ``preempt`` AWAITS the
cancelled task precisely so that lock release lands before a replacement run
tries to acquire it (otherwise the new run would see "lock held" and skip).

A preempted MANUAL run re-requests itself (``harnessRunRequested=true``) so a
button press is never silently swallowed by a chat that arrived mid-run.
"""

import asyncio
import logging
from typing import Awaitable, Callable

import asyncpg

log = logging.getLogger("worker.harness_scheduler")


class HarnessScheduler:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool
        self._tasks: dict[str, asyncio.Task] = {}
        self._manual: dict[str, bool] = {}

    async def preempt(self, project_id: str) -> None:
        """Cancel the project's in-flight harness run (no-op when idle) and wait
        for its cleanup (flag clear + lock release) to finish."""
        task = self._tasks.pop(project_id, None)
        manual = self._manual.pop(project_id, False)
        if task is None or task.done():
            return
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        except Exception:
            log.warning("preempted harness task errored for project %s", project_id, exc_info=True)
        log.info("preempted harness run for project %s", project_id)
        if manual:
            # The button press must survive the preemption — re-queue it.
            try:
                await self._pool.execute(
                    'UPDATE "Project" SET "harnessRunRequested"=true WHERE id=$1', project_id
                )
            except Exception:
                log.warning("failed to re-request preempted manual harness for %s", project_id, exc_info=True)

    async def schedule(
        self,
        project_id: str,
        runner: Callable[[], Awaitable[None]],
        *,
        manual: bool = False,
    ) -> None:
        """Replace the project's harness run with a fresh background task."""
        await self.preempt(project_id)
        task = asyncio.create_task(runner())
        self._tasks[project_id] = task
        self._manual[project_id] = manual
        task.add_done_callback(lambda t: self._cleanup(project_id, t))

    def _cleanup(self, project_id: str, task: asyncio.Task) -> None:
        if self._tasks.get(project_id) is task:
            self._tasks.pop(project_id, None)
            self._manual.pop(project_id, None)

    async def shutdown(self) -> None:
        for project_id in list(self._tasks):
            await self.preempt(project_id)
