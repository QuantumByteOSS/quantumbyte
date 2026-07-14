Run `bun run build` and `bun run dev` concurrently in the workspace root
and return their output (build logs + dev server startup logs). `bun run dev`
is killed after a 15-second timeout — just long enough to surface startup
crashes, missing env vars, module-not-found errors, or port conflicts.

If `node_modules/` doesn't exist, runs `bun install` first.

This runs purely in-process against the local workspace checkout. It does NOT
touch the live app preview (use `get_app_preview_logs` for that).

Use when:
  - The user reports the app won't start or crashes immediately.
  - You just scaffolded a new template and want to verify it compiles.
  - You need to see actual runtime errors (TypeScript errors, missing
    dependencies, broken imports) before committing.
  - The preview is broken and you want to isolate whether the problem is
    in the user's code versus the preview infrastructure.

Returns:
  - `install`: stdout from `bun install` (only present when node_modules
    was missing and install was run).
  - `build`: stdout + stderr from `bun run build` (combined, truncated to
    last 150 lines).
  - `dev`: stdout + stderr from `bun run dev` (combined, killed at 15s,
    truncated to last 150 lines).
