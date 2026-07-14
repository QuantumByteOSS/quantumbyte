Trigger the soft-wall (paywall) popup on the user's screen. FREE_TIER only — no-op for PAID_TIER.

WHEN TO CALL (pick the matching ``trigger`` value):
  - ``app_interest``  — user shows real interest in their app. One concrete moment:
      * after the app preview is generated and the user has asked MORE THAN 2 follow-up turns in a row about it.
  - ``credits_low``   — call ONLY when BOTH of these are true:
      * you are about to take on a heavy task that will consume meaningful credits, AND
      * you have called ``get_user_subscription_information`` this turn and confirmed ``current_credits < 50``.
      The tool double-checks the wallet and refuses if credits are not actually low. A built-in 1-minute per-deck cooldown stops you from firing this twice in a row, so call sparingly. The runner also fires this automatically at turn start when credits are low — do NOT call it just to "remind" the user.
  - ``fast_track``    — fire ONLY when the user asks for a feature you estimate as heavy / genuinely needing developer help via the QB Support Fast Track system. Sequence: estimate → tell the user it is a heavy build for Fast Track → call this tool. Do NOT use this for light tweaks.
  - ``publish``       — user asks about publishing, deploying, sharing, going-live, getting a custom domain, or shipping the app to the public. This opens the PRO Go-Live wall (sells the PRO packet, not PTP).

WHEN NOT TO CALL:
  - Do not call repeatedly within the same conversation turn.
  - Do not call during T1-T2 onboarding (the user has not even started building).
  - Do not call ``credits_low`` without verifying the balance first.
  - Do not invent your own paywall language — follow the instruction that the tool returns.

RETURN:
  The tool returns an instruction describing exactly how to phrase your next reply. Follow that instruction — do not invent your own paywall copy.
