#!/usr/bin/env bash
set -euo pipefail

# Manual download. Run this from the task folder before you build the env.
# It is not called from Harbor setup.sh.

DEST="$(cd "$(dirname "$0")" && pwd)/data"
REPO="$DEST/repo"
mkdir -p "$DEST"

# SWE-QA Flask split: 48 question/answer pairs.
curl -L --retry 3 -o "$DEST/flask.jsonl" \
  "https://raw.githubusercontent.com/peng-weihan/SWE-QA-Bench/master/Benchmark/flask.jsonl"

# Pinned Flask snapshot from SWE-QA repo_commit.txt (85c5d93).
FLASK_SHA="85c5d93cbd049c4bd0679c36fd1ddcae8c37b642"
curl -L --retry 3 -o "$DEST/flask.tar.gz" \
  "https://github.com/pallets/flask/archive/${FLASK_SHA}.tar.gz"

rm -rf "$REPO"
mkdir -p "$REPO"
tar -xzf "$DEST/flask.tar.gz" --strip-components=1 -C "$REPO"
rm -f "$DEST/flask.tar.gz"

echo "Downloaded to $DEST"
echo "Questions: $DEST/flask.jsonl"
echo "Repo: $REPO (flask ${FLASK_SHA:0:7})"
