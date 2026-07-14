# Running QuantumByte locally

How to stand up the full stack on your machine and drive it end to end. This is
the **operator / developer** guide — for the system design read
[ARCHITECTURE.md](../ARCHITECTURE.md); for how to contribute changes read
[CONTRIBUTING.md](../CONTRIBUTING.md).

> **Spike-stage.** The `apps/web` blueprint workspace and its agent runtime are an
> exploratory spike running ahead of the phased roadmap. Commands are stable; the
> UI and flows still move. If something here drifts, `make help` and each app's
> `README.md` are the source of truth.

## What you're running

Three apps over one Postgres, no broker — the message table **is** the queue:

```
  Browser ──▶ web (Next.js, :3000) ──┐
                                      │  writes messages
                                      ▼
                              Postgres (:5432)  ◀── the queue (status + assigned_worker)
                                      ▲
              claims work (SKIP LOCKED) │ assigns
                    ┌─────────────────┴─────────────────┐
              orchestrator (Python)              worker (Python, N instances)
              assigns pending msgs               runs the Claude Agent SDK
              to workers, w/ affinity            per project, streams replies
                                                       │
                        ┌──────────────────────────────┼───────────────┐
                        ▼                               ▼               ▼
                   Redis (:6379)                  minio (:9000)    GitHub (per-project repo)
                   harness run lock               generated assets  agent workspace clone
```

- **web** — Next.js frontend + API, Prisma over Postgres. Serves the blueprint
  workspace and owns the schema.
- **orchestrator** — assigns `PENDING` messages to live workers with
  project→worker affinity. Single instance.
- **worker** — runs the Claude Agent SDK against a per-project Git clone. Run
  several for a fleet.
- **Postgres** — primary datastore and the work queue.
- **Redis** — lock store for the harness per-project run lock only (not a broker;
  the worker degrades open if it's down).
- **minio** — S3-compatible store for agent-generated assets.

## Prerequisites

- **Docker + Docker Compose** — Postgres, Redis, minio.
- **Node.js 20+** and **npm** — the web app.
- **Python 3.11+** — orchestrator and worker (each gets its own venv).
- **An Anthropic API key** *or* a `claude.ai` login — the worker uses one to run
  the Agent SDK (see env notes below).
- **A GitHub PAT** (`repo` scope) — the worker creates a private repo per project
  and clones it as the agent workspace.

## First run

```bash
make setup     # env + deps (web npm, orch/worker venvs) + infra + migrations + Prisma client
```

`make setup` is idempotent — safe to re-run. It runs, in order:

| Step | Target | Does |
| --- | --- | --- |
| 1 | `env` | Copies `apps/web/.env.example` → `apps/web/.env` if missing (never clobbers). |
| 2 | `install` | `npm install` (web) + creates Python venvs and `pip install` (orch, worker). |
| 3 | `db-up` | `docker compose up -d --wait` — starts **Postgres, Redis, minio** + creates the `qb-assets` bucket, waits until all healthy. |
| 4 | `migrate` | Applies Prisma migrations. |
| 5 | `generate` | Generates the Prisma client into `apps/web/src/generated/prisma`. |

### Fill in secrets

`make env` only creates the **web** `.env`. The worker and orchestrator read env
from their own `.env` files (or the process environment) — copy their examples:

```bash
cp apps/worker/.env.example       apps/worker/.env
cp apps/orchestrator/.env.example apps/orchestrator/.env
```

Then set, in `apps/worker/.env`:

- **`ANTHROPIC_API_KEY`** — a real `sk-ant-…` key. Or leave the `sk-ant-...`
  placeholder to fall back to your `claude.ai` login at
  `~/.claude/.credentials.json` (only a real-looking key is passed to the SDK).
- **`GIT_PAT`** — a GitHub PAT with `repo` scope. The repo owner is derived from
  the token; no username needed. Required for the agent workspace.

Everything else has a working local default. Full var reference:
[web](../apps/web/.env.example) · [orchestrator](../apps/orchestrator/.env.example) ·
[worker](../apps/worker/.env.example).

## Start it

Everything in one terminal (Ctrl-C stops all three):

```bash
make dev       # starts infra, then web + orchestrator + worker together
```

Or one app per terminal — better for reading logs and running a worker fleet:

```bash
make db-up         # infra (Postgres + Redis + minio)
make web           # http://localhost:3000
make orchestrator
make worker        # repeat in more terminals for a fleet
```

Handy endpoints:

| URL | What |
| --- | --- |
| http://localhost:3000 | web app |
| http://localhost:9001 | minio console (`quantumbyte` / `quantumbyte`) |
| `localhost:5432` | Postgres (`quantumbyte` / `quantumbyte`) |

## End-to-end walkthrough

1. Open http://localhost:3000 and create a project from an intent prompt.
2. The web app writes a `PENDING` message to Postgres.
3. The orchestrator assigns it to a live worker (pinning that project to the
   worker via affinity for `AFFINITY_TTL_SECONDS`).
4. The worker clones the project's GitHub repo, runs the Agent SDK, and streams
   replies + activity back into the chat. Generated assets land in minio and are
   served from `S3_PUBLIC_URL`.
5. The harness derives requirements from the project overview and verifies them
   against the workspace; verdicts show in the blueprint UI.

If nothing moves after you send a prompt, at least one **worker** must be running
and heart-beating — check the worker terminal.

## Stopping and resetting

```bash
make db-down   # stop infra containers (data persists in named volumes)
make clean     # remove node_modules + Python venvs (does not touch the DB)
```

Full wipe including data:

```bash
docker compose down -v   # removes pgdata + miniodata volumes — destroys all local data
```

## Troubleshooting

| Symptom | Likely cause / fix |
| --- | --- |
| Prompt sent, chat never advances | No worker running, or none heart-beating. Start `make worker`. |
| Worker exits on start / auth error | `ANTHROPIC_API_KEY` invalid and no `claude.ai` creds. Set a real key or log in. |
| Worker can't create/clone repo | `GIT_PAT` missing or lacks `repo` scope. |
| `make migrate` fails to connect | Infra not up/healthy. Run `make db-up` and re-run. |
| Generated images 404 | minio not up, or `S3_PUBLIC_URL` not browser-reachable. Check the minio console and the bucket is public-read. |
| Harness never runs / duplicate runs | Redis unreachable — the worker degrades open (runs without the dedup lock). Bring Redis up to restore dedup. |
| Port already in use (3000/5432/6379/9000) | Another process owns it. Stop it, or remap in `docker-compose.yml` / the dev script. |

## Also see

- [ARCHITECTURE.md](../ARCHITECTURE.md) — system design and invariants
- [apps/orchestrator/README.md](../apps/orchestrator/README.md), [apps/worker/README.md](../apps/worker/README.md) — per-app config tables
- [docs/roadmap.md](roadmap.md) — where this is going
