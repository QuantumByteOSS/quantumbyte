# orchestrator

Single-instance Python service that assigns pending chat messages to workers
(QuantumByte, [RFC 0003](../../docs/rfcs/0003-agent-execution-model.md)).

It coordinates work entirely through PostgreSQL — no Redis, no broker. It reads
and writes the **same** database the web app owns; the schema is owned by Prisma
in `apps/web`, so this process runs DML only and never touches DDL.

Each loop (~1s) it:

1. **Recovers** from dead workers and stalls — unpins projects from dead
   workers, resets stalled `PROCESSING` turns back to `PENDING`, and unassigns
   `PENDING` messages pinned to dead workers.
2. **Assigns** unassigned `PENDING` `USER` messages to live workers, honouring
   project→worker affinity (warm sessions) and the one-agent-per-project
   invariant.

## Run

```sh
pip install -r requirements.txt
python main.py
```

From the repo root you can instead run `make orchestrator` (it uses the venv
created by `make install-orchestrator`).

## Config (env, or a local `.env`)

| Var | Default | Meaning |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql://quantumbyte:quantumbyte@localhost:5432/quantumbyte` | Postgres connection string |
| `WORKER_TIMEOUT_SECONDS` | `30` | A worker is "live" if it heartbeated within this window |
| `WORKER_REAP_SECONDS` | `3600` | A worker with no heartbeat for this long is reaped |
| `POLL_INTERVAL_SECONDS` | `1` | Sleep between assignment loops |
| `MAX_TURN_ATTEMPTS` | `3` | Max retries of a turn before it is failed |
| `AFFINITY_TTL_SECONDS` | `1800` | How long a project stays pinned to its last worker after going idle |
| `PREVIEW_PORT_MIN` | `4100` | Low end of the per-project preview port range |
| `PREVIEW_PORT_MAX` | `4199` | High end of the per-project preview port range |

## Notes

- **Single instance.** If it dies, `PENDING` messages simply wait; nothing is
  lost, and it resumes assigning on restart. Multi-instance orchestrator
  failover is out of scope (RFC 0003).
