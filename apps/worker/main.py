"""QuantumByte worker — runs Claude Agent SDK turns for chat messages.

One of an N-instance fleet (RFC 0003). Coordinates entirely through Postgres:
registers itself in "Worker", heartbeats, then claims one PENDING USER message
at a time (its own, one-agent-per-project) and runs a warm Claude Agent SDK turn.

Mirrors apps/web/src/lib/claude-agent.ts: model claude-opus-4-8, a short
conversational system prompt, NO tools, and the ANTHROPIC_API_KEY fallback trick
so the SDK subprocess falls back to ~/.claude/.credentials.json when no real key
is present.
"""

import asyncio
import json
import logging
import os
import signal
import socket
import time
import urllib.parse
import uuid
from datetime import datetime, timezone
from typing import Awaitable, Callable

import asyncpg
from dotenv import load_dotenv
from ulid import ULID

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    HookMatcher,
    ResultMessage,
    StreamEvent,
    TextBlock,
    ThinkingBlock,
    ToolUseBlock,
    query,
)

# Load .env BEFORE importing local modules — workspace.py (and others) read
# os.environ at import time (GIT_PAT, LOCAL_STORAGE, ...), so dotenv must win first.
load_dotenv()

import aioboto3

from hooks import (
    BUDGET_PROTOCOL_PROMPT,
    TurnBudgetState,
    activate_turn_budget,
    build_budget_countdown_hook,
    build_pre_compact_hook,
    deactivate_turn_budget,
)
import redis_lock
from harness import PRODUCT_OVERVIEW_PATH, run_harness
from harness_scheduler import HarnessScheduler
from preview import PreviewManager
from mcp_servers import S3Config, ToolContext, build_mcp_servers
from prompt_management import PromptKey, get_prompt_text, get_skills
from session_store import PostgresSessionStore
from workspace import (
    commit_and_push,
    ensure_workspace,
    local_path,
    stage_and_diff,
    workspace_has_code,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("worker")

# --- config -----------------------------------------------------------------

DEFAULT_DATABASE_URL = "postgresql://quantumbyte:quantumbyte@localhost:5432/quantumbyte"
DATABASE_URL = os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)
HEARTBEAT_SECONDS = float(os.environ.get("HEARTBEAT_SECONDS", "5"))
POLL_INTERVAL_SECONDS = float(os.environ.get("POLL_INTERVAL_SECONDS", "1"))
# Lease on a claimed turn. Set on claim and renewed every HEARTBEAT_SECONDS for as
# long as the turn runs (lease_renew_loop) — it says "someone is still on this", and
# it is the only thing that keeps the orchestrator from requeueing the turn. Must
# comfortably exceed the renew interval so one slow renew never drops the lease; it
# does NOT bound how long a turn may run.
LEASE_SECONDS = int(os.environ.get("LEASE_SECONDS", "120"))
# Idle TTL for this worker's affinity pin — must match the orchestrator's value.
# The orchestrator owns expiry (it unpins quiescent projects past the TTL); the
# worker refreshes it after each completed activity and reacts to a dropped pin
# by tearing down the warm session (see affinity_watch_loop).
AFFINITY_TTL_SECONDS = int(os.environ.get("AFFINITY_TTL_SECONDS", "1800"))

# Each worker instance needs a unique id (RFC 0003 "Scaling").
# Default = hostname + a random suffix: unique everywhere, including containers
# (PID is always 1 under K8s, so it is useless as an id) and multiple instances
# on one host. This id is random per process, so a restart reads as a brand-new
# worker (affinity resets — fine, it is soft). For affinity that SURVIVES a
# restart, set WORKER_ID to something stable, e.g. a StatefulSet pod name.
WORKER_ID = os.environ.get("WORKER_ID") or f"{socket.gethostname()}-{uuid.uuid4().hex[:8]}"

MODEL = "claude-opus-4-8"
# Cheap model for the throwaway commit-message summarization call.
COMMIT_MSG_MODEL = "claude-haiku-4-5"


def asyncpg_dsn(url: str) -> str:
    """asyncpg rejects query params like `?schema=public` — strip them."""
    parts = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def agent_env() -> dict[str, str]:
    """Mirror claude-agent.ts agentEnv(). A real key looks like `sk-ant-...` and
    is long; the `.env.example` placeholder ("sk-ant-...") and empty strings must
    be treated as absent so the SDK subprocess falls back to the claude.ai login
    credentials (~/.claude/.credentials.json) instead of sending a 401 key.
    """
    key = (os.environ.get("ANTHROPIC_API_KEY") or "").strip()
    valid = len(key) > 20 and "..." not in key
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    if valid:
        env["ANTHROPIC_API_KEY"] = key
    return env


async def generate_commit_message(user_request: str, diff: str) -> str:
    """One-shot cheap-model call: summarize the staged diff into a single
    Conventional Commits subject line. Falls back to a generic message on any
    failure (empty reply, model error) — a bad message must never block the push.
    """
    prompt = (
        "Write ONE Conventional Commits subject line for the change below. "
        "Rules: <=72 chars, imperative mood, no body, no backticks, no quotes, "
        "output only the line.\n\n"
        f"User request:\n{user_request[:1000]}\n\n"
        f"Staged diff:\n{diff[:6000]}"
    )
    options = ClaudeAgentOptions(
        model=COMMIT_MSG_MODEL,
        allowed_tools=[],
        max_turns=1,
        permission_mode="bypassPermissions",
        env=agent_env(),
    )
    text = ""
    try:
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        text = block.text
            elif isinstance(message, ResultMessage):
                if message.result:
                    text = message.result
    except Exception:
        log.warning("commit-message generation failed", exc_info=True)

    first_line = text.strip().splitlines()[0].strip() if text.strip() else ""
    return first_line[:72] or "agent: apply changes"


