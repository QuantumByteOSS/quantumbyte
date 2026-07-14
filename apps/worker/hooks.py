"""Worker SDK hooks: an advisory per-turn budget countdown + a compaction notice.

Ported from the reference ``agentic_system/hooks`` — trimmed to what this
deployment supports (no goal system, no tiers, no initial-generation), rewired
from websocket → the Postgres/SSE channel, and configured from env (no settings
module).

- **budget_countdown** (PostToolUse): one advisory clock per turn for PARTNER
  (single-agent — no subagents). Purely advisory: nothing denies a tool or
  stops the turn.
- **pre_compact** (PreCompact): flashes a "Compacting conversation…" notice on
  the in-flight assistant row so the FE shows why the stream paused.

All hooks fail open (return ``{}`` / no-op) so a bug never bricks a turn.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any

import asyncpg
from claude_agent_sdk.types import (
    HookContext,
    PostToolUseHookInput,
    PreCompactHookInput,
)

log = logging.getLogger("worker.hooks")

# ── Config (env; 0 disables a dimension) ────────────────────────────────────
TOKEN_BUDGET = int(os.environ.get("AGENT_TURN_TOKEN_BUDGET", "0"))
PARTNER_TIME_BUDGET = int(os.environ.get("AGENT_PARTNER_TIME_BUDGET_SECONDS", "300"))

# Escalation thresholds (fraction of budget remaining).
_PRIORITIZE_THRESHOLD = 0.5
_WRAP_UP_THRESHOLD = 0.2

# ── Directives (single-agent — PARTNER does all the work itself) ─────────────
_PARTNER_PRIORITIZE = (
    "Over half the turn budget is spent — focus on the highest-impact remaining work and keep "
    "tool output lean."
)
_PARTNER_WRAP_UP = (
    "The turn budget is nearly exhausted. Do NOT start large new work: finish the current step, "
    "then tell the user what was done and what remains, and end the turn."
)
_PARTNER_EXHAUSTED = (
    "The turn budget is exhausted. STOP starting new work. Briefly summarize what was completed and "
    "what remains, and end the turn."
)

# Static budget-protocol section appended to the PARTNER system prompt when a
# budget is active. Number-free so it never churns the prompt-cache prefix — the
# live numbers arrive via the [Turn budget] PostToolUse countdown.
BUDGET_PROTOCOL_PROMPT = """

## Turn Budget Protocol

Each turn has one advisory time (and optionally token) budget. After tool calls you will see
a `[Turn budget] … remaining` countdown.

- Plenty left: work normally.
- Over half spent: prioritize the highest-impact work.
- Nearly exhausted: do not start large new work; finish the current step, tell the user what
  is done and what remains, and end the turn.

The budget is advisory — finish an in-flight action cleanly rather than cutting it off — but
never ignore an exhausted countdown."""


def _fmt_clock(seconds: float) -> str:
    s = max(0, int(seconds))
    return f"{s // 60}m{s % 60:02d}s"


@dataclass
class TurnBudgetState:
    """The turn's advisory budget: tokens + one clock."""

    token_budget: int = TOKEN_BUDGET
    time_budget_seconds: int = PARTNER_TIME_BUDGET
    tokens_spent: int = 0
    started_at: float = field(default_factory=time.monotonic)

    @property
    def enabled(self) -> bool:
        return self.token_budget > 0 or self.time_budget_seconds > 0

    def restart_clock(self) -> None:
        self.started_at = time.monotonic()
        self.tokens_spent = 0
        self.time_budget_seconds = PARTNER_TIME_BUDGET

    def add_usage(self, usage: dict[str, Any] | None) -> None:
        if isinstance(usage, dict) and isinstance(usage.get("output_tokens"), int):
            self.tokens_spent += max(0, usage["output_tokens"])

    @property
    def elapsed_seconds(self) -> float:
        return time.monotonic() - self.started_at

    def remaining_fraction(self) -> float:
        fractions: list[float] = []
        if self.token_budget > 0:
            fractions.append((self.token_budget - self.tokens_spent) / self.token_budget)
        if self.time_budget_seconds > 0:
            fractions.append((self.time_budget_seconds - self.elapsed_seconds) / self.time_budget_seconds)
        return max(0.0, min(fractions)) if fractions else 1.0

    def countdown_line(self) -> str:
        parts: list[str] = []
        if self.token_budget > 0:
            parts.append(f"~{max(0, self.token_budget - self.tokens_spent) // 1000}k of {self.token_budget // 1000}k tokens")
        if self.time_budget_seconds > 0:
            parts.append(f"{_fmt_clock(self.time_budget_seconds - self.elapsed_seconds)} of {self.time_budget_seconds // 60}m")
        return f"[Turn budget] {' and '.join(parts)} remaining."


# Current turn's budget per warm-client cache key (= project_id).
_ACTIVE_BUDGETS: dict[str, TurnBudgetState] = {}


def activate_turn_budget(cache_key: str | None, state: TurnBudgetState | None) -> None:
    if cache_key and state is not None:
        state.restart_clock()
        _ACTIVE_BUDGETS[cache_key] = state


def deactivate_turn_budget(cache_key: str | None) -> None:
    if cache_key:
        _ACTIVE_BUDGETS.pop(cache_key, None)


def _tiered(line: str, fraction: float, prioritize: str, wrap_up: str, exhausted: str) -> str:
    if fraction <= 0.0:
        return f"{line} {exhausted}"
    if fraction <= _WRAP_UP_THRESHOLD:
        return f"{line} {wrap_up}"
    if fraction <= _PRIORITIZE_THRESHOLD:
        return f"{line} {prioritize}"
    return line


def build_budget_countdown_hook(cache_key: str | None):
    """PostToolUse hook: inject the shared countdown with tiered directives."""

    async def budget_countdown_hook(
        input_data: PostToolUseHookInput, tool_use_id: str | None, context: HookContext
    ) -> dict[str, Any]:
        try:
            state = _ACTIVE_BUDGETS.get(cache_key) if cache_key else None
            if state is None or not state.enabled:
                return {}
            message = _tiered(state.countdown_line(), state.remaining_fraction(),
                              _PARTNER_PRIORITIZE, _PARTNER_WRAP_UP, _PARTNER_EXHAUSTED)
            return {"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": message}}
        except Exception:
            log.exception("[budget] countdown hook failed — no-op")
        return {}

    return budget_countdown_hook


def build_pre_compact_hook(pool: asyncpg.Pool, project_id: str):
    """PreCompact hook: flash a compaction notice on the in-flight assistant row.

    The row is PROCESSING and streaming; setting its content shows the notice
    until the next token delta overwrites it. Fail-open."""

    async def pre_compact_hook(
        input_data: PreCompactHookInput, tool_use_id: str | None, context: HookContext
    ) -> dict[str, Any]:
        try:
            trigger = input_data.get("trigger", "auto")
            log.info("[pre_compact] compaction starting (trigger=%s) project=%s", trigger, project_id)
            await pool.execute(
                """UPDATE "ChatMessage" SET content=$2
                   WHERE id = (SELECT id FROM "ChatMessage"
                               WHERE "projectId"=$1 AND role='ASSISTANT' AND status='PROCESSING'
                               ORDER BY "createdAt" DESC LIMIT 1)""",
                project_id,
                "_Compacting conversation…_",
            )
        except Exception:
            log.exception("[pre_compact] hook failed — allowing compaction")
        return {}

    return pre_compact_hook
