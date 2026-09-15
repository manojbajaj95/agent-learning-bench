#!/usr/bin/env bash
set -euo pipefail
python3 /opt/f1/f1.py publish 168
rm -- "$0"
