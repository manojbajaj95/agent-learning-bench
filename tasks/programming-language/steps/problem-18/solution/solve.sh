#!/usr/bin/env bash
set -euo pipefail
cat > /app/workspace/solution.lang <<'LANGUAGE_EOF'
hgdhbhgdbhgdhfcbgfafg
LANGUAGE_EOF
language-lab submit problem-18 < /app/workspace/solution.lang
