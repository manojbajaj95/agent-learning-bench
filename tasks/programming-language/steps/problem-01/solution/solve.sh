#!/usr/bin/env bash
set -euo pipefail
cat > /app/workspace/solution.lang <<'LANGUAGE_EOF'
cccccca
LANGUAGE_EOF
language-lab submit problem-01 < /app/workspace/solution.lang
