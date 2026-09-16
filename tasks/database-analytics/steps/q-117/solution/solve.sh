#!/usr/bin/env python3
import json, subprocess
from pathlib import Path
sql = "SELECT CAST(SUM(IIF(STRFTIME('%Y', T3.dob) < '1985' AND T1.laps > 50, 1, 0)) AS REAL) * 100 / COUNT(*)\nFROM results AS T1\nINNER JOIN races AS T2 ON T1.raceId = T2.raceId\nINNER JOIN drivers AS T3 ON T1.driverId = T3.driverId\nWHERE T2.year BETWEEN 2000 AND 2005"
raw = subprocess.check_output(['db', 'query', sql], text=True)
rows = json.loads(raw.splitlines()[0])
if len(rows) == 1 and len(rows[0]) == 1:
    answer = rows[0][0]
elif rows and all(len(r) == 1 for r in rows):
    answer = [r[0] for r in rows]
else:
    answer = rows
Path('/app/answer.json').write_text(json.dumps({'answer': answer}) + '\n')
