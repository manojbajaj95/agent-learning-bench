#!/usr/bin/env python3
import json, subprocess
from pathlib import Path
sql = "SELECT ((MAX(CASE WHEN T2.raceId = 853 THEN CAST(T2.fastestLapSpeed AS REAL) END) - MAX(CASE WHEN T2.raceId = 854 THEN CAST(T2.fastestLapSpeed AS REAL) END)) * 100) / MAX(CASE WHEN T2.raceId = 853 THEN CAST(T2.fastestLapSpeed AS REAL) END) AS faster_percentage FROM drivers AS T1 INNER JOIN results AS T2 ON T2.driverId = T1.driverId WHERE T1.forename = 'Paul' AND T1.surname = 'di Resta'"
raw = subprocess.check_output(['db', 'query', sql], text=True)
rows = json.loads(raw.splitlines()[0])
if len(rows) == 1 and len(rows[0]) == 1:
    answer = rows[0][0]
elif rows and all(len(r) == 1 for r in rows):
    answer = [r[0] for r in rows]
else:
    answer = rows
Path('/app/answer.json').write_text(json.dumps({'answer': answer}) + '\n')
