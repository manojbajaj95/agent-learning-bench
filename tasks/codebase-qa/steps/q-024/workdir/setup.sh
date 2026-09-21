#!/usr/bin/env bash
set -euo pipefail
python3 /opt/qa/qa.py publish 24
rm -- "$0"
