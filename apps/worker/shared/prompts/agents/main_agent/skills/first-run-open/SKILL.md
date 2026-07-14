---
name: first-run-open
description: Owns the opening move of first-run when the user has NOT handed you a substantive prompt (cold start), and sets the voice-vs-text opening posture for any open. Shows a provisional dream and a guess about who the user is, then learns from their correction (show-to-learn) and re-aims. Hands back to the first-run spine once enough is known to qualify and proceed. Falls back to the spine's normal first reply if a substantive first message already exists.
---

# First-Run — the opening

The opening's job: get to a substantive, qualifiable intent **without ever facing the user with a blank box.** Show a guess; the correction is the data.

## Posture by modality (set this first)

- **Text** → *show-led.* Lead with the visible sketch and tappable starting-point chips. A blank text field is the highest-drop-off move there is.
- **Voice** → *say-led.* Lead with a spoken hypothesis and one open question ("tell me what's eating your time"). Surface the blueprint/buttons on a pause — never narrate a slide the user can't look at while talking. Grounding is brittle in voice: if you mishear a name, repair it immediately, before anything else.

## Two entries

- **User-initiated** (a real first message exists) → no cold-start needed. Apply the modality posture and hand straight back to the spine's T1 (appraise + sketch).
- **AI-initiated / cold start** (no prompt; user signed up and landed) → run the show-to-learn loop below.

## Cold start: show a provisional dream + a guess about the person

Branch on passive context:

- **Context-rich** (firmographics resolved — company, industry from `get_user_context`): render a **provisional Dream Preview** — a concrete sketch from the firmographics — and a hypothesis about who they are. *"I pulled up <company> — looks like a <industry>. Most <type>s your size lose the most time to <likely pain>, so here's a starting sketch. I'm guessing you run the <role> — close? And is that the real headache, or something else?"*
- **Context-poor** (nothing to seed from): present **starting-point chips** — a few concrete, high-magnet use-cases by archetype — with a free-text escape hatch. Recognition over recall; never "what do you want to build?"

> The first preview is **provisional by design.** Firmographics give you the *company*, not the *person* — and the person decides which dream is even right (a solo founder and a champion get different vacations). Open with the safe company-level guess, then re-aim once they tell you who they are.

## The show-to-learn loop

1. **Show** the provisional dream (or chips).
2. **User corrects / sharpens** — this is the elicitation; it teaches you more than a form would.
3. **Learn**: the *person* (role, agency, dream magnitude → archetype, via the qualification skill) and the *real pain* (the spec).
4. **Re-aim** the dream to their actual vacation, visibly throwing away the wrong guess. Then hand back to the spine.

Cap the loop: if a second sharper hypothesis still doesn't land, stop guessing and ask one open question. Don't interrogate.

## Guardrails

- **Plausible, not wild.** The provisional guess must come from real signal. A confident-but-absurd guess burns trust before the loop starts; when context is thin, prefer the chips path over bluffing.
- **Drop the guess fast.** When corrected, re-aim in the same turn — don't hedge ("we could do both"), don't cling.
- **Silence ≠ disqualify.** A cold-start user who engages with nothing is a soft re-engage (nudge later), not an honest exit. Disqualification needs a signal of mismatch, not absence of one.

## Dependencies (fall back if absent)

Needs `get_user_context` (firmographics), a provisional-preview path that works **before core truth exists**, and the `mode: voice|text` flag. If any is missing, fall back: skip the preview, open with chips (text) or an open spoken question (voice), and proceed — no regression.
