#!/usr/bin/env bash
set -euo pipefail
cat > /app/report.md <<'REPORT_EOF'
# Quarterly Review: Q3 Close
**Prepared by:** Reporting Desk
**Period:** 2026-07-01 to 2026-09-30
**Ref:** RC-2026-019

## Summary

The third quarter closed two days early. Net billings held above plan and the close calendar ran without a material exception.

## Findings

- Net billings for the quarter came to $1,395,000.
- Adjustments booked at close were small at $62,000.
- The close finished on 2026-10-02.

## Recommendation

The close calendar should stay and the adjustment review should move one day earlier.

## Appendix

| Label | Amount |
| --- | --- |
| Net billings | $1,395,000 |
| Adjustments | $62,000 |

-- End of report --
REPORT_EOF
report submit
