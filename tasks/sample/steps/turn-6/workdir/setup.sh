#!/usr/bin/env bash
set -euo pipefail

python3 /opt/tally/game.py shuffle
python3 /opt/tally/game.py view

rm -- "$0"