# --- pass 2: deterministic _doc/product-overview.md reconcile ----------------
#
# Mirrors the deck-app's reconcile_doc_task (workers/tasks/reconcile_doc), scoped
# to `_doc/product-overview.md` ONLY — no creative blueprints, no harness. Authoring
# the product's core-truth doc is owned by the STRATEGIST persona but only runs when
# the main agent chooses to delegate — prompt-driven and unreliable, so the doc ends
# up missing or stale. This makes it deterministic: after every substantive turn a
# standalone STRATEGIST run reconciles the doc against the user's request. The LLM
# writes the content; code owns the trigger. It runs as its own one-shot SDK
# subprocess in the project's clone, so it never pollutes the warm chat session's
# transcript, and its file writes are persisted by the same stage_and_diff →
# commit_and_push that persists the turn.

RECONCILE_TOOLS = ["Read", "Write", "Edit", "Glob", "Grep"]

# The static task directive. Lives in the system prompt (constant across every
# turn) so the whole reconcile system prompt is prompt-cacheable — only the
# per-turn user query, sent as the query() prompt, varies.
_RECONCILE_DIRECTIVE = (
    "\n\n## Reconcile task\n\n"
    "You are running as a code-triggered reconcile step after a chat turn. Your job: "
    "read `_doc/product-overview.md` (create it if it is missing) and update only what "
    "is missing or materially out of date so it reflects the product as it now stands. "
    "If everything is already consistent, change nothing.\n\n"
    "SCOPE: touch `_doc/product-overview.md` and nothing else. Do NOT create or edit "
    "creative blueprints, slides, or any other file.\n\n"
    "The turn's user message is provided as the prompt."
)


def _reconcile_system_prompt() -> str:
    """STRATEGIST persona + the static reconcile directive, scoping it to
    product-overview.md. Constant per process → prompt-cacheable across turns."""
    return (
        get_prompt_text(PromptKey.AGENTS__MAIN_AGENT__SUBAGENTS__STRATEGIST_AGENT__SYSTEM_PROMPT)
        + _RECONCILE_DIRECTIVE
    )


async def reconcile_product_overview(cwd: str, user_query: str) -> None:
    """Reconcile ``_doc/product-overview.md`` via a standalone STRATEGIST run.

    Code-triggered (not model-decided) and fail-open — a reconcile failure must
    never break the turn that already produced a reply. Runs as its own one-shot
    SDK subprocess in the project's clone (STRATEGIST system prompt, file tools
    only, no creative-blueprints skill), so it never pollutes the warm chat
    session's transcript.
    """
    if not (user_query or "").strip():
        return

    options = ClaudeAgentOptions(
        model=MODEL,
        # STRATEGIST persona + static reconcile directive. Constant across turns so
        # the SDK's system-prompt cache block is reused; only the query varies.
        system_prompt=_reconcile_system_prompt(),
        allowed_tools=RECONCILE_TOOLS,
        setting_sources=[],  # never read the host/project ~/.claude
        permission_mode="bypassPermissions",
        env=agent_env(),
        cwd=cwd,
    )
    try:
        async for _message in query(prompt=user_query, options=options):
            pass
    except Exception:
        log.warning("product-overview reconcile failed (cwd=%s)", cwd, exc_info=True)


# --- warm session pool ------------------------------------------------------
#
# One persistent ClaudeSDKClient per project == warm behavior: the SDK subprocess
# stays alive with the conversation in memory between turns, so consecutive turns
# for a project skip the cold resume path.
#
# Lifecycle (RFC 0003 warm-session-lifecycle): a worker holds AT MOST ONE live
# affinity — the orchestrator only routes a project to a worker with no other pin,
# so this pool holds at most one warm client. The client survives idle gaps between
# chats until the affinity pin expires (orchestrator-owned idle TTL); the affinity
# watch loop notices the dropped pin and evicts the client. No LRU cap needed.


