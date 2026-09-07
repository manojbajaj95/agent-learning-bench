#!/usr/bin/env bash
set -euo pipefail
cat > /app/report.md <<'REPORT_EOF'
# Quarterly Review: Compliance Filing
**Prepared by:** Reporting Desk
**Period:** 2026-04-01 to 2026-06-30
**Ref:** RC-2026-013

## Summary

The quarterly filing was submitted on time. The reviewer raised two exceptions and both were closed before the deadline.

## Findings

- The filing was submitted on 2026-07-10.
- Two exceptions in the transaction schedule were closed before submission.
- External counsel reviewed the filing on 2026-07-08.

## Risk

The filing rules change on 2027-01-01 and the schedule format will need rework.

## Recommendation

Start the schedule rework in the third quarter and keep the current reviewer.

-- End of report --
REPORT_EOF
report submit
