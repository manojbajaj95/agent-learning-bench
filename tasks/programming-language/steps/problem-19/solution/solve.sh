#!/usr/bin/env bash
set -euo pipefail
cat > /app/workspace/solution.lang <<'LANGUAGE_EOF'
hgdhbcbhgbhgfffhbbcbcfffgbbbhfffcbbbgfhfcbgffgba
LANGUAGE_EOF
language-lab submit problem-19 < /app/workspace/solution.lang
