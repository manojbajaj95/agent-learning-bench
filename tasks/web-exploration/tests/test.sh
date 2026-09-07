#!/bin/bash
set -euo pipefail
rewardkit /tests
python3 /opt/web/web.py costs
