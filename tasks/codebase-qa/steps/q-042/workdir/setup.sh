#!/usr/bin/env bash
set -euo pipefail
python3 /opt/qa/qa.py publish 42
rm -- "$0"
