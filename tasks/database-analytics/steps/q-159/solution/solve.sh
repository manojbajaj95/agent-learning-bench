#!/usr/bin/env python3
import json, subprocess
from pathlib import Path
sql = "SELECT \"wins\", TRIM(\"forename\" || ' ' || \"surname\") AS full_name FROM (SELECT COALESCE((SELECT MAX(wins) FROM driverStandings WHERE driverId = T2.driverId), 0) AS wins, T2.forename, T2.surname FROM drivers AS T2 WHERE T2.dob IS NOT NULL ORDER BY T2.dob ASC LIMIT 1) AS _fmt"
raw = subprocess.check_output(['db', 'query', sql], text=True)
rows = json.loads(raw.splitlines()[0])
if len(rows) == 1 and len(rows[0]) == 1:
    answer = rows[0][0]
elif rows and all(len(r) == 1 for r in rows):
    answer = [r[0] for r in rows]
else:
    answer = rows
Path('/app/answer.json').write_text(json.dumps({'answer': answer}) + '\n')
