#!/usr/bin/env bash
set -euo pipefail
cat > /app/report.md <<'REPORT_EOF'
# Status Report: Reconciliation Run

## Summary

The nightly reconciliation run completed every night. Two breaks were opened and closed inside the period and no account holder balance was restated.

## Findings

- The run finished before the cut-off on every night of the period.
- Two exceptions were found in the fee posting step.
- No account holder balance required a restatement.

## Recommendation

Add a second alert on the fee posting step and keep the current schedule.

-- End of report --
REPORT_EOF
report submit
