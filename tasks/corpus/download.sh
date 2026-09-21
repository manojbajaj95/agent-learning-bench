#!/usr/bin/env bash
set -euo pipefail

# Refresh the upstream EnterpriseRAG-Bench dump into data/.
# The dump is in git. Run this only to replace it. Harbor setup.sh does not call it.

DEST="$(cd "$(dirname "$0")" && pwd)/data"
REL="https://github.com/onyx-dot-app/EnterpriseRAG-Bench/releases/download/v1.0.0"
RAW="https://raw.githubusercontent.com/onyx-dot-app/EnterpriseRAG-Bench/v1.0.0"
mkdir -p "$DEST"

curl -L --retry 3 -o "$DEST/questions.jsonl" \
  "$RAW/questions.jsonl"
curl -L --retry 3 -o "$DEST/confluence_slice_0001.zip" \
  "$REL/confluence_slice_0001.zip"
curl -L --retry 3 -o "$DEST/confluence_slice_0002.zip" \
  "$REL/confluence_slice_0002.zip"

echo "Downloaded to $DEST"
echo "Questions: $DEST/questions.jsonl"
echo "Wiki: $DEST/confluence_slice_0001.zip $DEST/confluence_slice_0002.zip"
