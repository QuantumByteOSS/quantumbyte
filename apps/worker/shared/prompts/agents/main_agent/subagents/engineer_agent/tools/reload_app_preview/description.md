Hard-reload the user's live app preview (the dev server backing this
deck). Always forces a full restart of the dev server — does not rely
on the preview service's auto-detection of "needs reload".

*** MANDATORY PREREQUISITE ***:
- **INITIAL GENERATION PHASE**: You MUST NEVER call this tool during the first initial generation process. The `complete_initial_generation` tool will automatically initialize the preview environment for you.
- **EXPLORE PHASE**: You MUST commit and push all local changes in the repository (`git add .`, `git commit -m "..."`, and `git push`) BEFORE calling this tool. The preview service clones/pulls from the remote repository to run the app, so reloading without pushing will compile old/incorrect code.


Use this when:
  - You changed environment variables or app config and the running dev
    server hasn't picked them up.
  - The preview is broken, unresponsive, or stuck on an old build.
  - A scaffold injection or dependency change requires the dev server to
    reload.
  - There is a code change and the user still doesn't see the changes.

`success=false` means the preview service refused the reload (unreachable, internal error) — surface it to the user, don't silently swallow it. A 404 (nothing running) is treated as no-op success.
