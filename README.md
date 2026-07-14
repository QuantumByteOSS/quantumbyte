# QuantumByte

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Discord](https://img.shields.io/badge/Discord-join%20the%20community-5865F2?logo=discord&logoColor=white)](https://discord.gg/zFD35kwHmU)

**Open-source app builder engine.** Generate working service-automation apps from intent — built for the people closest to the problem, not just the people who can code.

> Status: **pre-public**. Architecture-first phase. Public release target: within 30 days of program start (July 2026). See [docs/roadmap.md](docs/roadmap.md).

## Why open source

The AI app-builder layer is commoditizing. Generating an app from a prompt is becoming a commodity — so rather than pretend otherwise, we're helping it happen. The engine is open. The durable value — deployment, adoption, reliability, running real operations — lives above it.

## What's in this repo

This repo is the **open core**:

| Component | Description | Docs |
|---|---|---|
| App Generator | Intent → AppSpec → generated, validated app | [docs/architecture/app-generator.md](docs/architecture/app-generator.md) |
| Slide Harness | Deterministic slide/deck generation: SlideSpec IR, renderer, eval harness | [docs/architecture/slide-harness.md](docs/architecture/slide-harness.md) |

## Design principles

1. **Spec-first.** Every generation step produces a declarative, diffable artifact (AppSpec, SlideSpec). The LLM proposes; the spec is the contract; validators decide.
2. **Phase-by-phase rollout.** Capabilities are imported or rolled out milestone by milestone (see the [roadmap](docs/roadmap.md)) — each lands clean, spec-first, with its harness.
3. **Harness before features.** Anything generated must be reproducible and evaluable. The eval harness ships with the generator, not after it.
4. **Pluggable boundaries.** Model providers, target stacks, and deploy targets are adapters behind stable interfaces.

## Timeline & roadmap

Where we're headed, in order. Details, checklists, and exit criteria live in [docs/roadmap.md](docs/roadmap.md).

| # | Milestone | What it delivers |
|---|---|---|
| 1 | **App Generator** ✅ | Intent → generated, validated, running app |
| 2 | **Harness** ✅ | Every agent turn verified against the app's requirements |
| 3 | **Self-host ready** | One-command deploy of the whole stack on your own infra |
| 4 | **LLM Agent agnostic** | Pluggable model/agent providers — bring your own LLM |
| 5 | **Concept Editor** | New editor: shape the app's concepts before code exists |
| 6 | **Live Code Editor** | New editor: edit generated code live, in the workspace |
| 7 | **Blueprint Editor** | New editor: visual blueprint of the whole app |
| 8 | **…and beyond** | Community-driven — propose the next milestone via a design issue or [Discord](https://discord.gg/zFD35kwHmU) |

## Getting started

```bash
make install     # deps for web (npm) + orchestrator/worker (pip venvs)
make db-up       # start Postgres
make migrate     # create schema + generate Prisma client
make dev         # run web + orchestrator + worker together (Ctrl-C stops all)
```

Or run each app in its own terminal: `make web` (http://localhost:3000), `make orchestrator`, `make worker` (start several for a fleet). `make help` lists every target.

Full walkthrough — prerequisites, secrets, service topology, and troubleshooting — in **[docs/running.md](docs/running.md)**.

## Architecture

Start at [ARCHITECTURE.md](ARCHITECTURE.md).

## Community

Join us on **[Discord](https://discord.gg/zFD35kwHmU)** — design discussion, questions, and coordination for the founding group. Or follow along and DM [@kevin.pantasdo](https://www.threads.com/@kevin.pantasdo) on Threads.

## Contributing

Founding contributor group is intentionally small for now. Interested? Say hi on [Discord](https://discord.gg/zFD35kwHmU) or DM [@kevin.pantasdo](https://www.threads.com/@kevin.pantasdo). Start with [CONTRIBUTING.md](CONTRIBUTING.md); all participation is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). Security issues: see [SECURITY.md](SECURITY.md).

## License

[Apache-2.0](LICENSE). Contributions are accepted under the same license.
