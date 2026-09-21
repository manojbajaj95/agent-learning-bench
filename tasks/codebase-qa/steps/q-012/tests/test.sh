#!/bin/bash
set -euo pipefail
python3 /opt/qa/qa.py write-reference
rewardkit /tests
python3 /opt/qa/qa.py costs
