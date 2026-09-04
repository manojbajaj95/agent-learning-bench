#!/usr/bin/env bash
set -euo pipefail
cat > /app/report.md <<'REPORT_EOF'
# Status Report: Settlement Delays
**Prepared by:** Reporting Desk
**Period:** 2026-05-01 to 2026-05-31
**Ref:** RC-2026-011

## Summary

Settlement ran late on three days. The delays were traced to a slow clearing file and no account holder lost value from the delay.

## Findings

- Settlement was late on 2026-05-06, 2026-05-07 and 2026-05-19.
- The exception was a slow file from the clearing partner.
- Account holder balances were corrected on the same day each time.

## Risk

The clearing partner has not committed to a fixed delivery time, so the exception can repeat.

## Recommendation

Ask the clearing partner for a delivery window and add an alert at the file cut-off.

-- End of report --
REPORT_EOF
report submit
