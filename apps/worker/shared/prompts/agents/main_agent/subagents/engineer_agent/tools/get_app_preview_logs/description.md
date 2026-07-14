Pull the last 300 lines of this deck's preview-attach log. This is
the single best signal for diagnosing why a preview is stuck or failed
— it captures the full attach lifecycle as it happened, including the
`bun run dev` stdout/stderr from the user's own app.

*** MANDATORY PREREQUISITE ***:
- **INITIAL GENERATION PHASE**: You MUST NEVER call this tool during the first initial generation process. The `complete_initial_generation` tool will automatically initialize the preview environment for you.
- **EXPLORE PHASE**: You MUST commit and push all local changes in the repository (`git add .`, `git commit -m "..."`, and `git push`) BEFORE calling this tool to verify the log of the correct commit version.


What's in the log:
  - allowcheck call (whether the project is allowed to attach yet)
  - git clone / git pull of the user's repo
  - .env fetch from the deck app
  - bun install attempts + retries
  - `bun run dev` stdout AND stderr, interleaved (the dev server's own
    crash traces, build errors, port conflicts, etc.)
  - dev-server localhost verification
  - nginx route verification
  - READY / ERROR / restart transitions

Use this when:
  - You want to check the runtime process logs of the project app (literally check the bun run dev logs)
  - The preview is stuck on installing / starting / connecting
    and you need to see what the dev server is actually saying.
  - The user reports the preview is broken — read the tail first, then
    decide whether to reload, fix code, or escalate.
  - You just called `reload_app_preview` and want to verify the
    next attach cleared the prior error.
  - `get_app_preview_status` returned `running=false` and you want the
    last error before recommending a recovery action.

Use small tails (20-50) for a quick scan, the full window for a root-cause read. Lines are chronological (oldest → newest) and timestamped. An empty result means the project has never been attached or the service is unreachable — treat as "no signal", not "everything is fine".

The window is per-project: every fresh attach clears the prior run's log, so what you read here is the current attempt only.
