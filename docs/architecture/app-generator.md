# App Generator Architecture

> Draft v0.1. The generator is a pipeline of pure-ish stages connected by validated, versioned intermediate representations.

## Goal

Turn a non-coder's intent ("I run a clinic, I need appointment booking with WhatsApp reminders") into a working, inspectable, regenerable app — without the user ever reading code.

## Pipeline

```
intent ──▶ [1 Elicit] ──▶ IntentDoc
                              │
       ┌──────────────────────┘
       ▼
 [2 Specify] ──▶ AppSpec (the contract)
       │
       ▼
 [3 Plan] ──▶ BuildPlan (ordered, resumable steps)
       │
       ▼
 [4 Generate] ──▶ artifact tree (code, schema, config)
       │
       ▼
 [5 Validate] ──▶ typed report (schema ✓, build ✓, tests ✓, policies ✓)
       │
       ▼
 [6 Package] ──▶ deployable bundle → handed to a deploy adapter
```

Every arrow is a schema-validated artifact. Any stage can be re-run in isolation from its input artifact — that's what makes the pipeline debuggable, cacheable, and resumable.

### 1. Elicit
Conversational/form-driven capture of what the user actually needs. Output `IntentDoc`: domain, actors, entities, workflows, integrations, constraints — in plain language, confirmed with the user. LLM-heavy stage; the only stage where ambiguity is allowed.

### 2. Specify
`IntentDoc → AppSpec`. AppSpec is the heart of the system: a declarative, JSON-schema-validated description of the app —

```
AppSpec
├── meta          # name, version, spec_version
├── entities      # data model: fields, types, relations, constraints
├── workflows     # state machines: triggers, steps, transitions
├── views         # pages/forms/lists bound to entities & workflows
├── integrations  # declared external capabilities (messaging, calendar, payments)
├── policies      # authz rules, data retention, tenancy hints
└── theme         # branding tokens
```

The spec is the unit of ownership: users edit/regenerate specs, never generated code. Spec versions are diffable → app changes are reviewable by non-coders ("added a reminder step to booking workflow").

### 3. Plan
Deterministic (no LLM): topologically sort spec into `BuildPlan` — migrations before models before views, integration stubs resolved against the adapter registry. Resumable: each step records its input hash; unchanged steps are skipped on regeneration (incremental regen).

### 4. Generate
Executes plan steps against a **target stack adapter**. A stack adapter = templates + codegen rules + runtime conventions for one stack. First reference stack ships in-tree; others are pluggable. Hybrid codegen: deterministic templates for structure, LLM only for leaf-level custom logic — every LLM output constrained by tests generated from the spec.

### 5. Validate
Gate, not advice: schema conformance, compile/build, generated test suite (derived from workflows: every transition gets a test), policy lint (authz coverage, PII handling). Failures route back to stage 4 with structured errors — bounded self-repair loop (N attempts, then surface to user).

### 6. Package
Deployable bundle (OCI image + manifest) handed to a **deploy adapter**. Open core ships a local/docker adapter; the hosted platform is just another adapter. This line is the open-core/hosted boundary.

## Eval harness

Golden `IntentDoc → AppSpec` pairs and golden `AppSpec → app` builds live in `examples/`. CI replays them with pinned models; drift in spec quality or build pass-rate blocks merge. Same harness pattern as the [slide harness](slide-harness.md) — shared tooling.

## Non-goals (v0)

- General-purpose code assistant. This generates *apps of a shape the spec can express*, exceptionally well.
- Arbitrary code editing of generated output. Escape hatches come later, spec-first comes first.
- Multi-stack from day one. One reference stack, done properly.
