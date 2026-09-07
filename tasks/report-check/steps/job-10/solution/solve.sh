#!/usr/bin/env bash
set -euo pipefail
cat > /app/report.md <<'REPORT_EOF'
# Quarterly Review: Churn Review
**Prepared by:** Reporting Desk
**Period:** 2026-01-01 to 2026-03-31
**Ref:** RC-2026-010

## Summary

Churn stayed inside the plan for the quarter. The account holders who left were small accounts and the impact on net billings was limited.

## Findings

- Eleven account holders closed accounts during the quarter.
- Lost net billings from those accounts came to $96,500.
- The largest closure was recorded on 2026-03-09.

## Risk

Two large accounts are in renewal on 2026-07-31 and a loss there would move the churn line materially.

## Recommendation

Assign an owner to each renewal account and report the outcome next quarter.

-- End of report --
REPORT_EOF
report submit
