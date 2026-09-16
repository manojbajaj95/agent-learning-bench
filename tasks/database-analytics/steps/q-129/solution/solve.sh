#!/usr/bin/env python3
import json, subprocess
from pathlib import Path
sql = "WITH times AS (\n  SELECT r.year,\n         res.fastestLapTime,\n         (CAST(SUBSTR(res.fastestLapTime, 1, INSTR(res.fastestLapTime, ':') - 1) AS REAL) * 60)\n         + CAST(SUBSTR(res.fastestLapTime, INSTR(res.fastestLapTime, ':') + 1,\n                        INSTR(res.fastestLapTime, '.') - INSTR(res.fastestLapTime, ':') - 1) AS REAL)\n         + CAST(SUBSTR(res.fastestLapTime, INSTR(res.fastestLapTime, '.') + 1) AS REAL) / 1000.0 AS secs\n  FROM results AS res\n  JOIN races AS r ON res.raceId = r.raceId\n  WHERE res.fastestLapTime IS NOT NULL\n)\nSELECT year\nFROM times\nORDER BY secs ASC, year ASC\nLIMIT 1"
raw = subprocess.check_output(['db', 'query', sql], text=True)
rows = json.loads(raw.splitlines()[0])
if len(rows) == 1 and len(rows[0]) == 1:
    answer = rows[0][0]
elif rows and all(len(r) == 1 for r in rows):
    answer = [r[0] for r in rows]
else:
    answer = rows
Path('/app/answer.json').write_text(json.dumps({'answer': answer}) + '\n')
