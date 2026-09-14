#!/usr/bin/env bash
set -euo pipefail
cat > /app/workspace/solution.lang <<'LANGUAGE_EOF'
hgdbhgccfhbacfg
LANGUAGE_EOF
language-lab submit problem-09 < /app/workspace/solution.lang
