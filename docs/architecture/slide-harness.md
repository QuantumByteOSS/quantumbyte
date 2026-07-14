# Slide Harness Architecture

> Draft v0.1. The slide harness is the deterministic backbone for AI deck generation: a slide IR, pluggable renderers, and an evaluation harness that makes "did the deck get worse?" a CI question instead of a vibe.

## Goal

LLMs are good at deck *content* and bad at deck *geometry*. The harness splits the two: models emit a constrained `SlideSpec`, deterministic code renders and scores it.

## Components

```
 content intent ──▶ [Composer (LLM)] ──▶ SlideSpec (IR)
                                             │
                              ┌──────────────┼──────────────┐
                              ▼              ▼              ▼
                        [Layout solver] [Renderer(s)]  [Eval harness]
                              │              │              │
                        resolved boxes   HTML / PPTX /  scores, diffs,
                        (deterministic)  PDF / PNG      golden compare
```

### SlideSpec (IR)

JSON-schema-validated, versioned deck description:

```
SlideSpec
├── meta            # deck id, spec_version, theme ref
├── theme           # design tokens: type scale, palette, spacing, grid
├── slides[]
│   ├── layout      # named archetype (title, split, comparison, timeline…)
│   ├── regions[]   # semantic content slots: role + content, no coordinates
│   └── notes
└── assets[]        # images/charts by reference, with provenance
```

Key rule: **the model never emits coordinates.** It emits semantic regions on a named layout archetype; the layout solver owns geometry.

### Layout solver

Deterministic constraint pass: archetype + theme grid + content measurements → resolved boxes. Handles overflow (reflow, font-step-down within bounds, or split-slide proposal surfaced as a spec diff — never silent truncation). Pure function: same spec, same output, testable without any model.

### Renderers

`SlideSpec + resolved layout → artifact`, behind one interface. In-tree targets: HTML (canonical, previewable), PNG (for evals), PPTX/PDF (export). Renderer parity is itself under eval — same spec must read the same across targets.

### Eval harness

The reason this component is named "harness":

- **Golden decks** — curated `intent → SlideSpec` and `SlideSpec → render` pairs in `examples/`.
- **Structural checks** — schema conformance, overflow=0, contrast ratios, type-scale adherence, region completeness.
- **Visual regression** — PNG render diffed against goldens (perceptual hash + pixel budget).
- **Model-graded rubric** — content quality (hierarchy, one-idea-per-slide, scannability) scored by a judge model with pinned prompt+version; advisory at first, gating once stable.

Runs in CI on every PR touching composer prompts, solver, renderers, or theme.

## Relationship to the app generator

Same skeleton, shared tooling: LLM → validated IR → deterministic execution → eval gate. The slide harness is deliberately the **first, smallest end-to-end proof** of that architecture — it ships before the generator and de-risks the IR/harness pattern.

## Non-goals (v0)

- Full animation/transition system.
- WYSIWYG editor (spec edits + re-render first; editor is a consumer, not core).
- Pixel-perfect PPTX fidelity — semantic fidelity first.
