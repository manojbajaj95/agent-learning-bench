#!/usr/bin/env bash
set -euo pipefail
cat > /app/workspace/solution.lang <<'LANGUAGE_EOF'
hgdbhgfhbbhgdaffg
LANGUAGE_EOF
language-lab submit problem-15 < /app/workspace/solution.lang
