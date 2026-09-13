#!/usr/bin/env bash
set -euo pipefail
cat > /app/workspace/solution.lang <<'LANGUAGE_EOF'
hgdca
LANGUAGE_EOF
language-lab submit problem-05 < /app/workspace/solution.lang
