#!/usr/bin/env bash
set -euo pipefail
cat > /app/workspace/solution.lang <<'LANGUAGE_EOF'
hgdaa
LANGUAGE_EOF
language-lab submit problem-03 < /app/workspace/solution.lang
