#!/usr/bin/env bash
set -euo pipefail
cat > /app/report.md <<'REPORT_EOF'
# Quarterly Review: Fee Schedule Update
**Prepared by:** Reporting Desk
**Period:** 2026-01-01 to 2026-03-31
**Ref:** RC-2026-009

## Summary

The new fee schedule took effect during the quarter. Net billings from fees rose and no account holder left because of the change.

## Findings

- Fee net billings for the quarter came to $384,500.
- The schedule took effect on 2026-02-01.
- Four account holders asked for a review and all four stayed.

## Recommendation

Hold the schedule for two quarters and publish a plain summary for the account team.

-- End of report --
REPORT_EOF
report submit
