# Formula 1 database

The environment has one SQLite database of Formula 1 data.

You cannot open the database file with Python, sqlite3, or any other program.
Those paths are blocked. Query it only with:

```text
db query "<sql>"
```

`db query` runs one read-only SQL statement and prints JSON rows.
Use ordinary SQL to inspect tables (for example `sqlite_master` and `PRAGMA`).

Read `/app/question.md`. It has the question and a **Required output** block.
The only scored file is `/app/answer.json`. Write exactly one JSON object:

```json
{"answer": <value>}
```

The Required output block states the value. Follow it exactly.

- Integer: `{"answer": 2}` not `{"answer": "2"}`
- Unique list: drop duplicates and sort as the block says
- Rounded number: two decimal digits, rounded down, no percent sign, unless the block says otherwise
- Do not add extra fields, extra names, a year, or a different unit

The verifier strips whitespace and compares.

Keep notes in `/app/notes.md` if useful.
Past session logs are under `/app/sessions/`.

Stop after writing `/app/answer.json`.
