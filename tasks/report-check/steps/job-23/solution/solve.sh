#!/usr/bin/env bash
set -euo pipefail
cat > /app/report.md <<'REPORT_EOF'
# Incident Review: Batch Job Failure
**Prepared by:** Reporting Desk
**Period:** 2027-01-01 to 2027-01-31
**Ref:** RC-2027-023

## Summary

A batch job failed on two nights in January and caused a short service interruption. The failure was contained, account holder balances were corrected and the root cause is closed.

## Findings

- The job failed on 2027-01-14 and 2027-01-15.
- The cause was a stale credential in the loader.
- Corrections moved $148,000 across sixty-two accounts.

## Risk

The same credential pattern is used by two other jobs and has not been rotated.

## Recommendation

Rotate loader credentials on a schedule and add a failure alert for on-call personnel.

## Appendix

| Label | Amount |
| --- | --- |
| Corrections | $148,000 |
| Manual reversals | $21,400 |

-- End of report --
REPORT_EOF
report submit
