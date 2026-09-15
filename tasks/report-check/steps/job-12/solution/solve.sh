#!/usr/bin/env bash
set -euo pipefail
cat > /app/report.md <<'REPORT_EOF'
# Quarterly Review: Q2 Forecast
**Prepared by:** Reporting Desk
**Period:** 2026-04-01 to 2026-06-30
**Ref:** RC-2026-012

## Summary

The second quarter forecast holds. Net billings are tracking to plan and the account holder pipeline supports the second half of the year.

## Findings

- Net billings for the quarter came to $1,310,000.
- The pipeline added nine account holders during the quarter.
- One exception in the forecast model was corrected on 2026-05-22.

## Recommendation

Keep the current forecast and revisit the model assumptions before the third quarter.

-- End of report --
REPORT_EOF
report submit