def build_options(
    resume_session_id: str | None,
    session_store: PostgresSessionStore,
    cwd: str,
    ctx: ToolContext,
) -> ClaudeAgentOptions:
    """Build the per-turn ``ClaudeAgentOptions``, mirroring the reference
    ``params_builder.build_stream_params`` so later phases slot straight in here.

    P1: infra-independent options (``permission_mode``, ``thinking``, ``stderr``,
    Postgres ``session_store``). P2: full PARTNER ``system_prompt``. P3: the skills
    plugin and the file-tool surface (so the agent can build in ``cwd`` and the
    commit/push flow produces real commits). P4 (v1): the qb-partner / qb-designer
    MCP servers. P4b: the advisory turn-budget + pre-compact hooks.

    Single-agent: PARTNER does everything itself — no subagents, no Task tool.
    """
    # Materialize the skills plugin from shared/prompts (hot-reload) — the SDK
    # loads skills from a plugin dir and filters to ``skill_names``.
    skills_plugin_dir, skill_names = get_skills()

    # PARTNER prompt + the budget-protocol section when a turn budget is active.
    system_prompt = get_prompt_text(PromptKey.AGENTS__MAIN_AGENT__SYSTEM_PROMPT)
    if TurnBudgetState().enabled:
        system_prompt += BUDGET_PROTOCOL_PROMPT

    # Hooks bind to this project's warm client; the countdown reads the running
    # turn's budget from the registry keyed by project id (see hooks.py).
    cache_key = ctx.project_id

    return ClaudeAgentOptions(
        model=MODEL,
        # Full PARTNER system prompt, read fresh from shared/prompts each turn
        # (hot-reload). Injected via the SDK option — no .claude/ dependency.
        system_prompt=system_prompt,
        # File/codegen surface so PARTNER can build directly, plus its qb-partner
        # MCP tools and the qb-designer product/asset tools (single-agent — no
        # subagents, PARTNER handles design work itself).
        allowed_tools=[
            "Read", "Write", "Edit", "Bash", "Glob", "Grep",
            "mcp__qb-partner__about_you_as_ai_agent",
            "mcp__qb-partner__get_project_info",
            "mcp__qb-designer__update_product_title",
            "mcp__qb-designer__update_product_description",
            "mcp__qb-designer__update_product_logo",
            "mcp__qb-designer__generate_image",
            "mcp__qb-designer__list_assets",
            "mcp__qb-designer__get_asset_url",
            "mcp__qb-designer__delete_asset",
        ],
        # In-process MCP servers (qb-partner + qb-designer), both used by PARTNER.
        mcp_servers=build_mcp_servers(ctx),
        # Load ONLY the qb-skills plugin. Empty setting_sources stops the SDK from
        # defaulting to ["user","project"], which would read the host ~/.claude and
        # <cwd>/.claude — foreign skills + a .claude dependency we must never have.
        setting_sources=[],
        plugins=[{"type": "local", "path": str(skills_plugin_dir)}],
        skills=skill_names,  # SDK auto-adds Skill(<name>) to allowed_tools
        resume=resume_session_id,  # cold-resume the project's prior session
        include_partial_messages=True,  # emit StreamEvent deltas for live streaming
        permission_mode="bypassPermissions",  # build agent runs Bash freely in its clone
        # Enable extended thinking so the SDK emits ``thinking_delta`` stream
        # events (rendered as a live reasoning bubble on the FE). ``adaptive``
        # lets the model decide when/how much to think; ``display="summarized"``
        # is required on Opus 4.7+ to receive thinking text, not a signature-only
        # block.
        thinking={"type": "adaptive", "display": "summarized"},
        session_store=session_store,  # Postgres transcript store (fleet cold-resume)
        # Advisory turn-budget countdown (PostToolUse) plus a compaction notice
        # (PreCompact). All fail-open.
        hooks={
            "PostToolUse": [HookMatcher(matcher="", hooks=[build_budget_countdown_hook(cache_key)])],
            "PreCompact": [HookMatcher(matcher="", hooks=[build_pre_compact_hook(ctx.pool, ctx.project_id)])],
        },
        stderr=lambda msg: log.warning("[Claude SDK CLI stderr] %s", msg),
        env=agent_env(),
        cwd=cwd,  # the project's local git clone — agent runs here
    )


def _describe_tool_use(block: ToolUseBlock) -> str:
    """One human-readable line per tool call, streamed to the FE as the turn's
    live activity. Written for a non-technical user — name the artifact being
    touched, not the tool semantics."""
    tool_input = block.input if isinstance(block.input, dict) else {}
    name = block.name
    path = tool_input.get("file_path") or tool_input.get("path") or ""
    basename = str(path).rstrip("/").rsplit("/", 1)[-1] if path else ""
    if name == "Read":
        return f"Reading {basename}" if basename else "Reading the project"
    if name in ("Write", "Edit"):
        return f"Editing {basename}" if basename else "Editing files"
    if name in ("Glob", "Grep"):
        return "Searching the code"
    if name == "Bash":
        command = str(tool_input.get("command") or "").strip().splitlines()[0:1]
        first = command[0] if command else ""
        return f"Running `{first[:60]}`" if first else "Running a command"
    if name == "Skill":
        return f"Using the {tool_input.get('skill', 'skill')} skill"
    if name.startswith("mcp__"):
        return f"Using {name.rsplit('__', 1)[-1].replace('_', ' ')}"
    return f"Using {name}"


