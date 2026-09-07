# Kestrel Depot

The environment has one company intranet. Browse it with:

```text
web get <path>
web post <path> field=value ...
```

The home page is `/`. Pages return HTML. Follow the links.

Read `/app/question.md`. Do the job. Write the result to `/app/answer.json`:

```json
{ "answer": "..." }
```

Use a short string. For a form job, write the confirmation code that the site returns.
Quote values that contain spaces. Keep notes in `/app/notes.md` if useful. Past session logs are under `/app/sessions/`.

Stop after writing `/app/answer.json`.
