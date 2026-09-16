#!/usr/bin/env python3
import json, subprocess
from pathlib import Path
sql = "SELECT d.driverId,\n       (d.forename || ' ' || d.surname) AS driver_name,\n       MIN(lt.milliseconds) AS best_lap_ms\nFROM drivers AS d\nJOIN lapTimes AS lt ON lt.driverId = d.driverId\nWHERE d.nationality = 'German'\n  AND STRFTIME('%Y', d.dob) BETWEEN '1980' AND '1990'\n  AND lt.milliseconds IS NOT NULL\nGROUP BY d.driverId, driver_name\nORDER BY best_lap_ms ASC, driver_name ASC\nLIMIT 3"
raw = subprocess.check_output(['db', 'query', sql], text=True)
rows = json.loads(raw.splitlines()[0])
if len(rows) == 1 and len(rows[0]) == 1:
    answer = rows[0][0]
elif rows and all(len(r) == 1 for r in rows):
    answer = [r[0] for r in rows]
else:
    answer = rows
Path('/app/answer.json').write_text(json.dumps({'answer': answer}) + '\n')
