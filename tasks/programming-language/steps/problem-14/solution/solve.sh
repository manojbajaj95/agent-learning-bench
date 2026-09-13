#!/usr/bin/env bash
set -euo pipefail
cat > /app/workspace/solution.lang <<'LANGUAGE_EOF'
hgdbhgfhbbhgdhhgfcbgffgba
LANGUAGE_EOF
language-lab submit problem-14 < /app/workspace/solution.lang
