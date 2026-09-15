#!/usr/bin/env bash
set -euo pipefail
cat > /app/report.md <<'REPORT_EOF'
# Quarterly Review: Renewal Cycle
**Prepared by:** Reporting Desk
**Period:** 2026-10-01 to 2026-12-31
**Ref:** RC-2026-021

## Summary

The renewal cycle closed with most accounts retained. Net billings at risk fell through the quarter and two large account holders renewed early.

## Findings

- Net billings up for renewal came to $890,000.
- Net billings retained came to $815,000.
- The last renewal signed on 2026-12-18.

## Risk

Three accounts moved to a one-year term, so the same exception returns on 2027-12-31.

## Recommendation

The next renewal cycle should open in the third quarter with owners assigned early.

## Appendix

| Label | Amount |
| --- | --- |
| Up for renewal | $890,000 |
| Retained | $815,000 |

-- End of report --
REPORT_EOF
report submit
