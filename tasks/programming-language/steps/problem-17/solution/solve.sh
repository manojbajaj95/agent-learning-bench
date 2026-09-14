#!/usr/bin/env bash
set -euo pipefail
cat > /app/workspace/solution.lang <<'LANGUAGE_EOF'
hgdhbhgdbhgdfhbbhgbhgffhbcbcffgbbhffcbbgfhbbcffgffgfgbbbbba
LANGUAGE_EOF
language-lab submit problem-17 < /app/workspace/solution.lang