class SessionPool:
    def __init__(self, pool: asyncpg.Pool, previews: PreviewManager) -> None:
        self._pool = pool
        self._previews = previews
        self._clients: dict[str, ClaudeSDKClient] = {}
        self._session_store = PostgresSessionStore(pool)
        # Shared S3 config + aioboto3 session for the qb-designer asset tools.
        self._s3cfg = S3Config.from_env()
        self._s3_session = aioboto3.Session()
        # One advisory turn-budget per project (clock restarts each turn).
        self._budgets: dict[str, TurnBudgetState] = {}
        # Projects with work in flight (turn or manual harness). The affinity
        # watch loop must never evict these — an eviction mid-turn kills the SDK
        # subprocess under the running stream.
        self.in_flight: set[str] = set()

    def held_projects(self) -> list[str]:
        """Project ids this pool currently holds a warm client for."""
        return list(self._clients)

    async def evict(self, project_id: str) -> None:
        """Tear down the project's warm client + preview server (affinity gone).

        Port lifetime IS affinity lifetime (RFC 0003 / task T4): the preview dies
        in the same breath as the warm session."""
        client = self._clients.pop(project_id, None)
        self._budgets.pop(project_id, None)
        await self._previews.stop(project_id)
        if client is None:
            return
        try:
            await client.disconnect()
        except Exception:
            log.warning("error closing session for project %s", project_id, exc_info=True)
        log.info("evicted warm session for project %s (affinity gone)", project_id)

    async def get(self, project_id: str, resume_session_id: str | None) -> ClaudeSDKClient:
        client = self._clients.get(project_id)
        if client is not None:
            return client

        # Ensure the project's GitHub repo + local clone exist, then run the
        # agent inside that clone (idempotent — safe on every cold open).
        workspace = await ensure_workspace(project_id)

        # Per-project context the MCP tools close over (DB + S3 + project id).
        ctx = ToolContext(
            project_id=project_id,
            pool=self._pool,
            s3cfg=self._s3cfg,
            s3_session=self._s3_session,
        )
        options = build_options(resume_session_id, self._session_store, str(workspace), ctx)
        client = ClaudeSDKClient(options)
        await client.connect()
        self._clients[project_id] = client
        log.info(
            "opened warm session for project %s (resume=%s)",
            project_id,
            resume_session_id,
        )
        return client

    async def _wrap_query(self, project_id: str, content: str) -> str:
        """Wrap the raw user message with the per-turn CURRENT CONTEXT header
        (product title/status/cwd/workspace/preview), mirroring the reference
        context assembly. Fetched fresh each turn so the model always sees
        current project facts — including whether the workspace still has no app
        code (the BUILD MANDATE's bootstrap trigger) and which port the platform
        serves the preview from. Fail-open: on any error, send the raw content."""
        try:
            row = await self._pool.fetchrow(
                'SELECT title, status, "previewPort" FROM "Project" WHERE id=$1', project_id
            )
            has_code = await workspace_has_code(project_id)
            workspace_state = (
                "contains the app's code — keep it runnable (`npm run dev`, PORT env honored)"
                if has_code
                else "NO APP CODE YET — only planning documents. Bootstrap the product's runnable app THIS TURN (see BUILD MANDATE)."
            )
            port = row["previewPort"] if row else None
            preview_state = (
                f"after your turn the platform runs `npm run dev` here with PORT={port} and shows "
                f"the user a live preview at localhost:{port} — never start a dev server yourself"
                if port
                else "no preview port allocated yet; the platform will run the app for the user once one is"
            )
            return get_prompt_text(
                PromptKey.AGENTS__MAIN_AGENT__USER_QUERY_WITH_CONTEXT_FORMAT,
                project_id=project_id,
                current_product_title=(row and row["title"]) or "(untitled)",
                status=(row and row["status"]) or "(unknown)",
                cwd=str(local_path(project_id)),
                workspace_state=workspace_state,
                preview_state=preview_state,
                user_query=content,
            )
        except Exception:
            log.warning("query context wrap failed for %s", project_id, exc_info=True)
            return content

    async def run_turn(
        self,
        project_id: str,
        resume_session_id: str | None,
        content: str,
        on_delta: Callable[[str], Awaitable[None]] | None = None,
        on_thinking: Callable[[str], Awaitable[None]] | None = None,
        on_activity: Callable[[str], Awaitable[None]] | None = None,
    ) -> tuple[str, str, str | None]:
        """Send `content`, return (assistant_text, thinking_text, session_id).

        When `on_delta` / `on_thinking` are provided they are called with the
        accumulated reply / reasoning text as streaming `text_delta` /
        `thinking_delta` events arrive, so callers can persist both incrementally
        for live streaming. `on_activity` fires with a human-readable line
        ("Editing page.tsx", "Running `npm install`") each time the agent issues
        a tool call — the slow part of a turn, previously invisible to the user.
        """
        client = await self.get(project_id, resume_session_id)

        # Activate this project's advisory turn budget (clock restarts). The
        # budget-countdown hook reads it from the registry.
        budget = self._budgets.setdefault(project_id, TurnBudgetState())
        activate_turn_budget(project_id, budget)

        await client.query(await self._wrap_query(project_id, content))

        text = ""
        thinking_stream = ""  # live delta accumulation (already spans all blocks)
        # Authoritative thinking blocks. A multi-step turn (tool-use loop) emits
        # one ThinkingBlock per API step; keeping only the last one silently
        # discarded the earlier reasoning, so collect them all.
        thinking_blocks: list[str] = []
        session_id: str | None = None
        async for message in client.receive_response():
            if isinstance(message, StreamEvent):
                # Raw Anthropic API stream event. Text/thinking deltas arrive as
                # content_block_delta with a text_delta / thinking_delta payload.
                event = message.event
                if event.get("type") == "content_block_delta":
                    delta = event.get("delta") or {}
                    delta_type = delta.get("type")
                    if delta_type == "text_delta":
                        piece = delta.get("text") or ""
                        if piece:
                            text += piece
                            if on_delta is not None:
                                await on_delta(text)
                    elif delta_type == "thinking_delta":
                        piece = delta.get("thinking") or ""
                        if piece:
                            thinking_stream += piece
                            if on_thinking is not None:
                                await on_thinking(thinking_stream)
            elif isinstance(message, AssistantMessage):
                # Authoritative full blocks (deltas may be absent).
                for block in message.content:
                    if isinstance(block, TextBlock):
                        text = block.text
                    elif isinstance(block, ThinkingBlock):
                        if block.thinking:
                            thinking_blocks.append(block.thinking)
                    elif isinstance(block, ToolUseBlock) and on_activity is not None:
                        await on_activity(_describe_tool_use(block))
            elif isinstance(message, ResultMessage):
                session_id = message.session_id
                budget.add_usage(getattr(message, "usage", None))  # advisory token spend
                if message.subtype != "success":
                    deactivate_turn_budget(project_id)
                    raise RuntimeError(f"agent run failed: {message.subtype}")
                if message.result is not None:
                    text = message.result
        deactivate_turn_budget(project_id)
        thinking = "\n\n".join(thinking_blocks) if thinking_blocks else thinking_stream
        return text, thinking, session_id

    async def close(self) -> None:
        for project_id, client in list(self._clients.items()):
            try:
                await client.disconnect()
            except Exception:
                log.warning("error closing session for project %s", project_id, exc_info=True)
        self._clients.clear()


# --- database ops -----------------------------------------------------------

