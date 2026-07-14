# QuantumByte Architecture

> Living document. Everything here is a draft contract for the founding contributor group — challenge it via issues or Discord before code lands.

## System overview

```
                    ┌───────────────────────────────────────────┐
                    │           OPEN CORE (this repo)           │
                    │                                           │
 user intent ──────▶│  ┌────────────┐                           │
 (prompt, form,     │  │    App     │──▶ working app in a       │
  template)         │  │ Generator  │    project workspace      │
                    │  └─────┬──────┘            │              │
                    │        │                   ▼              │
                    │        │        ┌──────────────────────┐  │
                    │        │        │    Requirements      │  │
                    │        │        │      Harness         │  │
                    │        │        │  (read-only verifier)│  │
                    │        │        └──────────┬───────────┘  │
                    │        │                   │              │
                    │        │          verdict + evidence      │
                    │        │                   │              │
                    │  ┌─────▼───────────────────▼───────────┐  │
                    │  │      repair or ship decision        │  │
                    │  └─────────────────┬───────────────────┘  │
                    │                    │                      │
                    │  ┌────────────────┐│                      │
                    │  │ Slide Harness  ││ SlideSpec (IR)       │
                    │  │  + renderers   ││ → renderers + eval   │
                    │  └────────────────┘│                      │
                    └────────────────────┼──────────────────────┘
                             │  stable adapter interfaces
                    ┌────────▼──────────────────────────────────┐
                    │            HOSTED PLATFORM                │
                    │  deploy, tenancy, billing, ops, support   │
                    └───────────────────────────────────────────┘
```

One shared philosophy: **the LLM proposes, the spec is the contract, deterministic code validates and renders.** The builder writes; the verifier only reads. That separation is the point — a harness that could edit the project would be grading its own homework.

## Components

- **[App Generator](docs/architecture/app-generator.md)** — turns intent into a validated, runnable app via a declarative `AppSpec` intermediate representation.
- **Requirements harness** (`apps/worker/harness.py`, `apps/worker/harness_scheduler.py`) — derives business requirements from the product overview, then audits each one independently with a read-only verifier that does not inherit the builder's conversational context. Emits per-requirement `SUCCESS`/`FAIL` verdicts with evidence; records `INCONCLUSIVE` runs separately so uncertainty never becomes a false failure. Scheduling is preempt-and-coalesce behind a per-project Redis lock, so an audit never blocks the next chat turn.
- **[Slide Harness](docs/architecture/slide-harness.md)** — deterministic slide/deck generation: `SlideSpec` IR, pluggable renderers, and the evaluation harness that keeps generation quality measurable.

## Runtime stack

Three apps over one PostgreSQL database, no broker. **web** — Next.js (latest) frontend + backend in TypeScript, Prisma over Postgres — serves both the open core and the generator's reference output. **orchestrator** and **worker** — Python; the worker runs the Claude Agent SDK and the requirements harness, the orchestrator assigns pending messages to workers with project→worker affinity and recovers stalled turns. Coordination is the message table itself (`status` + `assigned_worker`), claimed via `FOR UPDATE SKIP LOCKED`. Redis holds only the per-project harness lock.

## Design principles

1. **Spec-first.** Every generation step produces a declarative, diffable artifact (AppSpec, SlideSpec). The LLM proposes; the spec is the contract; validators decide.
2. **Phase-by-phase rollout.** Capabilities are imported or rolled out milestone by milestone (see the [roadmap](docs/roadmap.md)) — each lands clean, spec-first, with its harness.
3. **Harness before features.** Anything generated must be reproducible and evaluable. The eval harness ships with the generator, not after it.
4. **Pluggable boundaries.** Model providers, target stacks, and deploy targets are adapters behind stable interfaces.

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
├── apps/                    # shipped today
│   ├── web/                 # Next.js frontend + backend (TS)
│   ├── orchestrator/        # task→worker assignment (Python)
│   └── worker/              # Claude Agent SDK runner + requirements harness (Python)
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

`apps/` is what runs today: the blueprint workspace, the worker fleet, and the requirements harness. `packages/` and `examples/` are the target end-state — the extraction of the spec pipeline into standalone, versioned packages lands per the [roadmap](docs/roadmap.md).
