---
name: build-recovery
description: Owns the build wait and build failure. Narrates the generation honestly while it runs, and when it errors, names the failure plainly with a real recovery path instead of a generic "oops". Loads when generation is long or returns an error. The single highest-risk moment for the "it's actually building" belief.
---

# Build-recovery — wait management + failure

The build is the moment the user shifts from evaluating to delighted-or-disappointed. A silent wait or a generic error is where the "it's actually building" belief dies.

## While it runs (wait management)

Narrate the next concrete piece coming online — short, present-tense, plural: *"wiring the booking calendar… setting up reminders… deploying."* Never show "no active activity" or an opaque spinner during the most exciting moment. Tie the narration to *their* app's real pieces, not generic build steps.

## When it fails

A generic "something went wrong, try again" is a belief-erosion event. An honest, specific narration is a belief-*reinforcement* event — a system that sees its own failure and fixes it is the strongest trust signal there is.

1. **Name it with the cause** if you have it: *"the database setup hit a configuration edge case."* If you don't: *"the build stopped partway — I'm not sure why yet, here's what I can try."* Never blame the user.
2. **Offer the real paths**, matched to the cause:
   - transient → simple retry: rebuild directly.
   - scope/spec issue → retry with refined inputs (back to naming/scope, then rebuild).
   - structural mismatch revealed → this may actually be a disqualification; route there.
3. Keep the user's momentum: one short honest line, one clear next move, no doc-length apology.
