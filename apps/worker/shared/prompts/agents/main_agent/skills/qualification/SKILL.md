---
name: qualification
description: Reads qualification signals from the user's input and passive context, sets the archetype and effort mode, and decides whether to proceed up the convince ladder or route to the disqualification skill. Runs alongside the first-run spine from the first substantive message onward. Falls back to "proceed at normal effort" if signals are unavailable.
---

# Qualification

A parallel read, not a gate the user sees. It answers two questions: *should we invest here, and which vacation do we sell?*

## Signals (from input + passive context)

- **real_business** — a concrete operation, not a vague idea.
- **stakes** — money, time, or reputation on the line.
- **agency** — can this person actually decide / act?
- **engagement** — specifics vs hand-waving.
- **realism** — is this in QB's wheelhouse (operational/service apps), not a consumer-megascale fantasy?

Combine into a **Magnet** magnitude (low / medium / high) — Magnet is the dream's pull, the force qualification reads first. High Magnet → **effort_mode: double_down**. Low → light touch or route to disqualification. A **realism** failure caps the whole thing regardless of Magnet — the forces are multiplicative (see the system prompt).

## Archetype (drives which vacation, and how the bears behave)

| Archetype | Tell | Vacation to sell | Bear posture |
|---|---|---|---|
| Solo founder | own checkbook, runs the thing | reclaim time / stop the bleed | practical, plainspoken |
| Champion | in-org advocate, needs sign-off | look good to leadership; load their pitch | ROI-framed; draft the internal case |
| Hobbyist | no commercial pressure | the joy of the thing shipped | peer-to-peer, honest about scope |
| Economic buyer | signs the check directly | risk-down, clear ROI | crisp, numbers-first |

Default to neutral if the archetype flag is absent — never force a label on thin evidence.

## Routing

- magnitude ≥ minimum → proceed; pass archetype + effort_mode to the spine so the convince ladder is tuned.
- magnitude sustained-low OR realism failure → hand to **disqualification**.

## The cost of skipping qualification

If the user skips ahead (or the opening loop didn't gather enough), proceed at neutral effort — but know the convince ladder and the generated app will be generic. That's the visible cost of a thin read; it's acceptable, not ideal.

## Dependencies (fall back if absent)

Needs a `qualification` signal (scored) and an `archetype` flag in context. If absent, fall back to "proceed at normal effort, neutral archetype" — the spine still runs, just untuned. No regression.
