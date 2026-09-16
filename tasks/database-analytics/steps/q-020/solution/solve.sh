#!/usr/bin/env python3
import json, subprocess
from pathlib import Path
sql = "SELECT TRIM(\"forename\" || ' ' || \"surname\") AS full_name FROM (SELECT T1.forename, T1.surname \nFROM drivers AS T1 \nINNER JOIN results AS T2 ON T2.driverId = T1.driverId \nWHERE T2.raceId = 592 \n  AND T2.time IS NOT NULL \n  AND T1.dob IS NOT NULL \nORDER BY T1.dob ASC, T1.driverId ASC \nLIMIT 1) AS _fmt"
raw = subprocess.check_output(['db', 'query', sql], text=True)
rows = json.loads(raw.splitlines()[0])
if len(rows) == 1 and len(rows[0]) == 1:
    answer = rows[0][0]
elif rows and all(len(r) == 1 for r in rows):
    answer = [r[0] for r in rows]
else:
    answer = rows
Path('/app/answer.json').write_text(json.dumps({'answer': answer}) + '\n')
