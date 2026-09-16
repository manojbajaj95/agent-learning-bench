#!/usr/bin/env bash
set -euo pipefail
cat > /app/report.md <<'REPORT_EOF'
# Vendor Assessment: Support Outsourcer
**Prepared by:** Reporting Desk
**Period:** 2027-01-01 to 2027-03-31
**Ref:** RC-2027-026

## Summary

The support outsourcer held quality through the quarter. Response times met the target and account holder satisfaction was flat.

## Findings

- Fees paid to the outsourcer were $178,000.
- The team closed 12400 cases in the quarter.
- The quarterly review was held on 2027-03-19.

## Recommendation

Extend the contract for two quarters and add a monthly quality report.

## Appendix

| Label | Amount |
| --- | --- |
| Fees paid | $178,000 |
| Credits applied | $9,500 |

-- End of report --
REPORT_EOF
report submit
