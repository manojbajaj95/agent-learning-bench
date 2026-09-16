#!/usr/bin/env bash
set -euo pipefail
cat > /app/report.md <<'REPORT_EOF'
# Status Report: Onboarding Queue

## Summary

The onboarding queue cleared four days early. Support handled the overflow without extra personnel and no account holder waited longer than two days.

## Findings

- The queue held 320 files at the start of the period.
- Three exceptions in the identity check step were fixed.
- Account holders in the priority lane were onboarded within one day.

## Recommendation

Move two reviewers to the standard lane and keep the priority lane staffed.

-- End of report --
REPORT_EOF
report submit
