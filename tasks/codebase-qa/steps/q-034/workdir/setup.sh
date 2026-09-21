#!/usr/bin/env bash
set -euo pipefail
python3 /opt/qa/qa.py publish 34
rm -- "$0"
