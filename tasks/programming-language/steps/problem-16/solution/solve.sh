#!/usr/bin/env bash
set -euo pipefail
cat > /app/workspace/solution.lang <<'LANGUAGE_EOF'
hgdbhgdbhgdbhgcfffhhgbbbhgfaffgbbbhhgffabbg
LANGUAGE_EOF
language-lab submit problem-16 < /app/workspace/solution.lang
