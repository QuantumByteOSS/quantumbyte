Force-touch all files in the workspace `app/` directory to trigger Skaffold's
file watcher and push code changes into the running app preview dev server.

Use this when the user has made code changes (file edits, template
modifications) that should be reflected in the preview but the hot-reload
hasn't picked them up yet.

Note: This tool only applies when the "using-new-app-preview" feature flag
is enabled for the user. When the flag is off, the call is a no-op
(skipped, not an error).
