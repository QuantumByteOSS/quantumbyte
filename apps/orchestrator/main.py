"""QuantumByte orchestrator — assigns PENDING chat messages to live workers.

Single-instance Python loop coordinating work entirely through PostgreSQL
(RFC 0003). No Redis, no broker. It shares the same database the web app owns;
the schema is owned by Prisma in apps/web — this process runs DML only, never DDL.

Each tick:
  1. Recover from dead workers / stalls (unpin dead affinity, reset stalled
     PROCESSING turns to PENDING, unassign PENDING pinned to dead workers).
  2. Assign PENDING USER messages to workers, honouring project→worker affinity
     and the one-agent-per-project invariant.
"""

import logging
import os
import time

import psycopg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://quantumbyte:quantumbyte@localhost:5432/quantumbyte"
)
WORKER_TIMEOUT_SECONDS = int(os.environ.get("WORKER_TIMEOUT_SECONDS", "30"))
# How long a worker row outlives its last heartbeat before it is deleted. A worker
# deregisters itself on a clean shutdown; one that is SIGKILLed, OOM-killed, or whose
# host vanishes never does, and its row lingers forever. Nothing routes to it (every
# decision is made against the live set, not the table), so this is hygiene, not
# correctness — hence a grace far longer than WORKER_TIMEOUT_SECONDS: a worker that is
# merely wedged or partitioned gets a long window to come back and resume heartbeating
# before we forget it existed.
WORKER_REAP_SECONDS = int(os.environ.get("WORKER_REAP_SECONDS", "3600"))
POLL_INTERVAL_SECONDS = float(os.environ.get("POLL_INTERVAL_SECONDS", "1"))
# A turn is stale only when its worker-renewed lease lapses (ChatMessage.leaseExpiresAt),
# never when the message is merely old: createdAt does not advance, so an age-based
# timeout requeues a long turn on every tick forever and the agent re-answers the same
# message. The worker renews the lease every few seconds for as long as the turn runs.
# Turns legitimately run for many minutes (the build agent) — the lease, not a wall
# clock, is what says whether anyone is still working on it.
# How many times a turn may be claimed before it is failed instead of requeued. Stops a
# turn that kills its worker every attempt from cycling forever.
MAX_TURN_ATTEMPTS = int(os.environ.get("MAX_TURN_ATTEMPTS", "3"))
# Idle TTL for a project→worker affinity pin. Set/refreshed on every assignment
# (and by the worker after each completed activity); once it lapses with the
# project quiescent, the pin is dropped and the worker tears down its warm session.
AFFINITY_TTL_SECONDS = int(os.environ.get("AFFINITY_TTL_SECONDS", "1800"))
# App-preview port range. One port per pinned project, allocated with the pin and
# cleared with it. Globally unique across projects (workers share localhost for now).
PREVIEW_PORT_MIN = int(os.environ.get("PREVIEW_PORT_MIN", "4100"))
PREVIEW_PORT_MAX = int(os.environ.get("PREVIEW_PORT_MAX", "4199"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("orchestrator")


def live_workers(cur):
    """Return the set of Worker.id whose heartbeat is within the timeout window."""
    cur.execute(
        """
        SELECT id FROM "Worker"
        WHERE "lastSeen" > now() - make_interval(secs => %s)
        """,
        (WORKER_TIMEOUT_SECONDS,),
    )
    return {row[0] for row in cur.fetchall()}


def recover(cur, live):
    """Sweep state left behind by dead or stalled workers back to a routable state."""
    live_list = list(live)

    # Drop affinity pins that point at a worker no longer live.
    cur.execute(
        """
        UPDATE "Project"
        SET "assignedWorker" = NULL, "affinityExpiresAt" = NULL, "previewPort" = NULL
        WHERE "assignedWorker" IS NOT NULL
          AND NOT ("assignedWorker" = ANY(%s))
        """,
        (live_list,),
    )
    if cur.rowcount:
        log.info("unpinned %s project(s) from dead workers", cur.rowcount)

    # Expire idle affinity pins: TTL lapsed and the project is quiescent — no turn
    # in flight or queued, no harness running. The pinned worker notices the dropped
    # pin (affinity watch loop) and tears down its warm session. PENDING messages
    # block expiry because they are about to be assigned, which would refresh the pin.
    cur.execute(
        """
        UPDATE "Project"
        SET "assignedWorker" = NULL, "affinityExpiresAt" = NULL, "previewPort" = NULL
        WHERE "assignedWorker" IS NOT NULL
          AND "affinityExpiresAt" IS NOT NULL
          AND "affinityExpiresAt" < now()
          AND "harnessRunning" = false
          AND NOT EXISTS (
            SELECT 1 FROM "ChatMessage" m
            WHERE m."projectId" = "Project".id
              AND m.status IN ('PROCESSING', 'PENDING')
          )
        """
    )
    if cur.rowcount:
        log.info("expired %s idle affinity pin(s)", cur.rowcount)

    # Clear a stuck harness-running flag left by a dead worker. A live worker running
    # the harness pins the project to itself (claim_harness_one sets assignedWorker),
    # so a running flag whose project is now unpinned (the sweep above NULLed it) or
    # pinned to a dead worker means the run died mid-flight — reset it so the UI
    # stops showing "Checking…" and the project can request a fresh run.
    cur.execute(
        """
        UPDATE "Project"
        SET "harnessRunning" = false
        WHERE "harnessRunning" = true
          AND (
            "assignedWorker" IS NULL
            OR NOT ("assignedWorker" = ANY(%s))
          )
        """,
        (live_list,),
    )
    if cur.rowcount:
        log.info("cleared %s stuck harnessRunning flag(s) from dead workers", cur.rowcount)

    # A PROCESSING turn is abandoned when nobody is still working on it: its worker
    # is dead, or its worker-renewed lease has lapsed (a live worker renews the lease
    # every few seconds for the whole turn, however long that takes). A NULL lease on
    # a PROCESSING row predates the lease column — treat it as lapsed; the reclaim
    # sets one.
    abandoned = """
        status = 'PROCESSING'
        AND (
          "assignedWorker" IS NULL
          OR NOT ("assignedWorker" = ANY(%s))
          OR "leaseExpiresAt" IS NULL
          OR "leaseExpiresAt" < now()
        )
    """

    # A turn that has burned through its attempts is poison: every claim so far ended
    # with its worker dead or its lease lapsed, so requeuing it again just feeds the
    # same loop. Fail it instead — the error surfaces on the message in the UI.
    cur.execute(
        f"""
        UPDATE "ChatMessage"
        SET status = 'FAILED',
            "assignedWorker" = NULL,
            "leaseExpiresAt" = NULL,
            error = 'This turn was interrupted repeatedly and could not be completed. Please try again.'
        WHERE {abandoned}
          AND role = 'USER'
          AND attempts >= %s
        """,
        (live_list, MAX_TURN_ATTEMPTS),
    )
    if cur.rowcount:
        log.warning(
            "failed %s message(s) after %s attempts", cur.rowcount, MAX_TURN_ATTEMPTS
        )

    # Requeue the rest. Worker turn handlers are idempotent (RFC 0003), so re-running
    # is safe. USER rows only — the unit of work is the user turn; the ASSISTANT reply
    # row (created up front for streaming) is a byproduct and is never re-claimable
    # (the worker only claims role='USER'), so requeuing it would orphan it.
    cur.execute(
        f"""
        UPDATE "ChatMessage"
        SET status = 'PENDING', "assignedWorker" = NULL, "leaseExpiresAt" = NULL
        WHERE {abandoned}
          AND role = 'USER'
        """,
        (live_list,),
    )
    if cur.rowcount:
        log.info("reset %s stalled PROCESSING message(s) to PENDING", cur.rowcount)

    # Clean up orphaned streaming ASSISTANT rows whose turn was abandoned — same
    # dead-worker / lapsed-lease test, so a live worker's in-flight stream is left
    # alone. Leaving one behind would deadlock the project: the worker's claim query
    # skips any project with a PROCESSING row of ANY role, so the requeued USER turn
    # could never be picked up. The reclaim creates a fresh assistant row.
    cur.execute(
        f"""
        DELETE FROM "ChatMessage"
        WHERE {abandoned}
          AND role = 'ASSISTANT'
        """,
        (live_list,),
    )
    if cur.rowcount:
        log.info("deleted %s orphaned PROCESSING assistant row(s)", cur.rowcount)

    # Unassign PENDING messages pinned to a dead worker so they can be re-routed.
    cur.execute(
        """
        UPDATE "ChatMessage"
        SET "assignedWorker" = NULL
        WHERE status = 'PENDING'
          AND "assignedWorker" IS NOT NULL
          AND NOT ("assignedWorker" = ANY(%s))
        """,
        (live_list,),
    )
    if cur.rowcount:
        log.info("unassigned %s PENDING message(s) from dead workers", cur.rowcount)

    # Reap worker rows long past their last heartbeat. A worker deregisters itself on a
    # clean shutdown; one that is killed outright leaves its row behind forever. Runs
    # last: every sweep above has already moved that worker's pins and turns off it, so
    # by here the row owns nothing. Worker ids are plain strings (no FK), so this frees
    # the id for reuse — safe, because a restarted worker gets a fresh random id anyway
    # unless WORKER_ID is pinned, in which case it re-registers with an upsert.
    cur.execute(
        """
        DELETE FROM "Worker"
        WHERE "lastSeen" < now() - make_interval(secs => %s)
        """,
        (WORKER_REAP_SECONDS,),
    )
    if cur.rowcount:
        log.info("reaped %s worker row(s) dead for over %ss", cur.rowcount, WORKER_REAP_SECONDS)


def pending_projects(cur):
    """Projects with at least one unassigned PENDING USER message."""
    cur.execute(
        """
        SELECT DISTINCT "projectId" FROM "ChatMessage"
        WHERE role = 'USER' AND status = 'PENDING' AND "assignedWorker" IS NULL
        """
    )
    return [row[0] for row in cur.fetchall()]


def project_is_processing(cur, project_id):
    """True if the project already has a PROCESSING message (one-agent-per-project)."""
    cur.execute(
        """
        SELECT 1 FROM "ChatMessage"
        WHERE "projectId" = %s AND status = 'PROCESSING'
        LIMIT 1
        """,
        (project_id,),
    )
    return cur.fetchone() is not None


def project_affinity(cur, project_id):
    """Current affinity pin for the project, or None."""
    cur.execute('SELECT "assignedWorker" FROM "Project" WHERE id = %s', (project_id,))
    row = cur.fetchone()
    return row[0] if row else None


def free_worker(cur, live):
    """Pick a live worker with no affinity pin (capacity: one project per worker).

    A worker holds exactly one warm session; while any project is pinned to it, it
    is not routable for other projects. Ties broken by worker id for determinism.
    Returns None when every live worker is pinned — the message waits for a pin to
    expire or a new worker to join.
    """
    cur.execute(
        """
        SELECT w.id
        FROM "Worker" w
        WHERE w.id = ANY(%s)
          AND NOT EXISTS (
            SELECT 1 FROM "Project" p WHERE p."assignedWorker" = w.id)
        ORDER BY w.id ASC
        LIMIT 1
        """,
        (list(live),),
    )
    row = cur.fetchone()
    return row[0] if row else None


def allocate_preview_port(cur):
    """Smallest free port in [PREVIEW_PORT_MIN, PREVIEW_PORT_MAX].

    Free = not held by any pinned project. Runs inside the tick's transaction, and
    a single orchestrator instance is the only allocator (RFC 0003), so two projects
    can never race the same port. None when the range is exhausted — the project
    still gets pinned, it just has no preview until a port frees up.
    """
    cur.execute('SELECT "previewPort" FROM "Project" WHERE "previewPort" IS NOT NULL')
    used = {row[0] for row in cur.fetchall()}
    for port in range(PREVIEW_PORT_MIN, PREVIEW_PORT_MAX + 1):
        if port not in used:
            return port
    return None


def assign(cur, live):
    """Assign unassigned PENDING USER messages to live workers."""
    for project_id in pending_projects(cur):
        # One agent per project: skip if a turn is already in flight.
        if project_is_processing(cur, project_id):
            continue

        # Affinity: reuse the pinned worker if it is live (warm session) and
        # refresh its idle TTL, else pick a free live worker (capacity 1) and
        # record the new pin with a fresh TTL.
        pinned = project_affinity(cur, project_id)
        if pinned is not None and pinned in live:
            worker = pinned
            # Refresh the idle TTL, and backfill a preview port if the pin was
            # created without one (the worker's manual-harness claim pins but
            # cannot allocate ports — only this single-instance loop can).
            cur.execute(
                """
                UPDATE "Project"
                SET "affinityExpiresAt" = now() + make_interval(secs => %s)
                WHERE id = %s
                RETURNING "previewPort"
                """,
                (AFFINITY_TTL_SECONDS, project_id),
            )
            if cur.fetchone()[0] is None:
                port = allocate_preview_port(cur)
                if port is not None:
                    cur.execute(
                        'UPDATE "Project" SET "previewPort" = %s WHERE id = %s',
                        (port, project_id),
                    )
                    log.info("backfilled preview port %s for project %s", port, project_id)
        else:
            worker = free_worker(cur, live)
            if worker is None:
                continue
            port = allocate_preview_port(cur)
            if port is None:
                log.warning(
                    "preview port range exhausted; project %s pinned without preview",
                    project_id,
                )
            cur.execute(
                """
                UPDATE "Project"
                SET "assignedWorker" = %s,
                    "affinityExpiresAt" = now() + make_interval(secs => %s),
                    "previewPort" = %s
                WHERE id = %s
                """,
                (worker, AFFINITY_TTL_SECONDS, port, project_id),
            )
            log.info("pinned project %s -> worker %s (preview port %s)", project_id, worker, port)

        cur.execute(
            """
            UPDATE "ChatMessage"
            SET "assignedWorker" = %s
            WHERE "projectId" = %s AND role = 'USER'
              AND status = 'PENDING' AND "assignedWorker" IS NULL
            """,
            (worker, project_id),
        )
        if cur.rowcount:
            log.info(
                "assigned %s message(s) of project %s to worker %s",
                cur.rowcount,
                project_id,
                worker,
            )


def tick(conn):
    with conn.cursor() as cur:
        live = live_workers(cur)
        recover(cur, live)
        if live:
            assign(cur, live)
        else:
            log.debug("no live workers; messages wait")
    conn.commit()


def main():
    log.info("=" * 60)
    log.info("QuantumByte orchestrator (RFC 0003) — single instance")
    log.info("DATABASE_URL             = %s", DATABASE_URL)
    log.info("WORKER_TIMEOUT_SECONDS   = %s", WORKER_TIMEOUT_SECONDS)
    log.info("WORKER_REAP_SECONDS      = %s", WORKER_REAP_SECONDS)
    log.info("MAX_TURN_ATTEMPTS        = %s", MAX_TURN_ATTEMPTS)
    log.info("POLL_INTERVAL_SECONDS    = %s", POLL_INTERVAL_SECONDS)
    log.info("AFFINITY_TTL_SECONDS     = %s", AFFINITY_TTL_SECONDS)
    log.info("=" * 60)

    conn = psycopg.connect(DATABASE_URL, autocommit=False)
    log.info("connected to Postgres; entering assignment loop")
    try:
        while True:
            try:
                tick(conn)
            except Exception:
                # One bad tick must not kill the loop.
                log.exception("tick failed; rolling back and continuing")
                try:
                    conn.rollback()
                except Exception:
                    log.exception("rollback failed; reconnecting")
                    try:
                        conn.close()
                    except Exception:
                        pass
                    conn = psycopg.connect(DATABASE_URL, autocommit=False)
            time.sleep(POLL_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        log.info("interrupted; shutting down")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
