# WebArena Shopping

Read `/app/task.json`. Complete its `intent` on its `start_urls` using the installed `agent-browser` skill and CLI. Shape `retrieved_data` as a list according to the task `results_schema`, or use `null` when there is nothing to return.

Read `/app/notes.md` and `/app/sessions/` when useful. Update `/app/notes.md` with reusable knowledge about the Shopping site, not task-specific answers.

Do not close the browser or stop HAR capture. The verifier stops capture after you finish.

Write `/app/agent_response.json`:

```json
{"task_type":"retrieve","status":"SUCCESS","retrieved_data":null,"error_details":null}
```

`task_type` is `retrieve`, `navigate`, or `mutate`. `status` must be `SUCCESS`, `NOT_FOUND_ERROR`, or `ACTION_NOT_ALLOWED_ERROR`. Put a short reason in `error_details` when status is not `SUCCESS`. Stop after writing the response.
