#!/usr/bin/env python3
import json, subprocess
from pathlib import Path
sql = "SELECT T2.name, T2.year, T1.location, MAX(T3.lap) AS max_laps\nFROM circuits AS T1 \nINNER JOIN races AS T2 ON T1.circuitId = T2.circuitId \nINNER JOIN lapTimes AS T3 ON T3.raceId = T2.raceId \nGROUP BY T2.raceId, T2.name, T2.year, T1.location\nORDER BY max_laps DESC, T2.raceId ASC\nLIMIT 1"
raw = subprocess.check_output(['db', 'query', sql], text=True)
rows = json.loads(raw.splitlines()[0])
if len(rows) == 1 and len(rows[0]) == 1:
    answer = rows[0][0]
elif rows and all(len(r) == 1 for r in rows):
    answer = [r[0] for r in rows]
else:
    answer = rows
Path('/app/answer.json').write_text(json.dumps({'answer': answer}) + '\n')
