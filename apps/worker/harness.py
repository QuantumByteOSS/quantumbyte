"""QuantumByte worker — pass 3: business-requirements harness.

Ports the deck-app harness (``workers/tasks/harness``), adapted to this worker's
Postgres-as-truth model. Deck-app stored requirements in a git JSON artifact +
verdicts in Mongo; here both live in Postgres (``HarnessRequirement`` +
``HarnessResult``), already read by the web GET/PUT routes, so the worker writes
straight to those tables.

Runs deterministically (code-triggered, not model-decided) after each turn's
commit/push. The flow, per project:

    gate on product-overview.md → mark harnessRunning →
    (re)derive requirements when the product target moved →
    diff-scope which requirements need re-verifying →
    one read-only structured audit per requirement → upsert verdicts →
    clear harnessRunning

GENERATE (derive requirements) only fires when the product-overview changed this
turn or the table is empty. RUN (verify) is diff-scoped: a requirement is re-checked
only when it has no verdict, is stale, or code it depends on changed since it was
last verified. Each requirement is audited by its own read-only structured SDK run
so one failure never sinks the batch. Fail-open: never raises into the turn.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Literal

import asyncpg
from pydantic import BaseModel, Field, ValidationError
from ulid import ULID

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    ToolUseBlock,
    query,
)

import redis_lock
from workspace import changed_files_since, head_sha, workspace_has_code

log = logging.getLogger("worker.harness")

# Read-only surface for both derive and verify — the harness must never mutate the repo.
READONLY_TOOLS = ["Read", "Glob", "Grep"]
# Bound the per-requirement fan-out so a big requirement set can't open dozens of
# SDK subprocesses at once.
MAX_CONCURRENCY = 4
# A derive + N read-only verify runs; the lock outlives a quick op.
_LOCK_TTL_SECONDS = 300


def _lock_key(project_id: str) -> str:
    return f"harness_run:{project_id}"
PRODUCT_OVERVIEW_PATH = "_doc/product-overview.md"
# Tool-input keys whose values are file paths/patterns — used to attribute reads for
# diff-scoping (watchedPaths).
_PATH_INPUT_KEYS = ("file_path", "path", "pattern", "notebook_path")
_READ_TOOL_NAMES = {"Read", "Glob", "Grep"}


# ── structured-output models ────────────────────────────────────────────────


class DerivedRequirement(BaseModel):
    """One business requirement derived from the product overview."""

    id: str = Field(description="Reuse the exact existing id when this is the same requirement; otherwise a short kebab-case slug")
    excerpt: str | None = Field(default=None, description="Tiny glance-line, under ~8 words, simpler than description")
    description: str = Field(description="One requirement in explain-like-I'm-five language — what a user/business experiences, no technical terms")
    type: Literal["explicit", "hidden"] = Field(description="'explicit' if stated in the overview, 'hidden' if implied by the product category")
    severity: Literal["critical", "high", "medium", "low"] = Field(description="Business impact if unmet")


class RequirementsDoc(BaseModel):
    """Structured-output wrapper — the derive run returns this single object."""

    requirements: list[DerivedRequirement] = Field(default_factory=list)


class HarnessVerdict(BaseModel):
    """Per-requirement verdict (the auditor only ever speaks SUCCESS/FAIL)."""

    result: Literal["SUCCESS", "FAIL"] = Field(description="SUCCESS if the product satisfies the requirement, else FAIL")
    evidence: str | None = Field(
        default=None,
        description="On FAIL, an explain-like-I'm-five description of what the user/business experiences. No file names or code. Null on SUCCESS.",
    )


# ── prompts ─────────────────────────────────────────────────────────────────

_DERIVE_SYSTEM_PROMPT = (
    "You are a product/business analyst — NOT an engineer. You extract a complete, de-duplicated "
    "list of business requirements for a product from its overview. Every requirement is written "
    "the way a product owner would say it: about features, user actions, business rules, and "
    "outcomes — never about code, APIs, databases, schemas, endpoints, or frameworks. Write in "
    "explain-like-I'm-five language: simple everyday words and short sentences. You return ONLY "
    "the structured output requested."
)

_VERIFY_SYSTEM_PROMPT = (
    "You are a meticulous, read-only product auditor. Given ONE business requirement and access to "
    "a repository, you determine whether the product, as built, satisfies that requirement. You read "
    "the actual source to decide, but you never modify anything. You return ONLY the structured "
    "verdict: SUCCESS when the product clearly meets the requirement, FAIL otherwise.\n\n"
    "EVIDENCE VOICE (mandatory): when you FAIL a requirement, write the evidence in explain-like-I'm-five "
    "language — simple everyday words and short sentences, describing what a user or the business "
    "actually experiences. NEVER reference file names, functions, code, APIs, endpoints, or databases.\n"
    "Good: 'A customer can still place an order at an outlet that is closed.'\n"
    "Bad: 'checkout.ts does not check outlet.is_open before calling createOrder().'"
)


def _derive_prompt(overview: str, existing: list[asyncpg.Record]) -> str:
    reusable = [r for r in existing if not r["locked"]]
    locked = [r for r in existing if r["locked"]]
    existing_block = "\n".join(f"- {r['id']}: {r['description']}" for r in reusable) or "(none yet)"
    locked_block = "\n".join(f"- {r['id']}: {r['description']}" for r in locked)
    locked_section = (
        "\n\nLOCKED REQUIREMENTS (the user owns these — do NOT reproduce, reword, or re-emit them; "
        "they are kept exactly as-is and are NOT part of the set you return; only produce requirements "
        f"that are genuinely distinct from every one of them):\n{locked_block}\n"
        if locked
        else ""
    )
    return (
        f"Read `{PRODUCT_OVERVIEW_PATH}` (the product overview) below and derive the full set of "
        "business requirements for this product. You may read the repository source to understand what "
        "the product does, but every requirement you write must be expressed in business terms.\n\n"
        "EXPLAIN-LIKE-I'M-FIVE VOICE (mandatory): write each `description` in the simplest possible "
        "language — short sentences, everyday words — about features, user actions, business rules, and "
        "outcomes. NEVER mention code, functions, APIs, endpoints, databases, schemas, or frameworks.\n"
        "Good: 'A customer cannot check out when the selected outlet is closed.'\n"
        "Bad: 'The /checkout endpoint validates outlet.is_open before creating the order.'\n\n"
        "For each requirement produce: an `excerpt` (tiny glance-line, under ~8 words); a `description` "
        "(fuller detail, same simple language); `type` = 'explicit' when the overview states it, or "
        "'hidden' when it is implied by the product category but not stated; and `severity` "
        "(critical/high/medium/low) by business impact if unmet.\n\n"
        "ID STABILITY (critical): an existing requirement list is given below as `id: description`. When "
        "a requirement you produce is the same one (semantically), REUSE its exact existing id. Only mint "
        "a new short kebab-case id for a genuinely new requirement. Drop requirements that no longer apply.\n\n"
        f"EXISTING REQUIREMENTS (reuse these ids):\n{existing_block}"
        f"{locked_section}\n"
        f"--- {PRODUCT_OVERVIEW_PATH} ---\n{overview}\n"
    )


def _verify_prompt(description: str) -> str:
    return (
        "Decide whether the product built in this repository satisfies the following business "
        "requirement. Read the relevant source to make the call. If it FAILs, explain the problem in "
        "explain-like-I'm-five language — simple words, short sentences, what a user or the business "
        "would experience — with NO file names, code, or technical jargon.\n\n"
        f"REQUIREMENT:\n{description}\n"
    )


# ── structured SDK run ──────────────────────────────────────────────────────


async def _run_structured(
    *,
    prompt: str,
    system_prompt: str,
    schema: dict,
    cwd: str,
    model: str,
    env: dict[str, str],
) -> tuple[dict | None, list[str]]:
    """Run a read-only one-shot SDK query that emits structured JSON output.

    Returns ``(structured_output_dict | None, watched_paths)``. A None dict means the
    run produced no structured output (inconclusive) — the caller records that as
    INCONCLUSIVE rather than a verdict. ``watched_paths`` are the repo-relative files
    the run read, for diff-scoping the next run.
    """
    options = ClaudeAgentOptions(
        model=model,
        system_prompt=system_prompt,
        allowed_tools=READONLY_TOOLS,
        setting_sources=[],  # never read host/project ~/.claude
        permission_mode="bypassPermissions",
        output_format={"type": "json_schema", "schema": schema},
        env=env,
        cwd=cwd,
    )
    structured: dict | None = None
    watched: set[str] = set()
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, ToolUseBlock) and block.name in _READ_TOOL_NAMES:
                    tool_input = block.input if isinstance(block.input, dict) else {}
                    for key in _PATH_INPUT_KEYS:
                        value = tool_input.get(key)
                        if isinstance(value, str) and value.strip():
                            watched.add(value.strip())
        elif isinstance(message, ResultMessage):
            structured = message.structured_output
    return structured, sorted(watched)


# ── Postgres helpers ────────────────────────────────────────────────────────


def _read_overview_sync(cwd: str) -> str:
    try:
        with open(f"{cwd}/{PRODUCT_OVERVIEW_PATH}", encoding="utf-8") as fh:
            return fh.read()
    except (FileNotFoundError, OSError):
        return ""


async def _read_overview(cwd: str) -> str:
    """Product-overview.md content ('' if missing/empty). Read off-thread — it's the
    gate the whole pass hinges on."""
    return await asyncio.to_thread(_read_overview_sync, cwd)


async def _reconcile_requirements(
    pool: asyncpg.Pool, project_id: str, derived: list[DerivedRequirement]
) -> None:
    """Upsert the derived requirement set into ``HarnessRequirement``, deleting rows
    that dropped out. A requirement whose text/metadata changed has its verdict row
    deleted so it re-verifies (no requirement-hash column, so change is detected here).
    New requirements are minted a fresh ULID id; matched ones keep their id.

    Locked rows are user-owned and authoritative: they are never updated or deleted
    here, regardless of what the model produced. A human curated them through the UI,
    so automatic re-derivation derives *around* them (the derive prompt is told they
    are fixed) rather than reverting the person's edit on the next turn.
    """
    rows = await pool.fetch(
        'SELECT id, description, excerpt, type, severity, locked FROM "HarnessRequirement" WHERE "projectId"=$1',
        project_id,
    )
    existing = {r["id"]: r for r in rows}
    existing_ids = set(existing)
    locked_ids = {rid for rid, r in existing.items() if r["locked"]}

    desired_ids: set[str] = set()
    for req in derived:
        # Reuse the id only when the model echoed a real existing one; otherwise mint fresh
        # (ULIDs are globally unique — the LLM's kebab id is project-local and could collide).
        rid = req.id if req.id in existing_ids else str(ULID())
        desired_ids.add(rid)
        # A locked row is the user's; leave its text/metadata exactly as they set it.
        # Keeping rid in desired_ids also protects it from the stale-delete sweep below.
        if rid in locked_ids:
            continue
        db_type = req.type.upper()
        db_sev = req.severity.upper()
        prior = existing.get(rid)
        if prior is None:
            await pool.execute(
                'INSERT INTO "HarnessRequirement"(id,"projectId",excerpt,description,type,severity,"createdAt","updatedAt")'
                " VALUES($1,$2,$3,$4,$5::\"RequirementType\",$6::\"Severity\",now(),now())",
                rid, project_id, req.excerpt, req.description, db_type, db_sev,
            )
        elif (
            prior["description"] != req.description
            or (prior["excerpt"] or None) != (req.excerpt or None)
            or prior["type"] != db_type
            or prior["severity"] != db_sev
        ):
            await pool.execute(
                'UPDATE "HarnessRequirement" SET excerpt=$2,description=$3,type=$4::"RequirementType",'
                'severity=$5::"Severity","updatedAt"=now() WHERE id=$1',
                rid, req.excerpt, req.description, db_type, db_sev,
            )
            # Text/metadata moved → the old verdict no longer applies. Cascade drops the result.
            await pool.execute('DELETE FROM "HarnessResult" WHERE "requirementId"=$1', rid)

    # Drop requirements that no longer exist (cascades their HarnessResult row).
    # Locked rows are never swept even if the model omitted them — a user deleting one
    # is the only thing that removes it.
    stale = existing_ids - desired_ids - locked_ids
    if stale:
        await pool.execute(
            'DELETE FROM "HarnessRequirement" WHERE "projectId"=$1 AND id = ANY($2::text[])',
            project_id, list(stale),
        )


async def _set_running(pool: asyncpg.Pool, project_id: str, running: bool) -> None:
    try:
        await pool.execute('UPDATE "Project" SET "harnessRunning"=$2 WHERE id=$1', project_id, running)
    except Exception:
        log.warning("failed to set harnessRunning=%s for project %s", running, project_id, exc_info=True)


# ── verify selection ────────────────────────────────────────────────────────


async def _needs_verify(project_id: str, req: asyncpg.Record, result: asyncpg.Record | None) -> bool:
    """A requirement is (re)verified when it has no verdict, its last run was
    inconclusive, it is flagged stale, or code it depends on changed since it was
    last verified. Unchanged code + a valid prior verdict → skip (the whole point of
    diff-scoping: don't re-audit what didn't move)."""
    if result is None or result["result"] is None:
        return True
    if result["runStatus"] != "OK" or result["isStale"]:
        return True
    base = result["lastVerifiedSha"]
    if not base:
        return True
    changed = await changed_files_since(project_id, base)
    if changed is None:
        return True  # can't diff → re-verify rather than serve stale
    watched = set(result["watchedPaths"] or [])
    # Precise scope when we recorded reads last time; otherwise coarse: any non-_doc
    # (code) change triggers a re-verify.
    if watched:
        return bool(watched & changed)
    return any(not p.startswith("_doc/") for p in changed)


# ── entry point ─────────────────────────────────────────────────────────────


async def run_harness(
    pool: asyncpg.Pool,
    project_id: str,
    cwd: str,
    *,
    po_changed: bool,
    env: dict[str, str],
    model: str,
    force_verify_all: bool = False,
) -> None:
    """Pass 3: derive + verify business requirements for one project. Fail-open —
    a harness failure must never break the turn that already produced a reply.

    ``po_changed`` = the product-overview changed in this turn's commit (drives the
    GENERATE gate together with an empty requirement table). ``force_verify_all``
    bypasses diff-scoping and re-verifies every requirement — used by the manual
    "Run harness" trigger so the button always produces a full pass. ``env`` /
    ``model`` are passed in from the caller to avoid a circular import on main.
    """
    try:
        overview = await _read_overview(cwd)
        if not overview.strip():
            # No product truth yet → nothing to derive from. No-op until pass 2 authors it.
            log.info("[harness] project %s: no product-overview; skipping", project_id)
            return

        # Per-project lock: collapse the turn-triggered run and a manual "Run harness"
        # into one. None → another run holds it; skip this duplicate.
        lock_key = _lock_key(project_id)
        token = await redis_lock.acquire(lock_key, _LOCK_TTL_SECONDS)
        if token is None:
            log.info("[harness] project %s: lock held; skipping duplicate", project_id)
            return

        await _set_running(pool, project_id, True)
        try:
            existing_rows = await pool.fetch(
                'SELECT id, description, locked FROM "HarnessRequirement" WHERE "projectId"=$1 ORDER BY "createdAt"',
                project_id,
            )

            # ── GENERATE ──────────────────────────────────────────────────────
            # Derive only when the product target moved this turn or nothing exists yet.
            if po_changed or not existing_rows:
                structured, _ = await _run_structured(
                    prompt=_derive_prompt(overview, existing_rows),
                    system_prompt=_DERIVE_SYSTEM_PROMPT,
                    schema=RequirementsDoc.model_json_schema(),
                    cwd=cwd, model=model, env=env,
                )
                if structured is not None:
                    try:
                        doc = RequirementsDoc.model_validate(structured)
                        await _reconcile_requirements(pool, project_id, doc.requirements)
                    except ValidationError:
                        log.warning("[harness] project %s: malformed derive output; keeping existing", project_id, exc_info=True)
                else:
                    log.info("[harness] project %s: derivation inconclusive; keeping existing", project_id)

            # ── RUN (verify) ──────────────────────────────────────────────────
            reqs = await pool.fetch(
                'SELECT id, description FROM "HarnessRequirement" WHERE "projectId"=$1 ORDER BY "createdAt"',
                project_id,
            )
            if not reqs:
                log.info("[harness] project %s: no requirements to verify", project_id)
                return

            # Deterministic fail-all: a workspace with no app code (only _doc/)
            # cannot satisfy ANY business requirement. Recording that without the
            # per-requirement SDK fan-out is honest, instant, and free — and it
            # stops the auditor from hallucinating verdicts off planning docs.
            # watchedPaths stays empty, so the first real code commit re-verifies
            # everything (see _needs_verify's coarse fallback).
            if not await workspace_has_code(project_id):
                sha = await head_sha(project_id)
                log.info(
                    "[harness] project %s: no app code in workspace; failing all %d requirements",
                    project_id, len(reqs),
                )
                for req in reqs:
                    await _upsert_result(
                        pool, req["id"], result="FAIL",
                        evidence="Nothing is built yet — the workspace has no app code, only planning documents.",
                        run_status="OK", sha=sha, watched=[],
                    )
                return

            results = {
                r["requirementId"]: r
                for r in await pool.fetch(
                    'SELECT "requirementId",result,"runStatus","lastVerifiedSha","watchedPaths","isStale"'
                    ' FROM "HarnessResult" WHERE "requirementId" = ANY($1::text[])',
                    [r["id"] for r in reqs],
                )
            }

            if force_verify_all:
                to_run = list(reqs)
            else:
                to_run = [r for r in reqs if await _needs_verify(project_id, r, results.get(r["id"]))]
            if not to_run:
                log.info("[harness] project %s: nothing to re-verify (diff-scoped)", project_id)
                return

            sha = await head_sha(project_id)
            log.info("[harness] project %s: verifying %d/%d requirements", project_id, len(to_run), len(reqs))

            semaphore = asyncio.Semaphore(MAX_CONCURRENCY)

            async def _verify_one(req: asyncpg.Record) -> None:
                try:
                    async with semaphore:
                        structured, watched = await _run_structured(
                            prompt=_verify_prompt(req["description"]),
                            system_prompt=_VERIFY_SYSTEM_PROMPT,
                            schema=HarnessVerdict.model_json_schema(),
                            cwd=cwd, model=model, env=env,
                        )
                    if structured is not None:
                        verdict = HarnessVerdict.model_validate(structured)
                        await _upsert_result(
                            pool, req["id"], result=verdict.result, evidence=verdict.evidence,
                            run_status="OK", sha=sha, watched=watched,
                        )
                    else:
                        await _upsert_result(
                            pool, req["id"], result=None, evidence=None,
                            run_status="INCONCLUSIVE", sha=sha, watched=[],
                        )
                except Exception:
                    log.exception("[harness] verify failed for project %s requirement %s", project_id, req["id"])
                    try:
                        await _upsert_result(
                            pool, req["id"], result=None, evidence=None,
                            run_status="INCONCLUSIVE", sha=sha, watched=[],
                        )
                    except Exception:
                        log.exception("[harness] failed to record INCONCLUSIVE for %s", req["id"])

            # _verify_one never raises → plain gather; one bad requirement can't sink the batch.
            await asyncio.gather(*(_verify_one(r) for r in to_run))
            log.info("[harness] completed for project %s", project_id)
        finally:
            await _set_running(pool, project_id, False)
            await redis_lock.release(lock_key, token)
    except Exception:
        log.exception("[harness] run failed for project %s", project_id)


async def _upsert_result(
    pool: asyncpg.Pool,
    requirement_id: str,
    *,
    result: str | None,
    evidence: str | None,
    run_status: str,
    sha: str | None,
    watched: list[str],
) -> None:
    """Upsert one verdict row (HarnessResult is keyed 1:1 by requirementId). Clears
    the stale flag — this verdict was just recomputed against the current HEAD."""
    await pool.execute(
        'INSERT INTO "HarnessResult"("requirementId",result,evidence,"runStatus","lastVerifiedSha","watchedPaths","runAt","isStale")'
        ' VALUES($1,$2::"HarnessResultValue",$3,$4::"HarnessRunStatus",$5,$6::text[],$7,false)'
        ' ON CONFLICT ("requirementId") DO UPDATE SET'
        ' result=EXCLUDED.result,evidence=EXCLUDED.evidence,"runStatus"=EXCLUDED."runStatus",'
        ' "lastVerifiedSha"=EXCLUDED."lastVerifiedSha","watchedPaths"=EXCLUDED."watchedPaths",'
        ' "runAt"=EXCLUDED."runAt","isStale"=false',
        # Prisma maps `DateTime` to `timestamp without time zone` (UTC naive) — asyncpg
        # rejects a tz-aware value for that type, so strip the offset.
        requirement_id, result, evidence, run_status, sha, watched,
        datetime.now(timezone.utc).replace(tzinfo=None),
    )
