AI TASK EXECUTION — node '{{node_title}}' is now IN_PROGRESS.

Task details:
{{node_json}}

Do the code work using Read/Write/Edit/Bash/Glob/Grep directly on the workspace cwd.

When finished (success or failure), call `complete_ai_task` with:
  deck_id={{deck_id}}
  node_id={{node_id}}
  status=success|failure
  summary=<one-line summary of what you changed>
  progress_id={{progress_id}}

Do NOT manually commit or push — the platform handles that automatically after your turn.
