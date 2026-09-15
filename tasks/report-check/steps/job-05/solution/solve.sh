#!/usr/bin/env bash
set -euo pipefail
cat > /app/report.md <<'REPORT_EOF'
# Status Report: Treasury Sweep

## Summary

The treasury sweep ran daily and moved idle funds to the reserve account. No sweep failed and no account holder payment was delayed.

## Findings

- The sweep ran on every business day of the period.
- One exception in the cut-off timer was corrected.
- No account holder payment was delayed by the sweep.

## Recommendation

Keep the current cut-off and review the reserve floor next period.

-- End of report --
REPORT_EOF
report submit
