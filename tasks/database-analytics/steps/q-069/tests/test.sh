#!/bin/bash
set -euo pipefail
rewardkit /tests
python3 /opt/f1/f1.py costs
