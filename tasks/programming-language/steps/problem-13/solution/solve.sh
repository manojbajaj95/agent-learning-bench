#!/usr/bin/env bash
set -euo pipefail
cat > /app/workspace/solution.lang <<'LANGUAGE_EOF'
hgdbhgfhbbhgdahfcbgffgba
LANGUAGE_EOF
language-lab submit problem-13 < /app/workspace/solution.lang
