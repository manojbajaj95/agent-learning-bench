#!/usr/bin/env python3
import json, subprocess
from pathlib import Path
sql = "WITH champion_times AS ( SELECT T2.year, CASE WHEN INSTR(T1.time, ':') = 2 THEN CAST(SUBSTR(T1.time, 1, 1) AS REAL) * 3600 + CAST(SUBSTR(T1.time, 3, 2) AS REAL) * 60 + CAST(SUBSTR(T1.time, 6, 2) AS REAL) + CAST(SUBSTR(T1.time, 9) AS REAL) / 1000 WHEN INSTR(T1.time, ':') = 3 THEN CAST(SUBSTR(T1.time, 1, 2) AS REAL) * 3600 + CAST(SUBSTR(T1.time, 4, 2) AS REAL) * 60 + CAST(SUBSTR(T1.time, 7, 2) AS REAL) + CAST(SUBSTR(T1.time, 10) AS REAL) / 1000 END AS time_seconds FROM results AS T1 INNER JOIN races AS T2 ON T1.raceId = T2.raceId WHERE T1.positionOrder = 1 AND T1.time IS NOT NULL AND T2.year < 1975 ) SELECT year, AVG(time_seconds) FROM champion_times GROUP BY year HAVING AVG(time_seconds) IS NOT NULL"
raw = subprocess.check_output(['db', 'query', sql], text=True)
rows = json.loads(raw.splitlines()[0])
if len(rows) == 1 and len(rows[0]) == 1:
    answer = rows[0][0]
elif rows and all(len(r) == 1 for r in rows):
    answer = [r[0] for r in rows]
else:
    answer = rows
Path('/app/answer.json').write_text(json.dumps({'answer': answer}) + '\n')
