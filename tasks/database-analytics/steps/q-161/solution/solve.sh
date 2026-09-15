#!/usr/bin/env python3
import json, subprocess
from pathlib import Path
sql = "SELECT lt.time AS fastest_lap_time\nFROM lapTimes lt\nJOIN races r ON lt.raceId = r.raceId\nJOIN circuits c ON r.circuitId = c.circuitId\nORDER BY lt.milliseconds ASC, \n         lt.raceId ASC, \n         lt.driverId ASC, \n         lt.lap ASC\nLIMIT 1"
raw = subprocess.check_output(['db', 'query', sql], text=True)
rows = json.loads(raw.splitlines()[0])
if len(rows) == 1 and len(rows[0]) == 1:
    answer = rows[0][0]
elif rows and all(len(r) == 1 for r in rows):
    answer = [r[0] for r in rows]
else:
    answer = rows
Path('/app/answer.json').write_text(json.dumps({'answer': answer}) + '\n')
