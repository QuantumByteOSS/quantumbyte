# worker

Python worker for the QuantumByte agent execution model ([RFC 0003](../../docs/rfcs/0003-agent-execution-model.md)).
One of an N-instance fleet, coordinated entirely through Postgres — no Redis, no
broker. Each worker registers itself, heartbeats, claims its assigned `PENDING`
chat messages one at a time (enforcing one-agent-per-project), runs a **warm**
Claude Agent SDK turn, and writes the result back.

Behavior mirrors `apps/web/src/lib/claude-agent.ts`: model `claude-opus-4-8`, a
short conversational system prompt, **no tools**, and the `ANTHROPIC_API_KEY`
fallback trick — a blank or placeholder key is dropped so the SDK subprocess
falls back to the claude.ai login credentials at `~/.claude/.credentials.json`.

## Install

```sh
cd apps/worker
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env   # edit as needed
```

## Run

```sh
.venv/bin/python main.py
```

## Configuration (env / `.env`)

| Variable                | Default                                                          | Notes                                              |
| ----------------------- | --------------------------------------------------------------- | -------------------------------------------------- |
| `DATABASE_URL`          | `postgresql://quantumbyte:quantumbyte@localhost:5432/quantumbyte` | Query params (`?schema=`) are stripped for asyncpg |
| `ANTHROPIC_API_KEY`     | _(unset)_                                                        | Blank/`sk-ant-...` placeholder → login-credential fallback |
| `HEARTBEAT_SECONDS`     | `5`                                                             | Worker liveness heartbeat interval                 |
| `POLL_INTERVAL_SECONDS` | `1`                                                             | Claim-loop poll interval                           |
| `WORKER_ID`             | `<hostname>-<random8>`                                         | Override the auto-generated unique id (set a stable value for affinity across restarts) |

## Running a fleet

Scaling is manual (RFC 0003 "Scaling"): the operator launches or kills worker
processes; nothing autoscales. Run several instances — e.g. `make worker` per
instance — and each self-registers in the `Worker` table within one heartbeat
cycle, becoming assignable immediately.

**Each instance needs a unique id.** The default `<hostname>-<random8>` is unique
on one host, across hosts, and inside containers — so two `python main.py` runs
never clobber each other's heartbeat. The PID is deliberately **not** used: under
Kubernetes the container PID is always 1, useless as an id. The random suffix
means a restart looks like a new worker (affinity resets — it's soft). Set a
stable `WORKER_ID` (e.g. a StatefulSet pod name) to keep affinity across restarts.

## Warm sessions

The worker keeps one persistent `ClaudeSDKClient` per project in memory (a dict),
so consecutive turns for a project skip the cold SDK resume. On first use for a
project it resumes `Project.agentSessionId` if set.

**TODO (documented):** warm-session eviction — a TTL + LRU cap — is not yet
implemented (see the `SessionPool` TODO in `main.py`, RFC 0003
"warm-session-lifecycle"). A burst of distinct projects currently grows the pool
unbounded; eviction only ever costs one cold resume, never correctness.

## Graceful shutdown

On `SIGINT` / `SIGTERM` the worker stops claiming, closes its SDK clients, and
deletes its `Worker` row. All state lives in Postgres, so an in-flight message
(left `PROCESSING`) is swept back to `PENDING` by the orchestrator after a
timeout and re-run — turn handlers re-check status before persisting, so re-runs
are idempotent.
