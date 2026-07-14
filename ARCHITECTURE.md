# QuantumByte Architecture

> Living document. Everything here is a draft contract for the founding contributor group — challenge it via issues or Discord before code lands.

## System overview

```
                    ┌──────────────────────────────────────────┐
                    │              OPEN CORE (this repo)        │
                    │                                          │
 user intent ──────▶│  ┌────────────┐      ┌────────────────┐  │
 (prompt, form,     │  │    App     │      │     Slide      │  │
  template)         │  │ Generator  │      │    Harness     │  │
                    │  └─────┬──────┘      └───────┬────────┘  │
                    │        │                     │           │
                    │   AppSpec (IR)          SlideSpec (IR)   │
                    │        │                     │           │
                    │  ┌─────▼──────┐      ┌───────▼────────┐  │
                    │  │ Validators │      │   Renderers    │  │
                    │  │ + Eval     │      │   + Eval       │  │
                    │  └─────┬──────┘      └───────┬────────┘  │
                    └────────┼─────────────────────┼───────────┘
                             │  stable adapter interfaces
                    ┌────────▼─────────────────────▼───────────┐
                    │           HOSTED PLATFORM                 │
                    │  deploy, tenancy, billing, ops, support   │
                    └───────────────────────────────────────────┘
```

Two components, one shared philosophy: **the LLM proposes, the spec is the contract, deterministic code validates and renders.**

## Components

- **[App Generator](docs/architecture/app-generator.md)** — turns intent into a validated, runnable app via a declarative `AppSpec` intermediate representation.
- **[Slide Harness](docs/architecture/slide-harness.md)** — deterministic slide/deck generation: `SlideSpec` IR, pluggable renderers, and the evaluation harness that keeps generation quality measurable.

## Runtime stack

Three apps over one PostgreSQL database, no broker. **web** — Next.js (latest) frontend + backend in TypeScript, Prisma over Postgres — serves both the open core and the generator's reference output. **orchestrator** and **worker** — Python; the worker runs the Claude Agent SDK, the orchestrator assigns pending messages to workers with project→worker affinity. Coordination is the message table itself (`status` + `assigned_worker`), claimed via `FOR UPDATE SKIP LOCKED`.

## Shared invariants

1. **Every IR is JSON-schema-validated, versioned, and diffable.** No opaque blobs between pipeline stages.
2. **Generation is replayable.** Given the same spec + seed + pinned model, the pipeline reproduces its artifacts (or reports exactly where nondeterminism entered).
3. **Adapters, not integrations.** Model providers (Anthropic, OpenAI, local), target stacks, storage, and deploy targets sit behind interfaces defined in the open core. Hosted-platform implementations are just another adapter.
4. **Evals are first-class.** Each component ships a golden-set eval harness in-tree; regressions block merge.

## Repo layout (target)

```
quantumbyte/
├── ARCHITECTURE.md
├── docs/
│   ├── architecture/        # component deep-dives (start here)
│   └── roadmap.md
├── apps/
│   ├── web/                 # Next.js frontend + backend (TS)
│   ├── orchestrator/        # task→worker assignment (Python)
│   └── worker/              # Claude Agent SDK runner, N instances (Python)
├── packages/
│   ├── appspec/             # AppSpec schema + validators
│   ├── generator/           # intent → AppSpec → app pipeline
│   ├── slidespec/           # SlideSpec schema + validators
│   ├── slide-harness/       # renderers + eval harness
│   └── adapters/            # provider/stack/deploy interfaces + reference impls
├── examples/                # golden specs, sample apps, sample decks
├── Makefile                 # local run/setup shortcuts
└── docker-compose.yml       # Postgres for local dev
```

`packages/` and `examples/` are the target end-state; code lands per the [roadmap](docs/roadmap.md). An early `apps/web` blueprint workspace already exists ahead of the packaged pipeline.
