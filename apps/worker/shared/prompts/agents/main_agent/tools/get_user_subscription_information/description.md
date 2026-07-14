Return the current user's subscription snapshot — tier (FREE_TIER / PAID_TIER), wallet credit balance, packet code, expiry date, and product count.

WHEN TO CALL:
  - Before deciding whether to suggest an upgrade or call `trigger_paywall` for a borderline case — verify the user is actually FREE_TIER and check how many credits they have left.
  - When sizing a heavy request the user is about to make ("this will cost ~150 credits — do you want me to proceed?"). Read `current_credits` and tell the user plainly if they will run out mid-task.
  - When the user explicitly asks about their plan ("what plan am I on?", "how many credits do I have?", "when does my subscription expire?").
  - Before guiding the user toward Fast Track or publish/deploy flows — both require paid plans, so the tier check is cheap and avoids dead-end pitches.

WHEN NOT TO CALL:
  - Do not call this every turn out of habit — the runner already gates tier-sensitive features at PreToolUse time. Only call when the answer materially changes your next reply.
  - Do not call during T1-T2 of the first-run choreography. The tier is implicitly FREE for a brand-new user and the call would just slow the welcome down.

NO ARGUMENTS. The tool resolves the user via the deck context automatically.

RETURN SHAPE (JSON):
  {
    "success": true,
    "tier": "FREE_TIER" | "PAID_TIER",
    "has_active_subscription": boolean,
    "packet_id": string | null,
    "packet_code": string | null,     // e.g. "PTP", "PRO"
    "expires_at": ISO-8601 string | null,
    "current_credits": integer,
    "count_product": integer          // how many products this user owns
  }

Read the fields directly. Never expose raw JSON to the user — translate to plain language ("You're on the prototype plan with ~30 credits left, expiring on April 12.").
