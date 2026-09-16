#!/usr/bin/env python3
import json, subprocess
from pathlib import Path
sql = "SELECT TRIM(\"forename\" || ' ' || \"surname\") AS full_name, \"url\" FROM (SELECT DISTINCT T2.forename, T2.surname, T2.url\nFROM lapTimes AS T1\nINNER JOIN drivers AS T2 ON T2.driverId = T1.driverId\nWHERE T1.raceId = 161 AND T1.time LIKE '1:27%') AS _fmt"
raw = subprocess.check_output(['db', 'query', sql], text=True)
rows = json.loads(raw.splitlines()[0])
if len(rows) == 1 and len(rows[0]) == 1:
    answer = rows[0][0]
elif rows and all(len(r) == 1 for r in rows):
    answer = [r[0] for r in rows]
else:
    answer = rows
Path('/app/answer.json').write_text(json.dumps({'answer': answer}) + '\n')
