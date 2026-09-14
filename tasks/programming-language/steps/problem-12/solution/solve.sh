#!/usr/bin/env bash
set -euo pipefail
cat > /app/workspace/solution.lang <<'LANGUAGE_EOF'
hgdbhgccfhbccfgba
LANGUAGE_EOF
language-lab submit problem-12 < /app/workspace/solution.lang
