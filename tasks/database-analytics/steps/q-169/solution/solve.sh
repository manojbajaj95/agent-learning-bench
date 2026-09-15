#!/usr/bin/env python3
import json, subprocess
from pathlib import Path
sql = "WITH per AS (\n  SELECT c.name AS circuit_name,\n         res.fastestLapTime,\n         (CAST(SUBSTR(res.fastestLapTime, 1, INSTR(res.fastestLapTime, ':') - 1) AS REAL) * 60)\n         + CAST(SUBSTR(res.fastestLapTime, INSTR(res.fastestLapTime, ':') + 1,\n                        INSTR(res.fastestLapTime, '.') - INSTR(res.fastestLapTime, ':') - 1) AS REAL)\n         + CAST(SUBSTR(res.fastestLapTime, INSTR(res.fastestLapTime, '.') + 1) AS REAL) / 1000.0 AS secs\n  FROM results AS res\n  JOIN races AS r ON res.raceId = r.raceId\n  JOIN circuits AS c ON r.circuitId = c.circuitId\n  WHERE c.country = 'Italy' AND res.fastestLapTime IS NOT NULL\n), min_per AS (\n  SELECT circuit_name, MIN(secs) AS min_secs\n  FROM per\n  GROUP BY circuit_name\n)\nSELECT p.circuit_name, p.fastestLapTime AS lap_record\nFROM per AS p\nJOIN min_per AS m\n  ON p.circuit_name = m.circuit_name AND p.secs = m.min_secs\nORDER BY p.circuit_name ASC"
raw = subprocess.check_output(['db', 'query', sql], text=True)
rows = json.loads(raw.splitlines()[0])
if len(rows) == 1 and len(rows[0]) == 1:
    answer = rows[0][0]
elif rows and all(len(r) == 1 for r in rows):
    answer = [r[0] for r in rows]
else:
    answer = rows
Path('/app/answer.json').write_text(json.dumps({'answer': answer}) + '\n')
