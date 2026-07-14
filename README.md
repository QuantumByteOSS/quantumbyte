<p align="center">
  <img src="apps/web/public/logo_qbits_color.png" width="180" alt="QuantumByte" />
</p>

<h1 align="center">Vibe coding is just the beginning.</h1>

<p align="center">
  The open-source Convergence App Builder.<br />
  Generate a working app from intent, then verify every agent turn against its business requirements.
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache%202.0-blue" alt="Apache 2.0 license" /></a>
  <a href="https://discord.gg/zFD35kwHmU"><img src="https://img.shields.io/badge/Discord-join%20the%20founding%20group-5865F2?logo=discord&logoColor=white" alt="Join the founding group on Discord" /></a>
  <img src="https://img.shields.io/badge/status-public%20alpha-f59e0b" alt="Public alpha" />
</p>

<p align="center">
  <a href="#quickstart">Quickstart</a> ·
  <a href="#why-convergence">Why convergence</a> ·
  <a href="#how-the-harness-works">The harness</a> ·
  <a href="https://discord.gg/zFD35kwHmU">Contribute</a>
</p>

> **The model generates. The harness verifies. Humans decide when it is ready.**

QuantumByte is early, working, and intentionally being built in public. We are looking for founding contributors who believe software should be shaped by the people who understand the problem, not only by the people who can code.

**[Join the founding group on Discord](https://discord.gg/zFD35kwHmU)**

## Why convergence

Vibe coding made software creation accessible. That is the breakthrough.

But an app can look finished long before it is ready for real operations. The interface renders. The happy path works. The demo impresses. Important requirements can still be missing, misunderstood, or silently broken.

We call this **false convergence**.

Generation gets you to an app that builds. Convergence asks what comes next:

- Does the app still match the original intent?
- Are its critical business requirements satisfied?
- What evidence supports each verdict?
- What must be repaired before humans trust it?

QuantumByte turns app generation into a continuing loop:

```text
Intent -> Build -> Verify -> Evidence -> Repair or Ready
```

The current open-source release begins with explicit business requirements. After every agent turn, a separate read-only harness checks the app requirement by requirement and returns structured verdicts with evidence.

## What ships today

### App builder

- Conversational intent capture and product overview
- Agent-generated applications in dedicated project repositories
- Build recovery after every completed agent turn
- Live app previews with health checks and device frames
- Worker coordination with project affinity and turn recovery

### Requirements harness

- Requirements derived from the product overview
- User-locked requirements that remain authoritative
- Independent, read-only audits for every requirement
- Structured `SUCCESS` or `FAIL` verdicts with evidence
- `INCONCLUSIVE` recorded separately from genuine failure
- Diff-scoped re-verification when relevant files change
- Non-blocking background runs with live verdicts in the UI

## Quickstart

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

Open [http://localhost:3000](http://localhost:3000). Run `make help` to see all development commands.

For environment variables, service topology, and troubleshooting, read [docs/running.md](docs/running.md).

## How the harness works

```text
User intent
    |
    v
Product overview -> Builder agent -> Working app
                                      |
                                      v
                            Read-only harness
                                      |
                   +------------------+------------------+
                   |                  |                  |
                Verdict            Evidence         Watched files
                   |                  |                  |
                   +------------------+------------------+
                                      |
                                      v
                               Repair or ready
```

The builder and verifier are deliberately separated. The builder can edit the project. The harness evaluates one business requirement at a time without inheriting the builder's conversation, and it cannot modify the repository it is auditing.

## Architecture

- **`apps/web`**: workspace, chat, live preview, and requirements UI using Next.js, TypeScript, and Prisma
- **`apps/orchestrator`**: project assignment, worker coordination, and recovery using Python and PostgreSQL
- **`apps/worker`**: agent execution, build loop, workspace management, and requirements harness using Python and the Claude Agent SDK
- **PostgreSQL**: source of truth for projects, messages, workers, requirements, and verdicts
- **Redis**: per-project harness locking

The current worker uses the Claude Agent SDK. Provider-neutral agent boundaries and additional model providers are on the roadmap.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the system overview.

## Convergence Programming

QuantumByte is an early executable system inspired by **Convergence Programming**, a research framework for AI-assisted programming and agents.

Traditional software generation is often framed as `specification -> program`. Convergence Programming studies the larger trajectory:

```text
lossy intent
    -> generated behavior
    -> observation
    -> evidence
    -> repair
    -> readiness decision
    -> action or block
```

The current harness implements one part of that agenda: continuous verification of generated software against explicit business requirements. It does not yet claim full world-grounded verification, complete production readiness, or the proposed ConvergenceBench evaluation framework.

## Roadmap

- [x] Intent-to-app generation
- [x] Live previews and health checks
- [x] Continuous business-requirements harness
- [x] Per-requirement verdicts and evidence
- [ ] One-command self-hosting
- [ ] Model and agent provider adapters
- [ ] Concept, code, and blueprint editors
- [ ] World-grounded evidence and readiness gates
- [ ] ConvergenceBench reference tasks and evaluation tooling

See [docs/roadmap.md](docs/roadmap.md) for milestone details.

## Why open source

The AI app-generation layer is commoditizing. We would rather help it happen than pretend otherwise.

Generating more code is not the durable problem. The harder problem is keeping human intent, AI interpretation, generated behavior, and operational requirements aligned as the system changes.

We are opening the engine so programmers and researchers can inspect the harness, challenge its assumptions, reproduce its behavior, and help build better ways to decide when AI-generated software is actually ready.

## Contributing

The first contributor group is intentionally small. We are looking for engineers with taste, first-principles thinkers who still ship, and researchers interested in requirements, verification, agents, and human-AI collaboration.

1. **[Join the Discord](https://discord.gg/zFD35kwHmU)** and introduce yourself.
2. Read [CONTRIBUTING.md](CONTRIBUTING.md).
3. Review [docs/roadmap.md](docs/roadmap.md) and propose where you can help.

All participation is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). Report security issues according to [SECURITY.md](SECURITY.md).

## License

QuantumByte is licensed under the [Apache License 2.0](LICENSE).
