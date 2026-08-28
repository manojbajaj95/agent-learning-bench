#!/usr/bin/env bash
set -euo pipefail
export WARDEN_SETUP=1
python3 /opt/warden/cli.py start 09
rm -- "$0"
