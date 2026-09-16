#!/usr/bin/env python3
import json, subprocess
from pathlib import Path
sql = "SELECT T1.nationality FROM drivers AS T1 INNER JOIN results AS T2 ON T2.driverId = T1.driverId WHERE T2.fastestLapSpeed IS NOT NULL AND TRIM(T2.fastestLapSpeed) != '' ORDER BY CAST(T2.fastestLapSpeed AS REAL) DESC LIMIT 1"
raw = subprocess.check_output(['db', 'query', sql], text=True)
rows = json.loads(raw.splitlines()[0])
if len(rows) == 1 and len(rows[0]) == 1:
    answer = rows[0][0]
elif rows and all(len(r) == 1 for r in rows):
    answer = [r[0] for r in rows]
else:
    answer = rows
Path('/app/answer.json').write_text(json.dumps({'answer': answer}) + '\n')
