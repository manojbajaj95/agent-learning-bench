#!/usr/bin/env bash
set -euo pipefail
cat > /app/report.md <<'REPORT_EOF'
# Status Report: Data Retention Sweep

## Summary

The retention sweep removed expired records from three stores. Legal signed the record list and no account holder file was deleted in error.

## Findings

- The sweep covered the ledger store, the document store and the log store with no service interruption.
- One exception in the exclusion list was corrected before the run.
- No file belonging to account holders was deleted in error.

## Recommendation

Run the sweep on the same schedule and extend it to the archive store next period.

-- End of report --
REPORT_EOF
report submit
