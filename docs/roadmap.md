# Roadmap — Timeline & Milestones

Strategy: **import or roll out, phase by phase.** This repo starts from the architecture and grows capability milestone by milestone — each one lands in the open, in this repo, for the community, clean and spec-first.

## Milestone 0 — Architecture ✅

- [x] Repo, name, org
- [x] License decision (Apache-2.0)
- [x] CONTRIBUTING.md, CODE_OF_CONDUCT.md, community docs
- [x] CI skeleton (lint, typecheck, tests)
- [x] Architecture docs published (component deep-dives in `docs/architecture/`)

**Exit met:** both component architectures documented and building against.

## Milestone 1 — App Generator ✅

The core loop: intent in, working app out.

- [x] Blueprint workspace (`apps/web`): intent captured in chat, agent builds the app in a per-project workspace
- [x] Orchestrator + worker fleet: project→worker affinity, lease-based turn recovery
- [x] Build mandate: every turn must leave the workspace building
- [x] Live app preview with device frames and health checks

**Exit met:** intent → running app, visible live in the workspace.

## Milestone 2 — Harness ✅

Everything the generator produces becomes reproducible and evaluable.

- [x] Business-requirements harness: per-requirement structured verdicts after every agent turn
- [x] Deterministic fail-all when the workspace has no code; INCONCLUSIVE ≠ FAIL
- [x] User-locked requirements survive auto-derivation
- [x] Non-blocking harness scheduling (preempt-and-coalesce) with live verdicts in the UI

**Exit met:** every agent turn is verified against the app's requirements.

## Milestone 3 — Self-host ready

Run the whole stack on your own infra without reading source code.

- [ ] One-command deploy (docker compose / equivalent) for web + orchestrator + worker + Postgres
- [ ] Configuration story: documented env surface, sane defaults, no hidden switches
- [ ] Upgrade + migration path between releases
- [ ] Self-hosting guide in docs

**Exit:** a stranger can stand up QuantumByte from the README alone.

## Milestone 4 — LLM Agent agnostic

No hard-wired provider anywhere in core.

- [ ] Model/agent provider interface stabilized (adapter boundary per design principles)
- [ ] Second provider implemented behind the interface (litmus test)
- [ ] Provider selection via config, per-stage overrides
- [ ] Community-contributed adapter accepted (interface proven from outside)

**Exit:** swap the LLM/agent backend with config only — no core changes.

## Milestone 5 — Concept Editor

New editor: shape the app's concepts — entities, flows, rules — before any code exists. The spec becomes something you *edit*, not just something the LLM emits.

## Milestone 6 — Live Code Editor

New editor: open the generated code in the workspace and edit it live, with changes flowing back through the spec-first contract instead of forking away from it.

## Milestone 7 — Blueprint Editor

New editor: the whole app as a visual blueprint — screens, data, integrations — navigable and editable at the system level.

## Milestone 8 — World-grounded evidence and readiness gates

Today the harness reads the code. The research agenda says that is not enough: a requirement can be satisfied in source and still fail in the world.

- [ ] Evidence from a running app, not just static reading (executed flows, observed behavior)
- [ ] Operational constraints as first-class requirements (latency, cost, data handling, failure modes)
- [ ] Readiness gate: a structured ship/block decision over the full verdict set, not a per-requirement glance
- [ ] Escalation path when the harness is uncertain — INCONCLUSIVE routed to a human, never silently passed

**Exit:** the verdict reflects how the app behaves, not only how it reads.

## Milestone 9 — ConvergenceBench

The evaluation framework for false convergence: does a system *look* ready while important requirements go unsatisfied?

- [ ] Reference tasks with known, deliberately hidden requirement violations
- [ ] Metrics for false convergence (missed requirement rate, false-FAIL rate, evidence quality)
- [ ] Harness-agnostic runner — evaluate other verifier designs, not just ours
- [ ] Published baseline results for the QuantumByte harness

**Exit:** "did the harness catch it?" becomes a number anyone can reproduce.

## Milestone 10 — …and beyond

Community-driven. Propose the next milestone via a design issue or on [Discord](https://discord.gg/zFD35kwHmU). Ideas already circling: more target stacks, more deploy targets, richer eval suites, template/marketplace layer.
