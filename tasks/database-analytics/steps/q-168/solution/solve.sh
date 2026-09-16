#!/usr/bin/env python3
import json, subprocess
from pathlib import Path
sql = "WITH fastest_lap_times AS ( SELECT T1.raceId, T1.fastestLapTime FROM results AS T1 WHERE T1.FastestLapTime IS NOT NULL) SELECT MIN(fastest_lap_times.fastestLapTime) as lap_record FROM fastest_lap_times INNER JOIN races AS T2 on fastest_lap_times.raceId = T2.raceId INNER JOIN circuits AS T3 on T2.circuitId = T3.circuitId WHERE T2.name = 'Austrian Grand Prix'"
raw = subprocess.check_output(['db', 'query', sql], text=True)
rows = json.loads(raw.splitlines()[0])
if len(rows) == 1 and len(rows[0]) == 1:
    answer = rows[0][0]
elif rows and all(len(r) == 1 for r in rows):
    answer = [r[0] for r in rows]
else:
    answer = rows
Path('/app/answer.json').write_text(json.dumps({'answer': answer}) + '\n')
