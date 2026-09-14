#!/usr/bin/env bash
set -euo pipefail
cat > /app/workspace/solution.lang <<'LANGUAGE_EOF'
hgdbhgdbhgdafafa
LANGUAGE_EOF
language-lab submit problem-06 < /app/workspace/solution.lang
