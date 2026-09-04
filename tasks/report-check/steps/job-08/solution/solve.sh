#!/usr/bin/env bash
set -euo pipefail
cat > /app/report.md <<'REPORT_EOF'
# Status Report: Payments Gateway Cutover
**Prepared by:** Reporting Desk
**Period:** 2026-04-01 to 2026-04-30
**Ref:** RC-2026-008

## Summary

The gateway cutover moved all traffic to the new provider. Account holder payments continued through the switch and the rollback plan was not used.

## Findings

- The cutover ran on 2026-04-18 during the low-volume window.
- One exception in the retry queue was corrected the same day.
- Account holder payments settled at the normal rate after the switch.

## Risk

The old provider contract ends on 2026-06-30, so a rollback after that date would need a new agreement.

## Recommendation

Decommission the old gateway after one clean month and keep the retry alert in place.

-- End of report --
REPORT_EOF
report submit
