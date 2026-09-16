#!/usr/bin/env bash
set -euo pipefail
cat > /app/report.md <<'REPORT_EOF'
# Quarterly Review: H1 Performance
**Prepared by:** Reporting Desk
**Period:** 2026-01-01 to 2026-06-30
**Ref:** RC-2026-015

## Summary

First half performance met plan. Net billings grew across both quarters and the account holder base was stable through the period.

## Findings

- Net billings for the half came to $2,550,000.
- Costs for the half were $1,870,000.
- The largest single gain came from the fee change on 2026-02-01.

## Risk

The second half depends on two renewals that close on 2026-07-31.

## Recommendation

The team should track both renewals weekly and keep the current cost plan.

## Appendix

| Label | Amount |
| --- | --- |
| Net billings | $2,550,000 |
| Costs | $1,870,000 |

-- End of report --
REPORT_EOF
report submit
