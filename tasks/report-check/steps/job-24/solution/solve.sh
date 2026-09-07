#!/usr/bin/env bash
set -euo pipefail
cat > /app/report.md <<'REPORT_EOF'
# Vendor Assessment: Clearing Partner
**Prepared by:** Reporting Desk
**Period:** 2027-01-01 to 2027-03-31
**Ref:** RC-2027-024

## Summary

The clearing partner met the service level in the quarter. Fees were stable and no account holder settlement was missed.

## Findings

- Fees paid to the partner were $214,000.
- Late files fell from nine to two.
- The service review was held on 2027-03-05.

## Recommendation

Renew the contract for one year and keep the delivery window in the agreement.

## Appendix

| Label | Amount |
| --- | --- |
| Fees paid | $214,000 |
| Penalty credits | $18,000 |

-- End of report --
REPORT_EOF
report submit
