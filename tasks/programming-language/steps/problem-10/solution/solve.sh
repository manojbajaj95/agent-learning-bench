#!/usr/bin/env bash
set -euo pipefail
cat > /app/workspace/solution.lang <<'LANGUAGE_EOF'
hgdbhgfhbbhgdhfcbgffgba
LANGUAGE_EOF
language-lab submit problem-10 < /app/workspace/solution.lang
