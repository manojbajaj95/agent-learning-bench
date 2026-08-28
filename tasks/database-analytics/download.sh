#!/usr/bin/env bash
set -euo pipefail

# Manual download. Run this from the task folder before you build the env.
# It is not called from Harbor setup.sh.

DEST="$(cd "$(dirname "$0")" && pwd)/data"
mkdir -p "$DEST"

curl -L --retry 3 -o "$DEST/minidev.zip" \
  "https://bird-bench.oss-cn-beijing.aliyuncs.com/minidev.zip"

curl -L --retry 3 -o "$DEST/dev_20251106.json" \
  "https://huggingface.co/datasets/birdsql/bird_sql_dev_20251106/resolve/main/data/dev_20251106-00000-of-00001.json"

unzip -j -o "$DEST/minidev.zip" \
  "minidev/MINIDEV/dev_databases/formula_1/formula_1.sqlite" \
  -d "$DEST"

echo "Downloaded to $DEST"
echo "SQLite: $DEST/formula_1.sqlite"
echo "Questions: $DEST/dev_20251106.json"
