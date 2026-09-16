#!/usr/bin/env bash
set -euo pipefail
cat > /app/report.md <<'REPORT_EOF'
# Status Report: Support Backlog

## Summary

Support closed the backlog down to forty open cases. The team cleared the oldest exceptions first and account holder replies stayed inside the target window.

## Findings

- The backlog fell from 210 cases to 40 cases.
- Repeat cases came mostly from the same exception on the statements page.
- No account holder case was escalated during the period.

## Recommendation

Publish a short guide for the statements page and review the backlog again next period.

-- End of report --
REPORT_EOF
report submit
