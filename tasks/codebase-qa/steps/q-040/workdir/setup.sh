#!/usr/bin/env bash
set -euo pipefail
python3 /opt/qa/qa.py publish 40
rm -- "$0"
