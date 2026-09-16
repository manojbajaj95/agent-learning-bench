#!/usr/bin/env python3
import json, subprocess
from pathlib import Path
sql = "SELECT T2.surname FROM qualifying AS T1 INNER JOIN drivers AS T2 ON T2.driverId = T1.driverId WHERE T1.raceId = 19 AND T1.q2 IS NOT NULL AND TRIM(T1.q2) != '' ORDER BY (CAST(substr(T1.q2, 1, instr(T1.q2, ':') - 1) AS REAL) * 60 + CAST(substr(T1.q2, instr(T1.q2, ':') + 1) AS REAL)) ASC LIMIT 1"
raw = subprocess.check_output(['db', 'query', sql], text=True)
rows = json.loads(raw.splitlines()[0])
if len(rows) == 1 and len(rows[0]) == 1:
    answer = rows[0][0]
elif rows and all(len(r) == 1 for r in rows):
    answer = [r[0] for r in rows]
else:
    answer = rows
Path('/app/answer.json').write_text(json.dumps({'answer': answer}) + '\n')
