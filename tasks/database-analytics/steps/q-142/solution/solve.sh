#!/usr/bin/env python3
import json, subprocess
from pathlib import Path
sql = "SELECT AVG(CAST(substr(T1.fastestLapTime, 1, instr(T1.fastestLapTime, ':') - 1) AS REAL) * 60 + CAST(substr(T1.fastestLapTime, instr(T1.fastestLapTime, ':') + 1) AS REAL)) AS avg_seconds FROM results AS T1 INNER JOIN races AS T2 ON T1.raceId = T2.raceId WHERE T1.rank < 11 AND T2.year = 2006 AND T2.name = 'United States Grand Prix' AND T1.fastestLapTime IS NOT NULL AND TRIM(T1.fastestLapTime) != ''"
raw = subprocess.check_output(['db', 'query', sql], text=True)
rows = json.loads(raw.splitlines()[0])
if len(rows) == 1 and len(rows[0]) == 1:
    answer = rows[0][0]
elif rows and all(len(r) == 1 for r in rows):
    answer = [r[0] for r in rows]
else:
    answer = rows
Path('/app/answer.json').write_text(json.dumps({'answer': answer}) + '\n')