# Chat has absolute priority over the harness: a running harness no longer blocks
# claiming (the claim loop PREEMPTS the in-flight harness run instead — see
# harness_scheduler.py). Only the one-agent-per-project turn invariant remains.
#
# The claim takes a lease (leaseExpiresAt) and counts the attempt. The lease is this
# worker saying "I am on this turn"; lease_renew_loop keeps pushing it forward until
# the turn ends. Without it the orchestrator has no way to tell a 20-minute build turn
# from an abandoned one, and would requeue the turn under a worker still running it.
CLAIM_SQL = """
UPDATE "ChatMessage"
SET status='PROCESSING',
    "leaseExpiresAt" = now() + make_interval(secs => $2),
    attempts = attempts + 1
WHERE id = (
  SELECT c.id FROM "ChatMessage" c
  WHERE c."assignedWorker" = $1
    AND c.status = 'PENDING'
    AND c.role = 'USER'
    AND NOT EXISTS (
      SELECT 1 FROM "ChatMessage" p
      WHERE p."projectId" = c."projectId" AND p.status = 'PROCESSING')
  ORDER BY c."createdAt"
  FOR UPDATE SKIP LOCKED
  LIMIT 1)
RETURNING id, "projectId", content;
"""

# Manual "Run harness" claim. Atomic: flip harnessRunning on + clear the request +
# pin the project to this worker (so orchestrator recovery can reset a stuck flag by
# dead-worker affinity), with a fresh affinity TTL. One-agent-per-project: never claim
# a project with a turn in flight; the chat CLAIM_SQL's `NOT harnessRunning` guard
# closes the other direction. Capacity 1: claim an UNPINNED project only when this
# worker holds no other pin — pinning a second project would break the
# one-affinity-per-worker invariant the orchestrator enforces on the chat path.
HARNESS_CLAIM_SQL = """
UPDATE "Project"
SET "harnessRunning" = true, "harnessRunRequested" = false, "assignedWorker" = $1,
    "affinityExpiresAt" = now() + make_interval(secs => $2)
WHERE id = (
  SELECT p.id FROM "Project" p
  WHERE p."harnessRunRequested" = true
    AND p."harnessRunning" = false
    AND (
      p."assignedWorker" = $1
      OR (p."assignedWorker" IS NULL AND NOT EXISTS (
            SELECT 1 FROM "Project" q WHERE q."assignedWorker" = $1))
    )
    AND NOT EXISTS (
      SELECT 1 FROM "ChatMessage" m
      WHERE m."projectId" = p.id AND m.status = 'PROCESSING')
  ORDER BY p."updatedAt"
  FOR UPDATE SKIP LOCKED
  LIMIT 1)
RETURNING id;
"""


async def register(pool: asyncpg.Pool) -> None:
    await pool.execute(
        """INSERT INTO "Worker"(id,"lastSeen","createdAt") VALUES($1,now(),now())
           ON CONFLICT (id) DO UPDATE SET "lastSeen"=now()""",
        WORKER_ID,
    )
    log.info("registered worker %s", WORKER_ID)


async def heartbeat_loop(pool: asyncpg.Pool, stop: asyncio.Event) -> None:
    while not stop.is_set():
        try:
            await pool.execute(
                'UPDATE "Worker" SET "lastSeen"=now() WHERE id=$1', WORKER_ID
            )
        except Exception:
            log.warning("heartbeat failed", exc_info=True)
        try:
            await asyncio.wait_for(stop.wait(), timeout=HEARTBEAT_SECONDS)
        except asyncio.TimeoutError:
            pass


async def affinity_watch_loop(
    pool: asyncpg.Pool,
    sessions: "SessionPool",
    harness_sched: "HarnessScheduler",
    stop: asyncio.Event,
) -> None:
    """Tear down warm sessions whose affinity pin is gone.

    The orchestrator owns expiry (recover() unpins quiescent projects past their
    idle TTL, and unpins on reassignment); this is the worker-side reaction. For
    every project this worker holds a warm client for, check the pin still points
    here — if not, evict the client and free the capacity-1 slot. In-flight work
    is never evicted: the orchestrator's expiry sweep excludes projects with a
    PROCESSING turn or a running harness, but the claim races that sweep by design,
    so the in_flight guard closes the window."""
    while not stop.is_set():
        try:
            held = sessions.held_projects()
            if held:
                rows = await pool.fetch(
                    'SELECT id FROM "Project" WHERE id = ANY($1::text[]) AND "assignedWorker" = $2',
                    held,
                    WORKER_ID,
                )
                still_pinned = {r["id"] for r in rows}
                for project_id in held:
                    if project_id not in still_pinned and project_id not in sessions.in_flight:
                        # Pin gone → nothing of this project may keep running here.
                        await harness_sched.preempt(project_id)
                        await sessions.evict(project_id)
        except Exception:
            log.warning("affinity watch failed", exc_info=True)
        try:
            await asyncio.wait_for(stop.wait(), timeout=HEARTBEAT_SECONDS)
        except asyncio.TimeoutError:
            pass


async def lease_renew_loop(pool: asyncpg.Pool, stop: asyncio.Event) -> None:
    """Push forward the lease on every row this worker is currently PROCESSING.

    Covers both rows of a turn — the USER row the orchestrator watches for staleness,
    and the ASSISTANT row being streamed into. As long as this loop runs, the
    orchestrator leaves the turn alone; the moment the worker dies it stops renewing
    and the lease lapses, which is what makes recovery work. The heartbeat is not
    enough on its own: it says the process is alive, not that it is still on this
    turn."""
    while not stop.is_set():
        try:
            await pool.execute(
                """UPDATE "ChatMessage"
                   SET "leaseExpiresAt" = now() + make_interval(secs => $2)
                   WHERE "assignedWorker" = $1 AND status = 'PROCESSING'""",
                WORKER_ID,
                LEASE_SECONDS,
            )
        except Exception:
            log.warning("lease renew failed", exc_info=True)
        try:
            await asyncio.wait_for(stop.wait(), timeout=HEARTBEAT_SECONDS)
        except asyncio.TimeoutError:
            pass


