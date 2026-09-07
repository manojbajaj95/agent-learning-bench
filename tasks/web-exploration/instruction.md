# WebArena Shopping

Read `/app/task.json`. Complete its `intent` on its `start_urls` using the installed `agent-browser` skill and CLI.

Read `/app/notes.md` and `/app/sessions/` when useful. Update `/app/notes.md` with reusable knowledge about the Shopping site, not task-specific answers.

Write `/app/agent_response.json` in the WebArena-Verified schema:

```json
{"task_type":"RETRIEVE|NAVIGATE|MUTATE","status":"SUCCESS","retrieved_data":null,"error_details":null}
```

Use the typed result format requested by the task. Stop after writing the response.
