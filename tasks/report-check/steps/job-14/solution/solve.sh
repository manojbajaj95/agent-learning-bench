#!/usr/bin/env bash
set -euo pipefail
cat > /app/report.md <<'REPORT_EOF'
# Portfolio Note: Merchant Mix
**Prepared by:** Reporting Desk
**Period:** 2026-01-01 to 2026-06-30
**Ref:** RC-2026-014

## Summary

The merchant mix shifted toward retail during the half. Net billings per account holder rose and the concentration in travel fell.

## Findings

- Retail merchants produced net billings of $820,000.
- Travel merchants produced net billings of $415,000.
- The mix shift was recorded from 2026-03-01 onward.
- Two exceptions in the merchant tagging job affected the split.

## Recommendation

Hold the retail focus for one more half and review the travel exposure in the fourth quarter.

## Appendix

| Label | Amount |
| --- | --- |
| Retail merchants | $820,000 |
| Travel merchants | $415,000 |

-- End of report --
REPORT_EOF
report submit
