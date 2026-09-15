#!/usr/bin/env python3
import json, subprocess
from pathlib import Path
sql = "WITH time_in_seconds AS (\n  SELECT T1.positionOrder,\n         CASE WHEN T1.positionOrder = 1\n              THEN (CAST(SUBSTR(T1.time, 1, 1) AS REAL) * 3600) + (CAST(SUBSTR(T1.time, 3, 2) AS REAL) * 60) + CAST(SUBSTR(T1.time, 6) AS REAL)\n              ELSE CAST(SUBSTR(T1.time, 2) AS REAL)\n         END AS time_seconds\n  FROM results AS T1\n  INNER JOIN races AS T2 ON T1.raceId = T2.raceId\n  WHERE T2.name = 'Australian Grand Prix' AND T1.time IS NOT NULL AND T2.year = 2008\n),\nchampion_time AS (\n  SELECT time_seconds FROM time_in_seconds WHERE positionOrder = 1\n),\nlast_driver_incremental AS (\n  SELECT time_seconds FROM time_in_seconds WHERE positionOrder = (SELECT MAX(positionOrder) FROM time_in_seconds)\n)\nSELECT (CAST((SELECT time_seconds FROM last_driver_incremental) AS REAL) * 100) /\n       (SELECT time_seconds + (SELECT time_seconds FROM last_driver_incremental) FROM champion_time)"
raw = subprocess.check_output(['db', 'query', sql], text=True)
rows = json.loads(raw.splitlines()[0])
if len(rows) == 1 and len(rows[0]) == 1:
    answer = rows[0][0]
elif rows and all(len(r) == 1 for r in rows):
    answer = [r[0] for r in rows]
else:
    answer = rows
Path('/app/answer.json').write_text(json.dumps({'answer': answer}) + '\n')
