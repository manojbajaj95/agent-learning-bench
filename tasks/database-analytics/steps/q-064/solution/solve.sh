#!/usr/bin/env python3
import json, subprocess
from pathlib import Path
sql = "SELECT CAST(COUNT(DISTINCT CASE WHEN T1.country = 'Germany' THEN T2.raceId END) AS REAL) * 100 / COUNT(DISTINCT T2.raceId) FROM circuits T1 INNER JOIN races T2 ON T2.circuitId = T1.circuitId WHERE T2.name = 'European Grand Prix'"
raw = subprocess.check_output(['db', 'query', sql], text=True)
rows = json.loads(raw.splitlines()[0])
if len(rows) == 1 and len(rows[0]) == 1:
    answer = rows[0][0]
elif rows and all(len(r) == 1 for r in rows):
    answer = [r[0] for r in rows]
else:
    answer = rows
Path('/app/answer.json').write_text(json.dumps({'answer': answer}) + '\n')
