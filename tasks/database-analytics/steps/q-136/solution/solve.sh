#!/usr/bin/env python3
import json, subprocess
from pathlib import Path
sql = "SELECT T3.year, T3.name, T3.date, T3.time \nFROM qualifying AS T1 \nINNER JOIN drivers AS T2 ON T1.driverId = T2.driverId \nINNER JOIN races AS T3 ON T1.raceId = T3.raceId \nWHERE T1.driverId = ( \n    SELECT driverId \n    FROM drivers \n    ORDER BY dob DESC, driverId ASC \n    LIMIT 1 \n) \nORDER BY T3.date ASC, T3.raceId ASC \nLIMIT 1"
raw = subprocess.check_output(['db', 'query', sql], text=True)
rows = json.loads(raw.splitlines()[0])
if len(rows) == 1 and len(rows[0]) == 1:
    answer = rows[0][0]
elif rows and all(len(r) == 1 for r in rows):
    answer = [r[0] for r in rows]
else:
    answer = rows
Path('/app/answer.json').write_text(json.dumps({'answer': answer}) + '\n')
