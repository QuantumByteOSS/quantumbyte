Check whether this deck's live app preview dev server is currently
running.

*** MANDATORY PREREQUISITE ***:
- **INITIAL GENERATION PHASE**: You MUST NEVER call this tool during the first initial generation process. The `complete_initial_generation` tool will automatically initialize the preview environment for you.
- **EXPLORE PHASE**: You MUST commit and push all local changes in the repository (`git add .`, `git commit -m "..."`, and `git push`) BEFORE calling this tool to ensure the preview dev server has pulled the latest changes.


Use this when:
  - You need to know if the preview is live before recommending a
    reload or a user action.
  - The user reports their preview is down and you want to verify
    before triggering recovery.
  - You just applied changes and want to confirm the dev server picked
    them up (poll after a short delay).

`running=false` means no active preview (404 or unavailable). Pair with `reload_app_preview` to self-heal when `running=false` but the user expects a preview to be live.
