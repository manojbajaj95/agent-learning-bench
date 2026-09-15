#!/usr/bin/env python3
"""Shim: reports are in alb.report; prefer `alb report`."""

from __future__ import annotations

import argparse
from pathlib import Path

from alb.bench import ROOT
from alb.report import render_markdown, write_report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs-dir", type=Path, default=ROOT / "jobs")
    parser.add_argument("--task", default=None)
    parser.add_argument("--job", default=None)
    parser.add_argument("--out-dir", type=Path, default=ROOT / "reports")
    args = parser.parse_args()
    rows, written = write_report(args.jobs_dir, args.out_dir, args.task, args.job)
    print(render_markdown(rows))
    for path in written.values():
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
