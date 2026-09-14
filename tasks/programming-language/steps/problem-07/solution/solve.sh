#!/usr/bin/env bash
set -euo pipefail
cat > /app/workspace/solution.lang <<'LANGUAGE_EOF'
hgdbhgdhfcbgfa
LANGUAGE_EOF
language-lab submit problem-07 < /app/workspace/solution.lang
