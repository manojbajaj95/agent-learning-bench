#!/usr/bin/env python3
import json, subprocess
from pathlib import Path
sql = "SELECT CAST(COUNT(*) AS REAL) / 10 AS annual_average \nFROM races \nWHERE year BETWEEN 2000 AND 2009 \nAND year IS NOT NULL"
raw = subprocess.check_output(['db', 'query', sql], text=True)
rows = json.loads(raw.splitlines()[0])
if len(rows) == 1 and len(rows[0]) == 1:
    answer = rows[0][0]
elif rows and all(len(r) == 1 for r in rows):
    answer = [r[0] for r in rows]
else:
    answer = rows
Path('/app/answer.json').write_text(json.dumps({'answer': answer}) + '\n')
