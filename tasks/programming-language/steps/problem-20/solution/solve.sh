#!/usr/bin/env bash
set -euo pipefail
cat > /app/workspace/solution.lang <<'LANGUAGE_EOF'
hgdbhgfhbbhgdhfcbgfafg
LANGUAGE_EOF
language-lab submit problem-20 < /app/workspace/solution.lang
