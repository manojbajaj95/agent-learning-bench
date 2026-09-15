#!/usr/bin/env python3
import json, subprocess
from pathlib import Path
sql = "SELECT T2.name\nFROM constructorStandings AS T1\nINNER JOIN constructors AS T2 ON T1.constructorId = T2.constructorId\nWHERE T1.points = 0 AND T1.raceId = 291"
raw = subprocess.check_output(['db', 'query', sql], text=True)
rows = json.loads(raw.splitlines()[0])
if len(rows) == 1 and len(rows[0]) == 1:
    answer = rows[0][0]
elif rows and all(len(r) == 1 for r in rows):
    answer = [r[0] for r in rows]
else:
    answer = rows
Path('/app/answer.json').write_text(json.dumps({'answer': answer}) + '\n')
