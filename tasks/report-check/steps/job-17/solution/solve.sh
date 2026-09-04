#!/usr/bin/env bash
set -euo pipefail
cat > /app/report.md <<'REPORT_EOF'
# Quarterly Review: Cost Base
**Prepared by:** Reporting Desk
**Period:** 2026-07-01 to 2026-09-30
**Ref:** RC-2026-017

## Summary

The cost base fell in the third quarter. Vendor spend dropped after the contract review and account holder support costs were flat.

## Findings

- Total costs for the quarter were $1,720,000.
- Vendor spend was $430,000, down from the prior quarter.
- The contract review closed on 2026-08-14.

## Risk

The support headcount plan for the fourth quarter is not yet approved.

## Recommendation

Approve the support headcount plan before the fourth quarter opens.

## Appendix

| Label | Amount |
| --- | --- |
| Total costs | $1,720,000 |
| Vendor spend | $430,000 |

-- End of report --
REPORT_EOF
report submit
