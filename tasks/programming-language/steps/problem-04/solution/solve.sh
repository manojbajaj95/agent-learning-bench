#!/usr/bin/env bash
set -euo pipefail
cat > /app/workspace/solution.lang <<'LANGUAGE_EOF'
hgdhgda
LANGUAGE_EOF
language-lab submit problem-04 < /app/workspace/solution.lang
