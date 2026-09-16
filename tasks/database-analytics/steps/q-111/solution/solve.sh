#!/usr/bin/env python3
import json, subprocess
from pathlib import Path
sql = "SELECT TRIM(\"forename\" || ' ' || \"surname\") AS full_name FROM (SELECT T2.forename, T2.surname FROM results AS T1 INNER JOIN drivers AS T2 on T1.driverId = T2.driverId WHERE STRFTIME('%Y', T2.dob) > '1975' AND T1.rank = 2) AS _fmt"
raw = subprocess.check_output(['db', 'query', sql], text=True)
rows = json.loads(raw.splitlines()[0])
if len(rows) == 1 and len(rows[0]) == 1:
    answer = rows[0][0]
elif rows and all(len(r) == 1 for r in rows):
    answer = [r[0] for r in rows]
else:
    answer = rows
Path('/app/answer.json').write_text(json.dumps({'answer': answer}) + '\n')
