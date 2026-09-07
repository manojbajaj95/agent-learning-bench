#!/bin/bash
set -euo pipefail
python3 /opt/corpus/corpus.py write-reference
rewardkit /tests
python3 /opt/corpus/corpus.py costs
