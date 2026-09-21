#!/usr/bin/env bash
set -euo pipefail
python3 /opt/qa/qa.py publish 27
rm -- "$0"
