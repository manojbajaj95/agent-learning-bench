#!/usr/bin/env bash
set -euo pipefail
python3 /opt/qa/qa.py publish 3
rm -- "$0"
