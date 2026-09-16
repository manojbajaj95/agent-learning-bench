#!/usr/bin/env bash
set -euo pipefail
python3 /opt/f1/f1.py publish 56
rm -- "$0"
