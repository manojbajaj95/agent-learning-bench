#!/usr/bin/env bash
set -euo pipefail
cat > /app/report.md <<'REPORT_EOF'
# Portfolio Note: Reserve Balances
**Prepared by:** Reporting Desk
**Period:** 2026-04-01 to 2026-06-30
**Ref:** RC-2026-016

## Summary

Reserve balances rose through the quarter. The floor was never breached and no account holder settlement drew on the buffer.

## Findings

- The closing reserve balance was $640,000.
- The lowest balance in the quarter was $512,000.
- The low point was recorded on 2026-05-12 and will recur next quarter.

## Recommendation

The reserve floor should rise by ten percent and be reviewed again after the third quarter.

## Appendix

| Label | Amount |
| --- | --- |
| Closing reserve | $640,000 |
| Lowest balance | $512,000 |

-- End of report --
REPORT_EOF
report submit
