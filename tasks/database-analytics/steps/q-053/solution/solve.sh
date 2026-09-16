#!/usr/bin/env python3
import json, subprocess
from pathlib import Path
sql = "SELECT \"age\", TRIM(\"forename\" || ' ' || \"surname\") AS full_name FROM (SELECT CAST(strftime('%Y', '2026-01-01') AS INTEGER) - CAST(strftime('%Y', dob) AS INTEGER) AS age, forename, surname FROM drivers WHERE nationality = 'Japanese' ORDER BY dob DESC LIMIT 1) AS _fmt"
raw = subprocess.check_output(['db', 'query', sql], text=True)
rows = json.loads(raw.splitlines()[0])
if len(rows) == 1 and len(rows[0]) == 1:
    answer = rows[0][0]
elif rows and all(len(r) == 1 for r in rows):
    answer = [r[0] for r in rows]
else:
    answer = rows
Path('/app/answer.json').write_text(json.dumps({'answer': answer}) + '\n')
