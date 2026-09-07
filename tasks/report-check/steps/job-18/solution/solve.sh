#!/usr/bin/env bash
set -euo pipefail
cat > /app/report.md <<'REPORT_EOF'
# Portfolio Note: Currency Exposure
**Prepared by:** Reporting Desk
**Period:** 2026-07-01 to 2026-09-30
**Ref:** RC-2026-018

## Summary

Currency exposure widened in the quarter. The hedge covered most of the position and no account holder settlement was repriced.

## Findings

- The open position at quarter end was $275,000.
- The hedged amount was $240,000.
- The position widened after the rate move on 2026-09-03.

## Risk

The hedge expires on 2026-12-31 and renewal pricing is not fixed.

## Recommendation

Start the hedge renewal in the fourth quarter and keep the coverage ratio above eighty percent.

## Appendix

| Label | Amount |
| --- | --- |
| Open position | $275,000 |
| Hedged amount | $240,000 |

-- End of report --
REPORT_EOF
report submit
