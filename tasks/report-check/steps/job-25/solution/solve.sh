#!/usr/bin/env bash
set -euo pipefail
cat > /app/report.md <<'REPORT_EOF'
# Incident Review: Duplicate Settlement
**Prepared by:** Reporting Desk
**Period:** 2027-02-01 to 2027-02-28
**Ref:** RC-2027-025

## Summary

A duplicate settlement file was released once in February. All duplicates were reversed the same day and no account holder lost funds.

## Findings

- The duplicate file was released on 2027-02-09.
- The release step ran twice after a retry.
- Reversals returned $96,400 to thirty-one accounts.

## Risk

The release step still has no idempotency check, so the exception can repeat.

## Recommendation

Close the exception by adding an idempotency key to the release step before the next settlement cycle.

## Appendix

| Label | Amount |
| --- | --- |
| Reversed amount | $96,400 |
| Fees refunded | $4,200 |

-- End of report --
REPORT_EOF
report submit
