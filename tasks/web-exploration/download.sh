#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$root/data"
url="https://raw.githubusercontent.com/ServiceNow/webarena-verified/6473f72db5dcefc97b5725b59e734504edc28a21/assets/dataset/webarena-verified.json"
curl --fail --location --retry 3 "$url" -o "$root/data/webarena-verified.json"
python3 "$root/generate_steps.py" --check
