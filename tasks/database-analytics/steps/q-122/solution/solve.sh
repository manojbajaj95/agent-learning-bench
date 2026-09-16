#!/usr/bin/env python3
import json, subprocess
from pathlib import Path
sql = "WITH top3 AS (\n  SELECT code, nationality\n  FROM drivers\n  ORDER BY JULIANDAY(dob) DESC\n  LIMIT 3\n)\nSELECT t.code,\n       (SELECT COUNT(*) FROM top3 WHERE nationality = 'Dutch') AS dutch_count\nFROM top3 AS t\nORDER BY t.code"
raw = subprocess.check_output(['db', 'query', sql], text=True)
rows = json.loads(raw.splitlines()[0])
if len(rows) == 1 and len(rows[0]) == 1:
    answer = rows[0][0]
elif rows and all(len(r) == 1 for r in rows):
    answer = [r[0] for r in rows]
else:
    answer = rows
Path('/app/answer.json').write_text(json.dumps({'answer': answer}) + '\n')