async def claim_one(pool: asyncpg.Pool) -> asyncpg.Record | None:
    """Claim one assigned PENDING USER message inside a transaction."""
    async with pool.acquire() as conn:
        async with conn.transaction():
            return await conn.fetchrow(CLAIM_SQL, WORKER_ID, LEASE_SECONDS)


async def claim_harness_one(pool: asyncpg.Pool) -> str | None:
    """Claim one project with a pending manual harness request. Returns its id (and
    has atomically set harnessRunning=true + cleared the request), or None."""
    async with pool.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(HARNESS_CLAIM_SQL, WORKER_ID, AFFINITY_TTL_SECONDS)
    return row["id"] if row else None


async def refresh_affinity(pool: asyncpg.Pool, project_id: str) -> None:
    """Restart the affinity idle-TTL countdown — the pin lives AFFINITY_TTL_SECONDS
    past the last completed activity (turn or harness run). Guarded on the pin so a
    pin the orchestrator already dropped or moved is never resurrected. Fail-open."""
    try:
        await pool.execute(
            """UPDATE "Project"
               SET "affinityExpiresAt" = now() + make_interval(secs => $2)
               WHERE id = $1 AND "assignedWorker" = $3""",
            project_id,
            AFFINITY_TTL_SECONDS,
            WORKER_ID,
        )
    except Exception:
        log.warning("affinity refresh failed for project %s", project_id, exc_info=True)


async def create_assistant_row(pool: asyncpg.Pool, project_id: str) -> str:
    """Insert the assistant reply row up front (empty, PROCESSING) so the client
    can render a streaming bubble and receive deltas as they land. Returns id.

    Tagged with this worker's id AND born under a lease, so the orchestrator can tell
    a live in-flight stream from an orphan left by a dead worker (see recover()). The
    lease is not optional here: recover() reads a NULL lease on a PROCESSING row as
    lapsed and DELETEs the row as an orphan, and lease_renew_loop only comes round
    every HEARTBEAT_SECONDS — so a row inserted without one is deleted out from under
    the worker still streaming into it, and the reply is lost."""
    assistant_id = str(ULID())
    await pool.execute(
        """INSERT INTO "ChatMessage"(id,"projectId",role,content,thinking,status,"assignedWorker","leaseExpiresAt","createdAt")
           VALUES($1,$2,'ASSISTANT','','','PROCESSING',$3,now() + make_interval(secs => $4),now())""",
        assistant_id,
        project_id,
        WORKER_ID,
        LEASE_SECONDS,
    )
    return assistant_id


async def update_assistant_content(
    pool: asyncpg.Pool, assistant_id: str, content: str
) -> None:
    await pool.execute(
        'UPDATE "ChatMessage" SET content=$2 WHERE id=$1', assistant_id, content
    )


async def update_assistant_thinking(
    pool: asyncpg.Pool, assistant_id: str, thinking: str
) -> None:
    await pool.execute(
        'UPDATE "ChatMessage" SET thinking=$2 WHERE id=$1', assistant_id, thinking
    )


async def set_stage(pool: asyncpg.Pool, user_msg_id: str, stage: str) -> None:
    """Advance the USER turn's pipeline stage (AGENT → RECONCILING → COMMITTING).
    Pure UI affordance streamed to the FE over the shared SSE; fail-open — a
    failed stage write must never affect the turn."""
    try:
        await pool.execute(
            'UPDATE "ChatMessage" SET stage=$2 WHERE id=$1', user_msg_id, stage
        )
        log.info("[turn %s] stage → %s", user_msg_id, stage)
    except Exception:
        log.warning("failed to set stage=%s on message %s", stage, user_msg_id, exc_info=True)


async def set_activity(pool: asyncpg.Pool, assistant_id: str, activity: str) -> None:
    """Persist the assistant row's live tool-activity line AND append it to the
    turn's activity timeline (`activityLog`), which the FE renders as the
    "working…" step feed. Consecutive duplicates are skipped (an agent re-reading
    the same file shouldn't spam the feed). Fail-open."""
    entry = json.dumps([{
        "at": datetime.now(timezone.utc).isoformat(),
        "text": activity,
    }])
    try:
        await pool.execute(
            'UPDATE "ChatMessage" SET activity=$2,'
            ' "activityLog" = coalesce("activityLog", \'[]\'::jsonb) || $3::jsonb'
            ' WHERE id=$1 AND activity IS DISTINCT FROM $2',
            assistant_id, activity, entry,
        )
        log.info("[turn] %s", activity)
    except Exception:
        log.warning("failed to set activity on message %s", assistant_id, exc_info=True)


