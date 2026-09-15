#!/usr/bin/env bash
set -euo pipefail
cat > /app/report.md <<'REPORT_EOF'
# Quarterly Review: Q1 Close
**Prepared by:** Reporting Desk
**Period:** 2026-01-01 to 2026-03-31
**Ref:** RC-2026-007

## Summary

The first quarter closed on time. Net billings held above plan and the account holder base grew, with no material exception in the close calendar.

## Findings

- Net billings for the quarter came to $1,240,000.
- The close finished on 2026-03-31, one day ahead of the due date.
- Two exceptions in the intercompany step were cleared before sign-off.

## Recommendation

Keep the close calendar unchanged and review the intercompany step before the next quarter.

-- End of report --
REPORT_EOF
report submit
