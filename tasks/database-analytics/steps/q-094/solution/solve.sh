#!/usr/bin/env python3
import json, subprocess
from pathlib import Path
sql = "SELECT COUNT(DISTINCT T1.driverId)\nFROM drivers AS T1\nINNER JOIN results AS T2 ON T1.driverId = T2.driverId\nINNER JOIN races AS T3 ON T3.raceId = T2.raceId\nWHERE T3.name = 'Australian Grand Prix'\n  AND T3.year = 2008\n  AND T1.nationality = 'British'"
raw = subprocess.check_output(['db', 'query', sql], text=True)
rows = json.loads(raw.splitlines()[0])
if len(rows) == 1 and len(rows[0]) == 1:
    answer = rows[0][0]
elif rows and all(len(r) == 1 for r in rows):
    answer = [r[0] for r in rows]
else:
    answer = rows
Path('/app/answer.json').write_text(json.dumps({'answer': answer}) + '\n')
