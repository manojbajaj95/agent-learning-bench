#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
export PATH="${HOME}/.docker/bin:${PATH}"
if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  echo "Set OPENAI_API_KEY first." >&2
  exit 1
fi
exec harbor run -p tasks/web-exploration -a pi -m openai/gpt-5.6-luna --agent-timeout-multiplier 5 --job-name webarena-shopping-baseline-smoke-3
