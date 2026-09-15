# Formula 1 database

The environment has one SQLite database of Formula 1 data.

You cannot open the database file with Python, sqlite3, or any other program.
Those paths are blocked. Query it only with:

```text
db query "<sql>"
```

`db query` runs one read-only SQL statement and prints JSON rows.
Use ordinary SQL to inspect tables (for example `sqlite_master` and `PRAGMA`).

Read `/app/question.md`. It has the question and an **Answer format** line.
Find the answer. Write it to `/app/answer.json`:

```json
{ "answer": ... }
```

Follow the Answer format line exactly. The verifier strips whitespace and compares.
Do not add extra fields, extra names, or a different unit.

Keep notes in `/app/notes.md` if useful.
Past session logs are under `/app/sessions/`.

Stop after writing `/app/answer.json`.
