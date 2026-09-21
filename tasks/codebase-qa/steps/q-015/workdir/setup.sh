#!/usr/bin/env bash
set -euo pipefail
python3 /opt/qa/qa.py publish 15
rm -- "$0"
