#!/usr/bin/env bash
set -euo pipefail
cat > /app/report.md <<'REPORT_EOF'
# Status Report: Support Backlog

## Summary

Support closed the backlog down to forty open tickets. The team cleared the oldest exceptions first and account holder replies stayed inside the target window.

## Findings

- The backlog fell from 210 tickets to 40 tickets.
- Repeat exceptions came mostly from the statements page.
- No account holder complaint was escalated during the period.

## Recommendation

Publish a short guide for the statements page and review the backlog again next period.

-- End of report --
REPORT_EOF
report submit
