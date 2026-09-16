#!/usr/bin/env python3
import json, subprocess
from pathlib import Path
sql = "SELECT TRIM(\"forename\" || ' ' || \"surname\") AS full_name FROM (SELECT T2.forename, T2.surname FROM pitStops AS T1 INNER JOIN drivers AS T2 on T1.driverId = T2.driverId WHERE T2.nationality = 'German' AND CAST(STRFTIME('%Y', T2.dob) AS INTEGER) BETWEEN 1980 AND 1985 GROUP BY T2.driverId, T2.forename, T2.surname ORDER BY AVG(T1.milliseconds) LIMIT 3) AS _fmt"
raw = subprocess.check_output(['db', 'query', sql], text=True)
rows = json.loads(raw.splitlines()[0])
if len(rows) == 1 and len(rows[0]) == 1:
    answer = rows[0][0]
elif rows and all(len(r) == 1 for r in rows):
    answer = [r[0] for r in rows]
else:
    answer = rows
Path('/app/answer.json').write_text(json.dumps({'answer': answer}) + '\n')
