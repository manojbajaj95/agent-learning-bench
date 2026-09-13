#!/usr/bin/env bash
set -euo pipefail
cat > /app/workspace/solution.lang <<'LANGUAGE_EOF'
hgdeeeeeeeeeebhgcfhhgbhgfgba
LANGUAGE_EOF
language-lab submit problem-11 < /app/workspace/solution.lang