async def persist_success(
    pool: asyncpg.Pool,
    user_msg_id: str,
    assistant_id: str,
    project_id: str,
    reply: str,
    thinking: str,
    session_id: str | None,
) -> None:
    """Finalize the streamed assistant reply, mark the user message done, persist
    session id — all in one transaction. Idempotency guard: re-check the user
    message is still PROCESSING (the orchestrator may have re-queued a stalled
    turn); if not, drop the assistant row we created to avoid a duplicate."""
    async with pool.acquire() as conn:
        async with conn.transaction():
            status = await conn.fetchval(
                'SELECT status FROM "ChatMessage" WHERE id=$1 FOR UPDATE', user_msg_id
            )
            if status != "PROCESSING":
                log.info(
                    "skipping persist for %s: status is %s (already handled)",
                    user_msg_id,
                    status,
                )
                await conn.execute(
                    'DELETE FROM "ChatMessage" WHERE id=$1', assistant_id
                )
                return
            updated = await conn.execute(
                "UPDATE \"ChatMessage\" SET content=$2, thinking=$3, status='COMPLETED',"
                ' "leaseExpiresAt"=NULL WHERE id=$1',
                assistant_id,
                reply,
                thinking,
            )
            if updated == "UPDATE 0":
                # The row we streamed into is gone — something swept it as an orphan
                # while we were still working. Re-insert rather than drop the reply on
                # the floor: a turn that ran to completion must never end with the user
                # message COMPLETED and no answer beside it.
                log.warning(
                    "assistant row %s vanished mid-turn; re-inserting the reply",
                    assistant_id,
                )
                await conn.execute(
                    """INSERT INTO "ChatMessage"(id,"projectId",role,content,thinking,status,"createdAt")
                       VALUES($1,$2,'ASSISTANT',$3,$4,'COMPLETED',now())""",
                    assistant_id,
                    project_id,
                    reply,
                    thinking,
                )
            await conn.execute(
                "UPDATE \"ChatMessage\" SET status='COMPLETED', \"leaseExpiresAt\"=NULL"
                " WHERE id=$1",
                user_msg_id,
            )
            if session_id:
                await conn.execute(
                    'UPDATE "Project" SET "agentSessionId"=$1 WHERE id=$2',
                    session_id,
                    project_id,
                )


async def persist_failure(
    pool: asyncpg.Pool, user_msg_id: str, assistant_id: str | None, error: str
) -> None:
    """Mark the user turn FAILED (the error renders in the UI off this row) and
    drop any partial assistant row so only the error bubble shows."""
    async with pool.acquire() as conn:
        async with conn.transaction():
            if assistant_id:
                await conn.execute(
                    'DELETE FROM "ChatMessage" WHERE id=$1', assistant_id
                )
            await conn.execute(
                "UPDATE \"ChatMessage\" SET status='FAILED', error=$2,"
                ' "leaseExpiresAt"=NULL WHERE id=$1',
                user_msg_id,
                error[:2000],
            )


# --- main loop --------------------------------------------------------------


async def run_manual_harness(pool: asyncpg.Pool, harness_sched: HarnessScheduler) -> bool:
    """Claim one pending manual harness request and schedule it as a background
    run. Returns True when one was claimed (caller should loop again immediately),
    False when none was pending.

    ``claim_harness_one`` already flipped ``harnessRunning`` on; the runner
    guarantees it is cleared on EVERY exit — including ``run_harness``'s early
    returns (empty overview / lock held) which don't own the flag on the manual
    path, and preemption (a chat arriving mid-run cancels this task; the
    scheduler then re-queues the request). ``force_verify_all`` so the button
    always produces a full pass, not a diff-scoped no-op.
    """
    try:
        project_id = await claim_harness_one(pool)
    except Exception:
        log.warning("harness claim query failed", exc_info=True)
        return False
    if project_id is None:
        return False

    log.info("claimed manual harness run for project %s", project_id)

    async def _run() -> None:
        try:
            await ensure_workspace(project_id)
            await run_harness(
                pool,
                project_id,
                str(local_path(project_id)),
                po_changed=False,
                env=agent_env(),
                model=MODEL,
                force_verify_all=True,
            )
        except Exception:
            log.exception("manual harness run failed for project %s", project_id)
        finally:
            try:
                await pool.execute('UPDATE "Project" SET "harnessRunning"=false WHERE id=$1', project_id)
            except Exception:
                log.warning("failed to clear harnessRunning for project %s", project_id, exc_info=True)
            # Harness run counts as activity — restart the idle-TTL countdown.
            await refresh_affinity(pool, project_id)

    await harness_sched.schedule(project_id, _run, manual=True)
    return True


