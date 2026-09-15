#!/usr/bin/env python3
import json, subprocess
from pathlib import Path
sql = "SELECT AVG(T1.milliseconds) \nFROM lapTimes AS T1 \nINNER JOIN races AS T2 ON T1.raceId = T2.raceId \nINNER JOIN circuits AS T3 ON T2.circuitId = T3.circuitId \nWHERE T3.country = 'Italy'"
raw = subprocess.check_output(['db', 'query', sql], text=True)
rows = json.loads(raw.splitlines()[0])
if len(rows) == 1 and len(rows[0]) == 1:
    answer = rows[0][0]
elif rows and all(len(r) == 1 for r in rows):
    answer = [r[0] for r in rows]
else:
    answer = rows
Path('/app/answer.json').write_text(json.dumps({'answer': answer}) + '\n')
