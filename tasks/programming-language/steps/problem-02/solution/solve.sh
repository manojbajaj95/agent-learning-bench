#!/usr/bin/env bash
set -euo pipefail
cat > /app/workspace/solution.lang <<'LANGUAGE_EOF'
hgda
LANGUAGE_EOF
language-lab submit problem-02 < /app/workspace/solution.lang
