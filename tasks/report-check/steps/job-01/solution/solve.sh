#!/usr/bin/env bash
set -euo pipefail
cat > /app/report.md <<'REPORT_EOF'
# Status Report: Ledger Migration

## Summary

The ledger migration moved fourteen batches to the new store during the period. No account holder records were lost and the cutover held.

## Findings

- The migration ran for nine nights and finished on schedule.
- Two exceptions in the batch loader were closed the same week.
- Account holder statements rendered correctly after the cutover.

## Recommendation

Keep the old store in read-only mode for one more period, then retire it.

-- End of report --
REPORT_EOF
report submit
