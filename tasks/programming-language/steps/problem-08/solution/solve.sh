#!/usr/bin/env bash
set -euo pipefail
cat > /app/workspace/solution.lang <<'LANGUAGE_EOF'
hgdbhgdccfhbafg
LANGUAGE_EOF
language-lab submit problem-08 < /app/workspace/solution.lang
