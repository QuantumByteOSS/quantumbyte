# Task Batch — Workspace Persistence, Worker Runtime, App Preview, Chat Input

Date: 2026-07-14
Status: DONE — all 10 tasks landed 2026-07-14 (Flows A, C, B, D, E in that order)

- Flow C: `Project.previewPort` allocated by the orchestrator with the pin
  (PREVIEW_PORT_MIN..MAX, default 4100–4199), cleared by every unpin path; the
  worker's PreviewManager serves the clone (npm run dev / static fallback) and
  dies with the affinity. Ping route: GET /api/projects/[id]/preview.
- Flow B (T1): the per-turn stage → commit → push pipeline already existed; added
  the .gitignore guard so preview build artifacts (node_modules/, .next/, …)
  never get committed by the turn's `git add -A`.
- Flow D: AppPreview rewritten — hidden/starting/ready states, iPhone 17 + tablet
  PNG frames (iframe under the transparent screen cutout; rects measured from the
  assets' alpha channel), CSS desktop chrome, mobile/tablet/desktop toggle,
  ResizeObserver fit. Verified in-browser (all modes × all states).
- Flow E (T9): attachments upload to minio via POST /api/projects/[id]/attachments
  (Asset rows, 5 files × 10 MB cap), referenced as markdown links in the chat
  message body so the worker pipeline needs no attachment awareness; Voice Mode
  hidden until it works. Verified end-to-end (upload → minio URL fetch → message).

- T2: verified done-as-designed. Chat turns already run through the warm per-project
  `ClaudeSDKClient` (`SessionPool`). The remaining `query()` sites are deliberate
  one-shots (commit-message, reconcile, harness — see J5); migrating them into the
  warm client would pollute the chat transcript.
- T3: implemented. `Project.affinityExpiresAt` (idle TTL, default 1800s, env
  `AFFINITY_TTL_SECONDS`); orchestrator routes new projects only to workers with no
  pin (capacity 1), sets/refreshes TTL on assignment, expires quiescent pins in
  `recover()`; worker refreshes TTL after each activity and runs an affinity watch
  loop that evicts the warm client when its pin drops. Verified end-to-end against
  live Postgres (capacity-1 routing, TTL set, expiry sweep, freed-worker reuse).
- T10: verified done-as-designed. `claim_loop` is strictly serial per worker:
  SDK turn → reconcile → commit/push → harness, all awaited before the next claim;
  cross-worker overlap blocked by the affinity pin + `NOT harnessRunning` guard.
Context: QuantumByte open-source, pre-release. Breaking changes acceptable; no migration burden.

---

## The 10 tasks (as requested, verbatim intent)

| # | Task | Notes from codebase scan |
|---|------|--------------------------|
| T1 | Auto commit + push user-workspace to GitHub on every change | `apps/worker/workspace.py` manages workspaces; no auto-commit today |
| T2 | Worker uses `ClaudeSDKClient` | Partially done: client pool exists (`apps/worker/main.py:301`); `harness.py:184` and `main.py:129,207` still use `query()` |
| T3 | Worker: max 1 affinity until expiry; retain same `ClaudeSDKClient` while affinity live, waiting for next chat | Affinity pin exists in orchestrator (`apps/orchestrator/main.py:165`); client pool keyed by project already — needs expiry semantics + capacity=1 enforcement |
| T4 | Orchestrator wires affinity → worker WITH open-port info; worker serves project preview at `localhost:port`; port released when affinity expires | New. Port allocation + lifecycle tied to affinity row |
| T5 | Platform ping-test polls the port; on success render right-side App Preview | New. Poll from web app |
| T6 | App Preview states: Hidden (default), Info (port allocated, ping fails), Preview (port allocated, ping OK) | New UI state machine |
| T7 | App Preview casing = iPhone 17 PNG frame | Asset in place at `apps/web/public/devices/iphone17.png` |
| T8 | Preview mode toggle: mobile / tablet / desktop; tablet casing PNG | Tablet asset in place (`tablet.png`); desktop has no asset — plain CSS browser-chrome frame |
| T9 | ChatBox: add attachments support; hide voice mode | `apps/web/src` chat components |
| T10 | Per user chat, worker runs serially: (1) ClaudeSDKClient turn, (2) ClaudeAgentSDK harness check (mechanism per deck-app) | Harness pass-3 already runs after each turn (commit d73b508, `apps/worker/harness.py`); deck-app mechanism = per-requirement read-only structured verdict, fail-open, redis lock, INCONCLUSIVE ≠ FAIL |

---

## Follow-up batch (2026-07-14, after first e2e feedback)

- **F1 — pipeline visibility.** `ChatMessage.stage` (USER row: AGENT → RECONCILING →
  COMMITTING) + `ChatMessage.activity` (ASSISTANT row: live tool line from the
  SDK's ToolUseBlocks, e.g. "Editing page.tsx", "Running `npm install`"). FE shows
  "Waiting for a builder…" while PENDING, the activity line while streaming, and
  stage copy for the post-turn pipeline. Fixed the thinking-overwrite bug: a
  multi-step turn emits one ThinkingBlock per API step and only the last survived;
  now all blocks are joined into a timeline.
- **F2 — preempt-and-coalesce harness scheduler** (`apps/worker/harness_scheduler.py`).
  Harness runs as a background task; the claim loop no longer awaits it and the
  `NOT harnessRunning` chat-claim guard is gone — chat is never blocked behind an
  audit. A new turn preempts (cancels) the in-flight run before touching the clone;
  preempted manual runs re-queue themselves. Sound because the harness is read-only,
  fail-open, upserts verdicts per requirement, and cancelled requirements stay
  UNVERIFIED (never FAIL). The final turn's harness always completes.

## Grouping by flow

### Flow A — Worker runtime & session lifecycle (T2, T3, T10)
One coherent change: the worker's execution model.
- T2: migrate remaining `query()` call sites to the persistent `ClaudeSDKClient` (chat turn path). Harness stays on one-shot runs by design (see judgment J5).
- T3: enforce worker capacity = 1 live affinity; affinity carries TTL; while unexpired, keep the same connected `ClaudeSDKClient` idle between chats; teardown client on expiry.
- T10: strict serial pipeline per user message: SDK client turn → harness check. Already mostly wired; ensure ordering guarantee + no overlap with next message.

### Flow B — Workspace persistence (T1)
- Commit + push after each mutating turn (not per file write — see J1). Push to project's GitHub repo, fail-open, async.

### Flow C — Preview infrastructure (T4, T5)
- T4: orchestrator allocates port from a range when pinning affinity; stores it with the pin; worker starts the project's dev server on that port; kills server + releases port when affinity expires (same lifecycle object as the SDK client — J3).
- T5: web app polls health of `localhost:port`; result drives preview state.

### Flow D — Preview UI (T6, T7, T8)
- T6: three-state right panel: Hidden / Info / Preview.
- T7: iPhone 17 PNG frame around iframe.
- T8: mobile/tablet/desktop toggle; tablet PNG frame; desktop = CSS frame.

### Flow E — Chat input (T9)
- Attachments (upload → land in worker workspace → referenced in prompt), hide voice mode button.

Dependency graph:

```
A (runtime lifecycle) ──► C (preview infra needs affinity+lifecycle) ──► D (preview UI needs ping state)
B (git push)  — independent, small
E (chatbox)   — independent, small
```

---

## Judgments (stated, debatable)

- **J1 — commit granularity.** "Every change" implemented as *end of each mutating agent turn*, debounced, not per-file-write. Per-write commits produce hundreds of junk commits and race the agent mid-edit. One commit per turn = meaningful history, message derivable from the turn. Push async with retry; push failure never blocks the turn (pre-release, nothing lost locally).
- **J2 — affinity expiry.** TTL-based (e.g. 30 min idle, refreshed on each chat). Expiry event is the single teardown point: disconnect SDK client, kill preview server, release port, unpin in DB. One lifecycle, no partial states.
- **J3 — port lifecycle owner.** Orchestrator allocates (it owns the affinity row; single allocator avoids races across workers). Worker binds/serves. Port column lives on the affinity pin so "port gone when affinity gone" is a foreign-key fact, not a cleanup job.
- **J4 — ping test path.** Web app server-side route proxies the health check (`GET /api/preview/health?project=…` → `localhost:port`). Browser-direct fetch to `localhost:port` works only when user and server share a machine — true today, but proxying costs one route and survives the move to real hosts. Poll interval ~2s while panel visible, backoff when failing.
- **J5 — harness stays one-shot.** Deck-app mechanism (read-only, per-requirement structured verdict, fail-open, INCONCLUSIVE ≠ FAIL) is deliberately session-per-verdict. Do NOT run harness through the long-lived chat client — separate `ClaudeAgentSDK` run keeps the auditor unbiased by chat context and keeps the client's session history clean.
- **J6 — device frames.** Copy PNGs into `apps/web/public/devices/`; do not cross-reference another repo. Screen area = absolutely-positioned iframe scaled inside PNG's screen bounds. Desktop mode: minimal CSS browser chrome (no asset provided; drawing one is cheap and theme-aware).
- **J7 — attachments.** Upload to web app → persist under project workspace (`attachments/` dir) → message metadata carries paths → worker includes them in the turn prompt. Images pass natively to the SDK; other files referenced by path. No external object storage pre-release.
- **J8 — preview state machine.** Single derived state: `hidden` (no port on affinity) → `info` (port set, last ping failed/never succeeded) → `preview` (ping OK). Ping regression after success → back to `info` with "restarting…" copy, don't flash to hidden.

---

## Priority proposal

1. **Flow A** — foundation; C depends on its lifecycle object; T2/T3 half-built so cheapest to finish now before drift.
2. **Flow C** — unlocks the whole preview feature; backend-only, testable with curl.
3. **Flow D** — user-visible payoff; pure frontend once C ships.
4. **Flow B** — small, independent; slot anywhere, do early if git history of user workspaces is wanted during testing.
5. **Flow E** — independent UX polish; last.

Suggested order: **A → C → B → D → E** (B slipped before D because it's ~1 file and protects test-phase work).
