---
name: business-requirements
description: Read and hand-edit the app's business requirements — the checklist the harness verifies the built app against. MUST be loaded whenever the user asks to add, change, remove, reword, re-prioritise, or reclassify a business requirement (e.g. "add a requirement that…", "that rule is wrong, fix it", "drop the requirement about X", "make the closed-outlet rule critical"). The requirements are a plain JSON file in the app repo; edit it directly with the file tools, then create the lock marker so the change survives.
---

# Business Requirements

The harness checks the finished app against a list of **business requirements** and gives a
ship / do-not-ship decision. Those requirements live in the app repo as a single JSON file:

```
_doc/business-requirements.json
```

It is a JSON **array**; each entry is one requirement:

```json
{
  "id": "no-checkout-when-closed",
  "excerpt": "No buying from a closed store.",
  "description": "A customer cannot check out when the selected outlet is closed.",
  "type": "explicit",
  "severity": "critical"
}
```

Field rules:

- **`id`** — stable kebab-case slug. **Reuse the existing id** when editing a requirement (never
  renumber). Only mint a new kebab-case id for a genuinely new requirement.
- **`excerpt`** — a tiny glance-line, ideally under ~8 words, clearly shorter than `description`.
- **`description`** — the requirement in **explain-like-I'm-five** language: short sentences,
  everyday words, as if explaining to someone with zero technical background. Describe what a
  person or the business experiences — **never** code, functions, APIs, endpoints, databases,
  schemas, tables, or frameworks. If you catch yourself naming a technical thing, rephrase it as
  what the user or business experiences.
  - Good: "A customer cannot check out when the selected outlet is closed."
  - Good: "Loyalty points are only awarded after an order is completed, never when it is cancelled."
  - Bad: "The /checkout endpoint validates outlet.is_open before creating the order."
- **`type`** — `"explicit"` when the user asked for it directly, `"hidden"` when it is implied by
  the product category but not stated (e.g. preventing double rewards, blocking orders to a
  closed outlet).
- **`severity`** — `"critical"`, `"high"`, `"medium"`, or `"low"`, by business impact if unmet.
  Only `critical` requirements block the ship gate; the rest surface as warnings.

## How to edit (MANDATORY steps)

Requirements are normally **auto-derived** from `_doc/product-overview.md`. To make a hand edit
stick — so the next auto-derivation does not overwrite it — you MUST do BOTH:

1. **Edit the file.** Read `_doc/business-requirements.json`, apply the add / change / remove
   the user asked for (keep it a valid JSON array, preserve unrelated entries and their ids),
   and write it back.
2. **Write the lock marker.** Create/refresh the file
   `_doc/business-requirements.lock` (any short text content). Its mere presence tells the system
   the requirements were hand-edited so auto-derivation stops overwriting them. **Skipping this
   means the user's edit will be silently regenerated away.**

Both files live under `_doc/`, so the end-of-turn commit persists them. After the turn, the
harness automatically re-checks the app against the new requirement set — you do not trigger it.

## When NOT to touch this

- If the user is changing what the **app does** (a feature, a rule in the product), fix the app —
  that is normal build work, and the harness re-checks it afterward. Only edit
  `business-requirements.json` when the user is changing the **requirement text itself** (the
  thing being checked), not the implementation.
- Never invent requirements the user didn't ask for; never delete requirements they didn't
  mention.