async def claim_loop(
    pool: asyncpg.Pool,
    sessions: SessionPool,
    previews: PreviewManager,
    harness_sched: HarnessScheduler,
    stop: asyncio.Event,
) -> None:
    while not stop.is_set():
        try:
            row = await claim_one(pool)
        except Exception:
            log.warning("claim query failed", exc_info=True)
            row = None

        if row is None:
            # No chat turn to run — service a pending manual harness request
            # instead (chat has priority: a chat arriving mid-run preempts it).
            if await run_manual_harness(pool, harness_sched):
                continue
            try:
                await asyncio.wait_for(stop.wait(), timeout=POLL_INTERVAL_SECONDS)
            except asyncio.TimeoutError:
                pass
            continue

        user_msg_id = row["id"]
        project_id = row["projectId"]
        content = row["content"]
        log.info("claimed message %s (project %s)", user_msg_id, project_id)

        assistant_id: str | None = None
        sessions.in_flight.add(project_id)
        try:
            # Chat preempts the harness: cancel the project's in-flight run (and
            # wait for its lock release) BEFORE the agent touches the clone, so a
            # read-only audit never observes a half-edited tree. The run is
            # rescheduled after this turn anyway — its verdicts were about to be
            # stale.
            await harness_sched.preempt(project_id)

            project_row = await pool.fetchrow(
                'SELECT "agentSessionId", "previewPort" FROM "Project" WHERE id=$1',
                project_id,
            )
            resume_session_id = project_row["agentSessionId"] if project_row else None
            preview_port = project_row["previewPort"] if project_row else None
            assistant_id = await create_assistant_row(pool, project_id)
            await set_stage(pool, user_msg_id, "AGENT")
            # Cold opens spend up to ~a minute in clone sync + SDK subprocess boot
            # before the first token/tool call arrives — fill that dead air. The
            # agent's first real activity line overwrites this.
            await set_activity(pool, assistant_id, "Setting up your workspace…")

            # Throttle streaming DB writes so a fast token stream doesn't hammer
            # Postgres — the SSE route polls at ~400ms, so ~120ms writes are more
            # than fine and keep the UI fluid. Content and thinking throttle
            # independently so a thinking burst never starves reply writes.
            last_content_write = 0.0
            last_thinking_write = 0.0

            async def on_delta(text: str) -> None:
                nonlocal last_content_write
                now = time.monotonic()
                if now - last_content_write >= 0.12:
                    last_content_write = now
                    await update_assistant_content(pool, assistant_id, text)

            async def on_thinking(text: str) -> None:
                nonlocal last_thinking_write
                now = time.monotonic()
                if now - last_thinking_write >= 0.12:
                    last_thinking_write = now
                    await update_assistant_thinking(pool, assistant_id, text)

            async def on_activity(activity: str) -> None:
                # Tool calls are sparse (one per agent step) — no throttle needed.
                await set_activity(pool, assistant_id, activity)

            reply, thinking, session_id = await sessions.run_turn(
                project_id, resume_session_id, content, on_delta, on_thinking, on_activity
            )

            # Pass 2: deterministic _doc/product-overview.md reconcile (standalone
            # STRATEGIST run, code-triggered not model-decided). Fail-open internally.
            # Runs before the commit below so its writes land in the same commit/push.
            await set_stage(pool, user_msg_id, "RECONCILING")
            await set_activity(pool, assistant_id, "Updating your product docs…")
            await reconcile_product_overview(str(local_path(project_id)), content)

            # Persist the agent's file writes to git BEFORE marking the turn done.
            # Cold opens reset --hard to remote (git-as-truth), so uncommitted work
            # is lost otherwise. Stage first, generate a commit message from the
            # diff, then commit + push. No-op when the agent touched no files.
            #
            # po_changed = did this turn's commit touch the product-overview? It gates
            # the harness GENERATE step (pass 3). Read off the staged diff — no extra git.
            po_changed = False
            await set_stage(pool, user_msg_id, "COMMITTING")
            await set_activity(pool, assistant_id, "Saving your app to GitHub…")
            try:
                diff = await stage_and_diff(project_id)
                if diff.strip():
                    po_changed = f"b/{PRODUCT_OVERVIEW_PATH}" in diff
                    message = await generate_commit_message(content, diff)
                    await commit_and_push(project_id, message)
            except Exception:
                log.warning(
                    "commit/push failed for message %s (project %s)",
                    user_msg_id,
                    project_id,
                    exc_info=True,
                )

            await persist_success(
                pool, user_msg_id, assistant_id, project_id, reply, thinking, session_id
            )
            log.info("completed message %s", user_msg_id)

            # Preview: make the project's dev server match its allocated port
            # (T4). Idempotent per turn — starts it cold, relaunches it if it
            # died, no-ops while it runs (dev servers hot-reload the agent's
            # writes). Runs in the background; never blocks the pipeline.
            await previews.ensure(project_id, str(local_path(project_id)), preview_port)

            # Pass 3: deterministic business-requirements harness — scheduled as a
            # BACKGROUND task (preempt-and-coalesce, see harness_scheduler.py). The
            # claim loop moves on immediately, so the next user chat is never
            # blocked behind the audit; a new turn for this project preempts the
            # run before touching the clone. Fail-open internally.
            turn_po_changed = po_changed
            await harness_sched.schedule(
                project_id,
                lambda: run_harness(
                    pool,
                    project_id,
                    str(local_path(project_id)),
                    po_changed=turn_po_changed,
                    env=agent_env(),
                    model=MODEL,
                ),
            )
        except Exception as exc:
            log.exception("agent turn failed for message %s", user_msg_id)
            try:
                await persist_failure(pool, user_msg_id, assistant_id, str(exc))
            except Exception:
                log.warning("failed to mark message FAILED", exc_info=True)
        finally:
            sessions.in_flight.discard(project_id)
            # Turn finished (either way) — restart the affinity idle-TTL countdown
            # so the warm session survives AFFINITY_TTL_SECONDS of user silence.
            await refresh_affinity(pool, project_id)


async def main() -> None:
    dsn = asyncpg_dsn(DATABASE_URL)
    log.info("worker %s starting (db=%s)", WORKER_ID, dsn)

    pool = await asyncpg.create_pool(dsn, min_size=1, max_size=4)
    previews = PreviewManager()
    sessions = SessionPool(pool, previews)
    harness_sched = HarnessScheduler(pool)
    stop = asyncio.Event()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:  # pragma: no cover — non-unix
            pass

    await register(pool)

    heartbeat = asyncio.create_task(heartbeat_loop(pool, stop))
    leases = asyncio.create_task(lease_renew_loop(pool, stop))
    claim = asyncio.create_task(claim_loop(pool, sessions, previews, harness_sched, stop))
    affinity_watch = asyncio.create_task(affinity_watch_loop(pool, sessions, harness_sched, stop))

    await stop.wait()
    log.info("shutting down worker %s", WORKER_ID)

    for task in (heartbeat, leases, claim, affinity_watch):
        task.cancel()
    await asyncio.gather(heartbeat, leases, claim, affinity_watch, return_exceptions=True)

    await harness_sched.shutdown()
    await sessions.close()
    await previews.stop_all()
    await redis_lock.close()
    try:
        await pool.execute('DELETE FROM "Worker" WHERE id=$1', WORKER_ID)
    except Exception:
        log.warning("failed to deregister worker", exc_info=True)
    await pool.close()
    log.info("worker %s stopped", WORKER_ID)


if __name__ == "__main__":
    asyncio.run(main())
