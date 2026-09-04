#!/usr/bin/env bash
set -euo pipefail
cat > /app/report.md <<'REPORT_EOF'
# Portfolio Note: Fee Yield
**Prepared by:** Reporting Desk
**Period:** 2026-07-01 to 2026-09-30
**Ref:** RC-2026-020

## Summary

Fee yield improved in the quarter. The retail book carried the gain and account holder pricing stayed unchanged.

## Findings

- Fee net billings for the quarter came to $402,000.
- The retail book contributed $268,000 of that total.
- Yield improved from the pricing change on 2026-07-01.

## Recommendation

Hold pricing for one more quarter and review the wholesale book in the fourth quarter.

## Appendix

| Label | Amount |
| --- | --- |
| Fee net billings | $402,000 |
| Retail book | $268,000 |

-- End of report --
REPORT_EOF
report submit
