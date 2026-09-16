#!/usr/bin/env python3
import json, subprocess
from pathlib import Path
sql = "SELECT TRIM(\"forename\" || ' ' || \"surname\") AS full_name, \"duration\" FROM (SELECT T3.forename,T3.surname,T1.Duration FROM pitStops AS T1 INNER JOIN races AS T2 on T1.raceId = T2.raceId INNER JOIN drivers as T3 on T1.driverId=T3.driverId WHERE T2.year = 2011 AND T2.name = 'Australian Grand Prix') AS _fmt"
raw = subprocess.check_output(['db', 'query', sql], text=True)
rows = json.loads(raw.splitlines()[0])
if len(rows) == 1 and len(rows[0]) == 1:
    answer = rows[0][0]
elif rows and all(len(r) == 1 for r in rows):
    answer = [r[0] for r in rows]
else:
    answer = rows
Path('/app/answer.json').write_text(json.dumps({'answer': answer}) + '\n')
