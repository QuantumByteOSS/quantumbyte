# QuantumByte

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Discord](https://img.shields.io/badge/Discord-join%20the%20community-5865F2?logo=discord&logoColor=white)](https://discord.gg/zFD35kwHmU)

> **The first open-source Convergence App Builder.**

Generate working service-automation apps from intent, then continuously verify what the AI built against the app's business requirements.

**The model generates. The harness verifies. Humans decide when it is ready to ship.**

## Why QuantumByte exists

AI can produce software that looks finished long before it is actually ready.

The interface may render. The happy path may work. The demo may impress. Yet important requirements can still be missing, misunderstood, or silently broken. We call this **false convergence**.

QuantumByte approaches AI-assisted software development as a continuing loop:

```text
Intent -> Build -> Inspect -> Verify -> Repair -> Decide
```

It does not treat generated code as the final answer. After every agent turn, QuantumByte's built-in requirements harness checks the current app and returns structured verdicts with evidence.

**Vibe coding ends at the demo. Convergence starts with evidence.**

## What ships today

QuantumByte is a working, open-source app builder engine with an integrated business-requirements harness.

### App generation

- Capture the product intent through a conversational workspace.
- Generate and update a working application in a dedicated project repository.
- Keep every completed agent turn in a buildable state.
- Preview the app live with health checks and device frames.
- Coordinate multiple workers with project-to-worker affinity and turn recovery.

### Continuous requirements verification

- Derive business requirements from the product overview.
- Let users add or lock requirements that must remain authoritative.
- Audit every requirement independently using a read-only verifier.
- Return structured `SUCCESS` or `FAIL` verdicts with supporting evidence.
- Record inconclusive runs separately instead of turning uncertainty into a false failure.
- Re-check only requirements affected by relevant code changes.
- Run verification in the background without blocking the next conversation.
- Show live requirement status in the product workspace.

## How it works

```text
User intent
    |
    v
Main agent -> product overview -> engineer agent -> working app
                                              |
                                              v
                                  requirements harness
                                              |
                         +--------------------+--------------------+
                         |                    |                    |
                      verdict              evidence          watched files
                         |                    |                    |
                         +--------------------+--------------------+
                                              |
                                              v
                                      repair or ship decision
```

The builder and verifier are deliberately separated. The builder can edit the project. The harness is read-only and evaluates one business requirement at a time, without inheriting the builder's conversational context.

## Convergence Programming

QuantumByte is an early executable system inspired by **Convergence Programming**, a research framework for AI-assisted programming and agents.

Traditional software generation is often framed as:

```text
specification -> program
```

Convergence Programming studies the larger trajectory:

```text
lossy intent
    -> generated behavior
    -> observation
    -> evidence
    -> repair
    -> readiness decision
    -> action or block
```

The central research problem is false convergence: a system appears ready under visible review while important operational constraints remain undiscovered or unsatisfied.

The current open-source harness implements an initial part of that agenda: continuous verification of generated software against explicit business requirements. It does not yet claim full world-grounded verification, complete production readiness, or the proposed ConvergenceBench evaluation framework.

## Who this is for

### Programmers

Study, run, modify, and extend a real AI app-building system. Build from intent, verify against requirements, and inspect the evidence behind every verdict.

### Researchers

Use QuantumByte as an evolving reference implementation for studying false convergence, requirements preservation, verifier-centric agents, evidence collection, and readiness decisions in AI-generated software.

### Operators and internal builders

Turn a real workflow into an application while keeping the business requirements visible and continuously checked throughout the build.

## Architecture

| Component           | Role                                                                               | Current stack               |
| ------------------- | ---------------------------------------------------------------------------------- | --------------------------- |
| `apps/web`          | Product workspace, chat, live preview, requirements UI                             | Next.js, TypeScript, Prisma |
| `apps/orchestrator` | Project assignment, worker coordination, recovery                                  | Python, PostgreSQL          |
| `apps/worker`       | Agent execution, workspace management, build loop, verification harness            | Python, Claude Agent SDK    |
| PostgreSQL          | Shared source of truth for projects, messages, workers, requirements, and verdicts | PostgreSQL                  |
| Redis               | Per-project harness locking                                                        | Redis                       |

The current worker uses the Claude Agent SDK. A provider-neutral agent boundary and additional model providers are on the roadmap.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the system overview and [docs/running.md](docs/running.md) for the complete local setup.

## Getting started

### Prerequisites

- Node.js and npm
- Python 3
- PostgreSQL
- Redis
- An Anthropic API key for the current worker implementation

### Run locally

```bash
git clone https://github.com/QuantumByteOSS/quantumbyte.git
cd quantumbyte

make install
make db-up
make migrate
make dev
```

The web app runs at [http://localhost:3000](http://localhost:3000). Run `make help` to see the available development commands.

For environment variables, service topology, and troubleshooting, read [docs/running.md](docs/running.md).

## Roadmap

- [x] Intent-to-app generation
- [x] Live application preview and health checks
- [x] Continuous business-requirements harness
- [x] Structured per-requirement verdicts and evidence
- [ ] One-command self-hosting
- [ ] Model and agent provider adapters
- [ ] Concept editor
- [ ] Live code editor
- [ ] Visual blueprint editor
- [ ] World-grounded evidence and readiness gates
- [ ] ConvergenceBench reference tasks and evaluation tooling

See [docs/roadmap.md](docs/roadmap.md) for milestone details.

## Why open source

The AI app-generation layer is commoditizing. Generating more code is not the durable problem.

The harder problem is keeping human intent, AI interpretation, generated behavior, and operational requirements aligned as the system changes.

We are open-sourcing the engine so programmers and researchers can inspect the harness, challenge its assumptions, reproduce its behavior, and help build better ways to determine when AI-generated software is actually ready.

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a contribution. All participation is governed by our [Code of Conduct](CODE_OF_CONDUCT.md).

- Join the [QuantumByte Discord](https://discord.gg/zFD35kwHmU)
- Follow or DM [@kevin.pantasdo](https://www.threads.com/@kevin.pantasdo)
- Report security issues according to [SECURITY.md](SECURITY.md)

## License

QuantumByte is licensed under [Apache License 2.0](LICENSE).
